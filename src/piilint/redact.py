"""Write cleaned file copies by rewriting PII spans (base wheel, no new deps).

Uses the same recognizers + ``mask_value`` as scan. Adapters/recognizers stay
untouched — orchestration lives here and in the CLI.
"""

from __future__ import annotations

import csv
import io
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from piilint.adapters.text import TextAdapter, looks_binary
from piilint.config import Config
from piilint.engine import _build_registry, scan_text_matches
from piilint.findings import EntityType, Finding, Location, mask_value
from piilint.policy import apply_policy
from piilint.recognizers import Match, RecognizerRegistry
from piilint.walker import iter_files

# Required Sprint 9 formats. Notebooks/parquet are follow-ups.
_TEXT = TextAdapter()


class RedactError(ValueError):
    """Usage / safety error for the redact command (maps to exit 2)."""


@dataclass(frozen=True, slots=True)
class RedactResult:
    files_written: int
    files_skipped: int
    spans_redacted: int


@dataclass(frozen=True, slots=True)
class _Span:
    start: int
    end: int
    entity: EntityType
    value: str


def _supported(path: Path) -> str | None:
    """Return adapter kind or None if unsupported for redact v1."""
    suffix = path.suffix.lower()
    if suffix in {".csv", ".tsv"}:
        return "csv"
    if suffix in {".json", ".jsonl"}:
        return "json"
    if _TEXT.supports(path):
        return "text"
    return None


def _line_index(text: str, offset: int) -> int:
    return text.count("\n", 0, offset) + 1


def _dedupe_spans(spans: list[_Span]) -> list[_Span]:
    """Keep non-overlapping spans (earlier start wins; ties → longer span)."""
    ordered = sorted(spans, key=lambda s: (s.start, -(s.end - s.start)))
    kept: list[_Span] = []
    cursor = -1
    for span in ordered:
        if span.start < cursor:
            continue
        if span.end <= span.start:
            continue
        kept.append(span)
        cursor = span.end
    return kept


def apply_span_replacements(text: str, spans: list[_Span]) -> str:
    """Replace spans with ``mask_value`` results (reverse offset order)."""
    kept = _dedupe_spans(spans)
    out = text
    for span in sorted(kept, key=lambda s: s.start, reverse=True):
        replacement = mask_value(span.value, span.entity)
        out = out[: span.start] + replacement + out[span.end :]
    return out


def _filter_matches(
    text: str,
    matches: list[Match],
    *,
    config: Config,
    rel_path: str,
    context_key: str | None = None,
) -> list[_Span]:
    """Convert matches ? findings, apply policy, return surviving spans."""
    if not matches:
        return []
    findings: list[Finding] = []
    line_texts: dict[tuple[str, int], str] = {}
    for idx, line in enumerate(text.split("\n"), start=1):
        line_texts[(rel_path, idx)] = line

    for i, match in enumerate(matches):
        line_no = _line_index(text, match.start)
        findings.append(
            Finding.create(
                entity=match.entity,
                raw_value=match.value,
                location=Location(
                    path=rel_path,
                    line=line_no,
                    column=context_key,
                    offset=match.start,
                ),
                confidence=match.confidence,
                severity=match.severity,
                occurrence_index=i,
            )
        )
    kept = apply_policy(findings, config, line_texts=line_texts)
    offset_entity = {
        (f.location.offset, f.entity) for f in kept if f.location.offset is not None
    }
    return [
        _Span(start=m.start, end=m.end, entity=m.entity, value=m.value)
        for m in matches
        if (m.start, m.entity) in offset_entity
    ]


def redact_plain_text(
    text: str,
    *,
    registry: RecognizerRegistry,
    config: Config,
    rel_path: str,
    context_key: str | None = None,
) -> tuple[str, int]:
    """Redact PII spans in a plain string. Returns (new_text, span_count)."""
    matches = scan_text_matches(
        text,
        registry.enabled_recognizers(),
        context_key=context_key,
        min_confidence=config.scan.min_confidence,
    )
    spans = _filter_matches(
        text, matches, config=config, rel_path=rel_path, context_key=context_key
    )
    if not spans:
        return text, 0
    return apply_span_replacements(text, spans), len(_dedupe_spans(spans))


def _read_text_file(path: Path) -> tuple[str, bool]:
    """Return (text, had_bom). Normalizes newlines to \\n for scanning; caller may rewrite."""
    data = path.read_bytes()
    had_bom = data.startswith(b"\xef\xbb\xbf")
    if had_bom:
        data = data[3:]
    if looks_binary(data[:8192]):
        raise RedactError(f"Refusing binary file: {path}")
    text = data.decode("utf-8", errors="replace")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    return text, had_bom


