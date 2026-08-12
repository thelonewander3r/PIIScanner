"""Typer CLI entrypoint."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console

from piilint import __version__
from piilint.config import ConfigError, load_config
from piilint.engine import scan_path
from piilint.findings import Severity
from piilint.reporters import render_console

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


def _fail_on_rank(name: str) -> int:
    mapping = {"never": 99, "low": 1, "medium": 2, "high": 3}
    if name not in mapping:
        raise typer.BadParameter("fail-on must be one of: high, medium, low, never")
    return mapping[name]


def _run_scan(
    path: Path,
    *,
    fail_on: str | None,
    min_confidence: float | None,
    enable_ip: bool | None,
    sample_rows: int | None,
    exclude: list[str] | None,
) -> None:
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

    try:
        threshold = _fail_on_rank(config.scan.fail_on)
    except typer.BadParameter as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        raise typer.Exit(2) from exc

    try:
        result = scan_path(path, config=config, sample_rows=sample_rows)
    except Exception as exc:  # noqa: BLE001 — unexpected errors are exit 2, not 1
        typer.secho(f"Scan failed: {exc}", fg=typer.colors.RED, err=True)
        raise typer.Exit(2) from exc

    render_console(result, console=Console())
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
    sample: Annotated[
        int | None,
        typer.Option("--sample", help="Sample at most N rows per tabular file."),
    ] = None,
    exclude: Annotated[
        list[str] | None,
        typer.Option("--exclude", help="Glob to exclude (repeatable; overrides config exclude)."),
    ] = None,
) -> None:
    _run_scan(
        path,
        fail_on=fail_on,
        min_confidence=min_confidence,
        enable_ip=enable_ip,
        sample_rows=sample,
        exclude=exclude,
    )


def run() -> None:
    """CLI entry that supports `piilint .` and `piilint scan .`."""
    import sys

    argv = sys.argv[1:]
    # `piilint --version`
    if argv == ["--version"] or argv == ["-V"]:
        typer.echo(__version__)
        raise SystemExit(0)
    # `piilint .` / `piilint PATH` → treat as scan when first token is not a command/flag
    known = {"scan", "baseline", "setup-ner", "--help", "-h", "help"}
    if argv and argv[0] not in known and not argv[0].startswith("-"):
        sys.argv = [sys.argv[0], "scan", *argv]
    elif not argv:
        sys.argv = [sys.argv[0], "--help"]
    app()


if __name__ == "__main__":
    run()
