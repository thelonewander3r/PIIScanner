"""Typer CLI entrypoint."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Annotated, Literal

import typer
from rich.console import Console

from piilint import __version__
from piilint.baseline import BaselineError, load_baseline, subtract_baseline, write_baseline
from piilint.config import Config, ConfigError, load_config
from piilint.engine import ScanResult, scan_path
from piilint.findings import Severity
from piilint.gitutil import GitError, find_repo_root, staged_files
from piilint.history import (
    HistoryError,
    default_history_path,
    latest_metadata_records,
    new_findings_since,
    parse_since,
    record_metadata_run,
    records_from_document,
    summarize_payload,
)
from piilint.metadata import build_metadata_document, render_metadata_json
from piilint.recognizers import ner as ner_mod
from piilint.redact import RedactError, redact_tree
from piilint.reporters import render_console, render_json, render_sarif

app = typer.Typer(
    name="piilint",
    help=(
        "Find PII in notebooks, CSV, JSON, Parquet, and source code — locally. "
        "piilint helps you find sensitive data before it leaks. It is a detection "
        "aid, not a compliance certification, and cannot guarantee that all "
        "sensitive data is found."
    ),
    add_completion=False,
    context_settings={"help_option_names": ["-h", "--help"]},
)

SEVERITY_RANK = {Severity.LOW: 1, Severity.MEDIUM: 2, Severity.HIGH: 3}

OutputFormat = Literal["console", "json", "sarif"]


def _fail_on_rank(name: str) -> int:
    mapping = {"never": 99, "low": 1, "medium": 2, "high": 3}
    if name not in mapping:
        raise typer.BadParameter("fail-on must be one of: high, medium, low, never")
    return mapping[name]


def _ci_truthy() -> bool:
    return os.environ.get("CI", "").strip().lower() in {"1", "true", "yes"}


def _resolve_staged_only_paths(target: Path) -> tuple[list[Path], int]:
    """Return (staged files under ``target``, total staged count). Raises GitError."""
    repo_root = find_repo_root(target if target.exists() else Path.cwd())
    staged = staged_files(repo_root)
    if not staged:
        return [], 0
    target_res = target.resolve()
    selected: list[Path] = []
    for path in staged:
        if target_res.is_file():
            if path == target_res:
                selected.append(path)
            continue
        try:
            path.relative_to(target_res)
        except ValueError:
            continue
        selected.append(path)
    return selected, len(staged)


def _prepare_scan(
    path: Path,
    *,
    fail_on: str | None = None,
    min_confidence: float | None = None,
    enable_ip: bool | None = None,
    enable_ner: bool = False,
    sample_rows: int | None = None,
    exclude: list[str] | None = None,
    baseline: Path | None = None,
    staged: bool = False,
) -> tuple[Config, ScanResult, int]:
    """Load config, scan, optional baseline subtract. Returns (config, result, fail threshold)."""
    if not path.exists():
        typer.secho(f"Path not found: {path}", fg=typer.colors.RED, err=True)
        raise typer.Exit(2)

    try:
        config = load_config(
            path,
            cli_fail_on=fail_on,
            cli_min_confidence=min_confidence,
            cli_enable_ip=enable_ip,
            cli_exclude=exclude,
        )
    except ConfigError as exc:
        typer.secho(f"Config error: {exc}", fg=typer.colors.RED, err=True)
        raise typer.Exit(2) from exc

    if enable_ner:
        try:
            ner_mod.require_ner_ready()
        except ner_mod.NerDependencyError as exc:
            typer.secho(str(exc), fg=typer.colors.RED, err=True)
            raise typer.Exit(2) from exc
        except ner_mod.NerModelError as exc:
            typer.secho(str(exc), fg=typer.colors.RED, err=True)
            raise typer.Exit(2) from exc
        from piilint.findings import EntityType as _EntityType

        config.entity_enabled[_EntityType.PERSON] = True
        config.entity_enabled[_EntityType.ADDRESS] = True

    try:
        threshold = _fail_on_rank(config.scan.fail_on)
    except typer.BadParameter as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        raise typer.Exit(2) from exc

    only_paths: list[Path] | None = None
    if staged:
        try:
            only_paths, staged_total = _resolve_staged_only_paths(path)
        except GitError as exc:
            typer.secho(f"Git error: {exc}", fg=typer.colors.RED, err=True)
            raise typer.Exit(2) from exc
        if not only_paths:
            if staged_total == 0:
                typer.echo("Nothing staged — nothing to scan.")
            else:
                typer.echo("No staged files under the scan path — nothing to scan.")
            raise typer.Exit(0)

    try:
        result = scan_path(
            path,
            config=config,
            sample_rows=sample_rows,
            only_paths=only_paths,
            enable_ner=enable_ner,
        )
    except Exception as exc:  # noqa: BLE001 — unexpected errors are exit 2, not 1
        typer.secho(f"Scan failed: {exc}", fg=typer.colors.RED, err=True)
        raise typer.Exit(2) from exc

    # Baseline subtract after policy (engine already applied policy), before reporter
    if baseline is not None:
        try:
            fingerprints = load_baseline(baseline)
        except BaselineError as exc:
            typer.secho(f"Baseline error: {exc}", fg=typer.colors.RED, err=True)
            raise typer.Exit(2) from exc
        result = ScanResult(
            findings=subtract_baseline(result.findings, fingerprints),
            files_scanned=result.files_scanned,
            elapsed_seconds=result.elapsed_seconds,
        )

    return config, result, threshold


def _run_scan(
    path: Path,
    *,
    fail_on: str | None,
    min_confidence: float | None,
    enable_ip: bool | None,
    enable_ner: bool,
    sample_rows: int | None,
    exclude: list[str] | None,
    baseline: Path | None,
    staged: bool,
    output_format: OutputFormat,
    show_matches: bool,
) -> None:
    if show_matches:
        if output_format != "console":
            typer.secho(
                "--show-matches applies only to --format console",
                fg=typer.colors.RED,
                err=True,
            )
            raise typer.Exit(2)
        if _ci_truthy():
            typer.secho(
                "--show-matches is refused when CI=true (local triage only)",
                fg=typer.colors.RED,
                err=True,
            )
            raise typer.Exit(2)

    config, result, threshold = _prepare_scan(
        path,
        fail_on=fail_on,
        min_confidence=min_confidence,
        enable_ip=enable_ip,
        enable_ner=enable_ner,
        sample_rows=sample_rows,
        exclude=exclude,
        baseline=baseline,
        staged=staged,
    )

    if output_format == "json":
        typer.echo(render_json(result, config), nl=False)
    elif output_format == "sarif":
        typer.echo(render_sarif(result), nl=False)
    else:
        render_console(result, console=Console(), show_matches=show_matches)

    actionable = [f for f in result.findings if SEVERITY_RANK[f.severity] >= threshold]
    raise typer.Exit(1 if actionable else 0)


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    version: bool = typer.Option(False, "--version", help="Print version and exit."),
) -> None:
    if version:
        typer.echo(__version__)
        raise typer.Exit(0)
    if ctx.invoked_subcommand is None:
        typer.echo(ctx.get_help())
        raise typer.Exit(0)


@app.command("scan", help="Scan a file or directory for PII.")
def scan_cmd(
    path: Annotated[
        Path,
        typer.Argument(exists=False, readable=False, help="Target path."),
    ] = Path("."),
    fail_on: Annotated[
        str | None,
        typer.Option("--fail-on", help="Minimum severity that fails CI (overrides config)."),
    ] = None,
    min_confidence: Annotated[
        float | None,
        typer.Option("--min-confidence", min=0.0, max=1.0, help="Drop findings below this."),
    ] = None,
    enable_ip: Annotated[
        bool | None,
        typer.Option("--enable-ip/--no-enable-ip", help="Enable IP address detection."),
    ] = None,
    ner: Annotated[
        bool,
        typer.Option(
            "--ner",
            help="Enable optional PERSON/ADDRESS NER (requires piilint[ner] + setup-ner).",
        ),
    ] = False,
    sample: Annotated[
        int | None,
        typer.Option("--sample", help="Sample at most N rows per tabular file."),
    ] = None,
    exclude: Annotated[
        list[str] | None,
        typer.Option("--exclude", help="Glob to exclude (repeatable; overrides config exclude)."),
    ] = None,
    baseline: Annotated[
        Path | None,
        typer.Option(
            "--baseline",
            help="Subtract fingerprints from this baseline file (report new findings only).",
        ),
    ] = None,
    staged: Annotated[
        bool,
        typer.Option(
            "--staged",
            help="Scan only git-staged files (Added/Copied/Modified/Renamed).",
        ),
    ] = False,
    output_format: Annotated[
        str,
        typer.Option(
            "--format",
            help="Output format: console (default), json, or sarif.",
        ),
    ] = "console",
    show_matches: Annotated[
        bool,
        typer.Option(
            "--show-matches",
            help="Unmask Sample column on console (local triage only; refused when CI=true).",
        ),
    ] = False,
) -> None:
    fmt = output_format.lower().strip()
    if fmt not in {"console", "json", "sarif"}:
        typer.secho(
            "--format must be one of: console, json, sarif",
            fg=typer.colors.RED,
            err=True,
        )
        raise typer.Exit(2)
    _run_scan(
        path,
        fail_on=fail_on,
        min_confidence=min_confidence,
        enable_ip=enable_ip,
        enable_ner=ner,
        sample_rows=sample,
        exclude=exclude,
        baseline=baseline,
        staged=staged,
        output_format=fmt,  # type: ignore[arg-type]
        show_matches=show_matches,
    )


@app.command("baseline", help="Write a baseline of current finding fingerprints.")
def baseline_cmd(
    path: Annotated[
        Path,
        typer.Argument(exists=False, readable=False, help="Target path to scan."),
    ] = Path("."),
    output: Annotated[
        Path,
        typer.Option(
            "--output",
            "-o",
            help="Baseline JSON output path (fingerprints only; no raw PII).",
        ),
    ] = Path("piilint-baseline.json"),
    min_confidence: Annotated[
        float | None,
        typer.Option("--min-confidence", min=0.0, max=1.0, help="Drop findings below this."),
    ] = None,
    enable_ip: Annotated[
        bool | None,
        typer.Option("--enable-ip/--no-enable-ip", help="Enable IP address detection."),
    ] = None,
    sample: Annotated[
        int | None,
        typer.Option("--sample", help="Sample at most N rows per tabular file."),
    ] = None,
    exclude: Annotated[
        list[str] | None,
        typer.Option("--exclude", help="Glob to exclude (repeatable; overrides config exclude)."),
    ] = None,
) -> None:
    """Scan like ``scan``, then write ALL post-policy findings into a baseline file.

    Exit 0 on success; exit 2 on path/config/scan errors. Does not apply --fail-on
    filtering — the baseline captures the full post-policy finding set.
    """
    if not path.exists():
        typer.secho(f"Path not found: {path}", fg=typer.colors.RED, err=True)
        raise typer.Exit(2)

    try:
        config = load_config(
            path,
            cli_min_confidence=min_confidence,
            cli_enable_ip=enable_ip,
            cli_exclude=exclude,
        )
    except ConfigError as exc:
        typer.secho(f"Config error: {exc}", fg=typer.colors.RED, err=True)
        raise typer.Exit(2) from exc

    try:
        result = scan_path(path, config=config, sample_rows=sample)
    except Exception as exc:  # noqa: BLE001
        typer.secho(f"Scan failed: {exc}", fg=typer.colors.RED, err=True)
        raise typer.Exit(2) from exc

    try:
        write_baseline(output, result.findings)
    except OSError as exc:
        typer.secho(f"Failed to write baseline: {exc}", fg=typer.colors.RED, err=True)
        raise typer.Exit(2) from exc

    typer.echo(
        f"Wrote baseline with {len({f.fingerprint for f in result.findings})} fingerprint(s) "
        f"→ {output}"
    )
    raise typer.Exit(0)


@app.command(
    "redact",
    help="Write cleaned copies with PII masked (never overwrites sources).",
)
def redact_cmd(
    path: Annotated[
        Path,
        typer.Argument(exists=False, readable=False, help="File or directory to redact."),
    ] = Path("."),
    output: Annotated[
        Path | None,
        typer.Option(
            "--output",
            "-o",
            help="Output directory for cleaned copies (required; sources untouched).",
        ),
    ] = None,
    min_confidence: Annotated[
        float | None,
        typer.Option("--min-confidence", min=0.0, max=1.0, help="Drop matches below this."),
    ] = None,
    enable_ip: Annotated[
        bool | None,
        typer.Option("--enable-ip/--no-enable-ip", help="Enable IP address detection."),
    ] = None,
    ner: Annotated[
        bool,
        typer.Option(
            "--ner",
            help="Enable optional PERSON/ADDRESS NER while redacting (requires piilint[ner]).",
        ),
    ] = False,
    exclude: Annotated[
        list[str] | None,
        typer.Option("--exclude", help="Glob to exclude (repeatable; overrides config exclude)."),
    ] = None,
) -> None:
    """Copy supported files under PATH into -o with PII spans rewritten.

    Honors the same config/policy as scan (entity toggles, allowlists, inline
    suppressions, min_confidence, excludes). Formats: text, json/jsonl, csv/tsv,
    notebooks, parquet (string columns), xlsx, and docx (requires piilint[office]).
    PDF redact deferred. No in-place mode.
    """
    if output is None:
        typer.secho("-o / --output is required", fg=typer.colors.RED, err=True)
        raise typer.Exit(2)
    if not path.exists():
        typer.secho(f"Path not found: {path}", fg=typer.colors.RED, err=True)
        raise typer.Exit(2)

    try:
        config = load_config(
            path,
            cli_min_confidence=min_confidence,
            cli_enable_ip=enable_ip,
            cli_exclude=exclude,
        )
    except ConfigError as exc:
        typer.secho(f"Config error: {exc}", fg=typer.colors.RED, err=True)
        raise typer.Exit(2) from exc

    if ner:
        try:
            ner_mod.require_ner_ready()
        except ner_mod.NerDependencyError as exc:
            typer.secho(str(exc), fg=typer.colors.RED, err=True)
            raise typer.Exit(2) from exc

    try:
        result = redact_tree(path, output, config=config, enable_ner=ner)
    except RedactError as exc:
        typer.secho(f"Redact error: {exc}", fg=typer.colors.RED, err=True)
        raise typer.Exit(2) from exc
    except Exception as exc:  # noqa: BLE001
        typer.secho(f"Redact failed: {exc}", fg=typer.colors.RED, err=True)
        raise typer.Exit(2) from exc

    typer.echo(
        f"Wrote {result.files_written} file(s) ? {output} "
        f"({result.spans_redacted} span(s) redacted, {result.files_skipped} skipped)"
    )
    raise typer.Exit(0)


@app.command(
    "report",
    help="Emit metadata-only findings JSON and auto-record into local history (no network).",
)
def report_cmd(
    path: Annotated[
        Path,
        typer.Argument(exists=False, readable=False, help="Target path."),
    ] = Path("."),
    metadata_only: Annotated[
        bool,
        typer.Option(
            "--metadata-only",
            help="Emit trust-boundary metadata JSON (required for this MVP).",
        ),
    ] = False,
    output: Annotated[
        Path | None,
        typer.Option(
            "--output",
            "-o",
            help="Write metadata JSON to FILE instead of stdout.",
        ),
    ] = None,
    fail_on: Annotated[
        str | None,
        typer.Option("--fail-on", help="Minimum severity that fails CI (overrides config)."),
    ] = None,
    min_confidence: Annotated[
        float | None,
        typer.Option("--min-confidence", min=0.0, max=1.0, help="Drop findings below this."),
    ] = None,
    enable_ip: Annotated[
        bool | None,
        typer.Option("--enable-ip/--no-enable-ip", help="Enable IP address detection."),
    ] = None,
    sample: Annotated[
        int | None,
        typer.Option("--sample", help="Sample at most N rows per tabular file."),
    ] = None,
    exclude: Annotated[
        list[str] | None,
        typer.Option("--exclude", help="Glob to exclude (repeatable; overrides config exclude)."),
    ] = None,
    baseline: Annotated[
        Path | None,
        typer.Option(
            "--baseline",
            help="Subtract fingerprints from this baseline file (report new findings only).",
        ),
    ] = None,
) -> None:
    """Scan like ``scan``, emit metadata-only JSON, and record into local SQLite history.

    Default ``piilint .`` / ``scan`` / ``baseline`` / ``redact`` do **not** write history.
    ``report --metadata-only`` always records locally; it never opens a network socket.
    """
    if not metadata_only:
        typer.secho(
            "report requires --metadata-only in this MVP (full reports use scan --format json)",
            fg=typer.colors.RED,
            err=True,
        )
        raise typer.Exit(2)

    config, result, _threshold = _prepare_scan(
        path,
        fail_on=fail_on,
        min_confidence=min_confidence,
        enable_ip=enable_ip,
        sample_rows=sample,
        exclude=exclude,
        baseline=baseline,
    )
    doc = build_metadata_document(result.findings, config)
    text_out = render_metadata_json(result.findings, config)
    try:
        records = records_from_document(doc)
        run_id = record_metadata_run(
            records,
            scanned_at=str(doc["scanned_at"]),
            config_hash=str(doc["config_hash"]),
            tool_version=__version__,
        )
    except HistoryError as exc:
        typer.secho(f"History error: {exc}", fg=typer.colors.RED, err=True)
        raise typer.Exit(2) from exc
    except OSError as exc:
        typer.secho(f"History write failed: {exc}", fg=typer.colors.RED, err=True)
        raise typer.Exit(2) from exc

    if output is not None:
        try:
            output.write_text(text_out, encoding="utf-8")
        except OSError as exc:
            typer.secho(f"Failed to write report: {exc}", fg=typer.colors.RED, err=True)
            raise typer.Exit(2) from exc
        typer.echo(
            f"Wrote metadata-only report ({len(records)} finding(s)) → {output} "
            f"(recorded run {run_id} in {default_history_path()})"
        )
    else:
        typer.echo(text_out, nl=False)
        typer.secho(
            f"# recorded run {run_id} → {default_history_path()}",
            fg=typer.colors.GREEN,
            err=True,
        )
    raise typer.Exit(0)


@app.command(
    "history",
    help="List finding_fingerprints first seen since a time (local SQLite; no network).",
)
def history_cmd(
    since: Annotated[
        str,
        typer.Option(
            "--since",
            help="Relative window (7d, 24h, 30m) or ISO-8601 datetime.",
        ),
    ],
    as_json: Annotated[
        bool,
        typer.Option("--json", help="Emit JSON instead of human-readable lines."),
    ] = False,
) -> None:
    """Print new ``finding_fingerprint``s whose earliest local history sighting is after T."""
    try:
        since_dt = parse_since(since)
        items = new_findings_since(since_dt)
    except HistoryError as exc:
        typer.secho(f"History error: {exc}", fg=typer.colors.RED, err=True)
        raise typer.Exit(2) from exc
    except OSError as exc:
        typer.secho(f"History read failed: {exc}", fg=typer.colors.RED, err=True)
        raise typer.Exit(2) from exc

    if as_json:
        import json

        payload = {
            "count": len(items),
            "findings": [i.as_dict() for i in items],
            "since": since_dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
        payload_text = json.dumps(payload, sort_keys=True, indent=2, ensure_ascii=False) + "\n"
        typer.echo(payload_text, nl=False)
        raise typer.Exit(0)

    typer.echo(
        f"New finding_fingerprint(s) since {since_dt.strftime('%Y-%m-%dT%H:%M:%SZ')} "
        f"({len(items)}):"
    )
    if not items:
        typer.echo("(none)")
        raise typer.Exit(0)
    for item in items:
        typer.echo(
            f"{item.scanned_at}  {item.severity:<6}  {item.entity:<12}  {item.finding_fingerprint}"
        )
    raise typer.Exit(0)


@app.command(
    "sync",
    help="Opt-in metadata sync helpers (dry-run only in this MVP; never opens sockets).",
)
def sync_cmd(
    metadata: Annotated[
        bool,
        typer.Option(
            "--metadata",
            help="Operate on metadata-only findings payload.",
        ),
    ] = False,
    dry_run: Annotated[
        bool,
        typer.Option(
            "--dry-run",
            help="Print counts / byte size / destination placeholder; send nothing.",
        ),
    ] = False,
) -> None:
    """Dry-run metadata sync summary. Real upload is out of scope for Slice B local MVP."""
    if not metadata:
        typer.secho("sync requires --metadata in this MVP", fg=typer.colors.RED, err=True)
        raise typer.Exit(2)
    if not dry_run:
        typer.secho(
            "Real upload is not implemented. Use: piilint sync --metadata --dry-run",
            fg=typer.colors.RED,
            err=True,
        )
        raise typer.Exit(2)

    # Intentionally no urllib/httpx/socket usage — local DB read only.
    try:
        records = latest_metadata_records(limit_runs=1)
        summary = summarize_payload(records)
    except HistoryError as exc:
        typer.secho(f"History error: {exc}", fg=typer.colors.RED, err=True)
        raise typer.Exit(2) from exc
    except OSError as exc:
        typer.secho(f"History read failed: {exc}", fg=typer.colors.RED, err=True)
        raise typer.Exit(2) from exc

    typer.echo("sync --metadata --dry-run (no network; nothing sent)")
    typer.echo(f"destination: {summary['destination']}")
    typer.echo(f"findings: {summary['finding_count']}")
    typer.echo(f"payload_bytes: {summary['payload_bytes']}")
    typer.echo("by_entity:")
    if summary["by_entity"]:
        for key, count in summary["by_entity"].items():
            typer.echo(f"  {key}: {count}")
    else:
        typer.echo("  (none)")
    typer.echo("by_severity:")
    if summary["by_severity"]:
        for key, count in summary["by_severity"].items():
            typer.echo(f"  {key}: {count}")
    else:
        typer.echo("  (none)")
    raise typer.Exit(0)


@app.command("setup-ner", help="Download the English spaCy model for optional NER.")
def setup_ner_cmd(
    model: Annotated[
        str,
        typer.Option("--model", help="spaCy model name to download."),
    ] = "en_core_web_sm",
) -> None:
    """Fetch the spaCy model for ``piilint[ner]`` (only scan-adjacent network path)."""
    if not ner_mod.ner_deps_available():
        typer.secho(
            'NER requires the optional extra. Install with: pip install "piilint[ner]" '
            "&& piilint setup-ner",
            fg=typer.colors.RED,
            err=True,
        )
        raise typer.Exit(2)
    typer.echo(f"Downloading spaCy model {model!r} (network)…")
    try:
        ner_mod.download_spacy_model(model)
    except Exception as exc:  # noqa: BLE001
        typer.secho(
            f"Failed to download spaCy model {model!r}: {exc}",
            fg=typer.colors.RED,
            err=True,
        )
        raise typer.Exit(2) from exc
    typer.secho(f"NER model ready: {model}", fg=typer.colors.GREEN)
    raise typer.Exit(0)


def run() -> None:
    """CLI entry that supports `piilint .` and `piilint scan .`."""
    import sys

    argv = sys.argv[1:]
    # `piilint --version`
    if argv == ["--version"] or argv == ["-V"]:
        typer.echo(__version__)
        raise SystemExit(0)
    # `piilint .` / `piilint PATH` → treat as scan when first token is not a command/flag
    known = {
        "scan",
        "baseline",
        "redact",
        "setup-ner",
        "report",
        "history",
        "sync",
        "--help",
        "-h",
        "help",
    }
    if argv and argv[0] not in known and not argv[0].startswith("-"):
        sys.argv = [sys.argv[0], "scan", *argv]
    elif not argv:
        sys.argv = [sys.argv[0], "--help"]
    app()


if __name__ == "__main__":
    run()