def _write_text(path: Path, text: str, *, had_bom: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = text
    data = payload.encode("utf-8")
    if had_bom:
        data = b"\xef\xbb\xbf" + data
    path.write_bytes(data)


def _redact_json_value(
    value: Any,
    *,
    registry: RecognizerRegistry,
    config: Config,
    rel_path: str,
    key: str | None,
) -> tuple[Any, int]:
    count = 0
    if isinstance(value, dict):
        out: dict[Any, Any] = {}
        for child_key, child in value.items():
            new_child, n = _redact_json_value(
                child,
                registry=registry,
                config=config,
                rel_path=rel_path,
                key=str(child_key),
            )
            out[child_key] = new_child
            count += n
        return out, count
    if isinstance(value, list):
        items = []
        for item in value:
            new_item, n = _redact_json_value(
                item, registry=registry, config=config, rel_path=rel_path, key=key
            )
            items.append(new_item)
            count += n
        return items, count
    if value is None or isinstance(value, (int, float, bool)):
        return value, 0
    text = str(value)
    if not text.strip():
        return value, 0
    redacted, n = redact_plain_text(
        text,
        registry=registry,
        config=config,
        rel_path=rel_path,
        context_key=key,
    )
    return redacted, n


def _redact_json_file(
    path: Path,
    *,
    registry: RecognizerRegistry,
    config: Config,
    rel_path: str,
) -> tuple[str, int]:
    raw = path.read_text(encoding="utf-8", errors="replace")
    if path.suffix.lower() == ".jsonl":
        lines_out: list[str] = []
        total = 0
        for line in raw.splitlines():
            if not line.strip():
                lines_out.append(line)
                continue
            try:
                data = json.loads(line)
            except json.JSONDecodeError:
                redacted, n = redact_plain_text(
                    line, registry=registry, config=config, rel_path=rel_path
                )
                lines_out.append(redacted)
                total += n
                continue
            new_data, n = _redact_json_value(
                data, registry=registry, config=config, rel_path=rel_path, key=None
            )
            lines_out.append(json.dumps(new_data, ensure_ascii=False, separators=(",", ":")))
            total += n
        # Preserve trailing newline if original had one
        body = "\n".join(lines_out)
        if raw.endswith("\n"):
            body += "\n"
        return body, total

    data = json.loads(raw)
    new_data, n = _redact_json_value(
        data, registry=registry, config=config, rel_path=rel_path, key=None
    )
    return json.dumps(new_data, ensure_ascii=False, indent=2) + "\n", n


def _redact_csv_file(
    path: Path,
    *,
    registry: RecognizerRegistry,
    config: Config,
    rel_path: str,
) -> tuple[str, int]:
    delimiter = "\t" if path.suffix.lower() == ".tsv" else ","
    text = path.read_text(encoding="utf-8", errors="replace")
    # Strip BOM for parsing
    if text.startswith("\ufeff"):
        text = text[1:]
    reader = csv.reader(io.StringIO(text), delimiter=delimiter)
    rows = list(reader)
    if not rows:
        return text, 0
    headers = rows[0]
    total = 0
    out_rows: list[list[str]] = [headers]
    for row in rows[1:]:
        new_row: list[str] = []
        for idx, cell in enumerate(row):
            header = headers[idx] if idx < len(headers) else None
            if not cell:
                new_row.append(cell)
                continue
            redacted, n = redact_plain_text(
                cell,
                registry=registry,
                config=config,
                rel_path=rel_path,
                context_key=header,
            )
            new_row.append(redacted)
            total += n
        out_rows.append(new_row)
    buf = io.StringIO()
    writer = csv.writer(buf, delimiter=delimiter, lineterminator="\n")
    writer.writerows(out_rows)
    return buf.getvalue(), total


def _safe_out_path(out_root: Path, rel: str) -> Path:
    """Resolve destination under out_root; refuse escapes."""
    # Normalize rel to forbid absolute / drive / .. escape
    rel_path = Path(rel)
    if rel_path.is_absolute() or bool(rel_path.drive):
        raise RedactError(f"Refusing absolute relative path: {rel}")
    dest = (out_root / rel_path).resolve()
    try:
        dest.relative_to(out_root.resolve())
    except ValueError as exc:
        raise RedactError(f"Refusing path outside output dir: {rel}") from exc
    return dest


def redact_tree(
    target: Path,
    output_dir: Path,
    *,
    config: Config,
    enable_ner: bool = False,
) -> RedactResult:
    """Redact supported files under ``target`` into ``output_dir`` (mirrors relpaths)."""
    if not target.exists():
        raise RedactError(f"Path not found: {target}")
    out_root = output_dir.resolve()
    out_root.mkdir(parents=True, exist_ok=True)

    root = target.resolve()
    base = root if root.is_dir() else root.parent
    registry = _build_registry(config, enable_ner=enable_ner)

    written = 0
    skipped = 0
    spans = 0

    for file_path in iter_files(root, exclude=config.scan.exclude or None):
        kind = _supported(file_path)
        if kind is None:
            skipped += 1
            continue
        try:
            rel = file_path.relative_to(base).as_posix()
        except ValueError:
            rel = file_path.name
        dest = _safe_out_path(out_root, rel)

        try:
            if kind == "text":
                text, had_bom = _read_text_file(file_path)
                new_text, n = redact_plain_text(
                    text, registry=registry, config=config, rel_path=rel
                )
                _write_text(dest, new_text, had_bom=had_bom)
            elif kind == "json":
                new_text, n = _redact_json_file(
                    file_path, registry=registry, config=config, rel_path=rel
                )
                _write_text(dest, new_text)
            else:
                new_text, n = _redact_csv_file(
                    file_path, registry=registry, config=config, rel_path=rel
                )
                _write_text(dest, new_text)
        except (OSError, json.JSONDecodeError, csv.Error, UnicodeError) as exc:
            raise RedactError(f"Failed to redact {rel}: {exc}") from exc

        written += 1
        spans += n

    return RedactResult(files_written=written, files_skipped=skipped, spans_redacted=spans)
