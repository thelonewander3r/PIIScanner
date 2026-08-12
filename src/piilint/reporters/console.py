"""Console reporter (Rich) — grouped by file, severity-colored table, totals line."""

from __future__ import annotations

from collections import Counter

from rich.console import Console
from rich.markup import escape
from rich.table import Table

from piilint.engine import ScanResult
from piilint.findings import Finding, Severity


def render_console(
    result: ScanResult,
    *,
    console: Console | None = None,
    show_matches: bool = False,
) -> None:
    """Render findings to a Rich console.

    When ``show_matches`` is True, the Sample column shows the normalized matched
    value instead of the masked sample (local triage only). Callers must refuse
    this flag when ``CI=true``.
    """
    out = console or Console(stderr=False)
    if not result.findings:
        out.print(
            f"[green]No PII findings[/green] — "
            f"{result.files_scanned} files scanned in {result.elapsed_seconds:.1f}s"
        )
        return

    by_file: dict[str, list[Finding]] = {}
    for finding in result.findings:
        by_file.setdefault(finding.location.path, []).append(finding)

    for path in sorted(by_file):
        out.print(f"\n[bold]{path}[/bold]")
        table = Table(show_header=True, header_style="bold", box=None, pad_edge=False)
        table.add_column("Sev")
        table.add_column("Entity")
        table.add_column("Location")
        table.add_column("Sample")
        table.add_column("Conf")
        for f in by_file[path]:
            sev_style = {
                Severity.HIGH: "red",
                Severity.MEDIUM: "yellow",
                Severity.LOW: "blue",
            }[f.severity]
            loc = f.location.label().removeprefix(f"{path} · ").removeprefix(path)
            if not loc:
                loc = f"line {f.location.line}" if f.location.line else "-"
            sample = f.normalized_value if show_matches and f.normalized_value else f.masked_sample
            if f.matched_count > 1:
                summary = f.extras.get("column_summary")
                if summary:
                    sample = f"{sample} ({summary})"
            if f.sampled:
                sample = f"{sample} [sampled]"
            table.add_row(
                f"[{sev_style}]{f.severity.value}[/{sev_style}]",
                f.entity.value,
                loc,
                escape(sample),
                f"{f.confidence:.2f}",
            )
        out.print(table)

    counts = Counter(f.severity for f in result.findings)
    out.print(
        f"\n{counts[Severity.HIGH]} high · {counts[Severity.MEDIUM]} medium · "
        f"{counts[Severity.LOW]} low — {result.files_scanned} files scanned "
        f"in {result.elapsed_seconds:.1f}s"
    )
