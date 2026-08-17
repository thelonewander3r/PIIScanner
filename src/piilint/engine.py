"""Scan engine — runs recognizers over adapter units with column aggregation."""

from __future__ import annotations

import re
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from pathlib import Path
from time import perf_counter
from typing import Any

from piilint.adapters import ColumnBatch, Unit, default_adapters, select_adapter
from piilint.config import Config, default_config
from piilint.findings import EntityType, Finding, Location, Severity, mask_value
from piilint.policy import apply_policy
from piilint.recognizers import Match, RecognizerRegistry, build_default_registry
from piilint.walker import iter_files

MAX_COLUMN_EXAMPLES = 3

_DOB_CONTEXT_KEYS = frozenset(
    {
        "dob",
        "date_of_birth",
        "dateofbirth",
        "birth_date",
        "birthdate",
        "birthday",
        "born",
        "birth",
    }
)

_IBAN_HINT = re.compile(r"[A-Za-z]{2}\d{2}")


def _worth_running(entity: EntityType, text: str, context_key: str | None = None) -> bool:
    """Cheap character-class gates before invoking recognizer logic."""
    if entity == EntityType.EMAIL:
        return "@" in text
    if entity == EntityType.PHONE:
        return sum(1 for ch in text if ch.isdigit()) >= 10
    if entity == EntityType.SSN_US:
        return sum(1 for ch in text if ch.isdigit()) >= 9
    if entity == EntityType.SIN_CA:
        return sum(1 for ch in text if ch.isdigit()) >= 9
    if entity == EntityType.BSN_NL:
        return sum(1 for ch in text if ch.isdigit()) >= 9
    if entity == EntityType.NINO_UK:
        has_letter = any(ch.isalpha() for ch in text)
        has_digit = any(ch.isdigit() for ch in text)
        return has_letter and has_digit
    if entity == EntityType.CREDIT_CARD:
        return sum(1 for ch in text if ch.isdigit()) >= 13
    if entity == EntityType.IBAN:
        return len(text) >= 15 and _IBAN_HINT.search(text) is not None
    if entity == EntityType.DOB:
        if not context_key:
            return False
        key = context_key.lower().replace(" ", "_")
        return key in _DOB_CONTEXT_KEYS and any(ch.isdigit() for ch in text)
    if entity == EntityType.IP_ADDRESS:
        return "." in text or ":" in text
    return True


@dataclass(slots=True)
class ScanResult:
    findings: list[Finding]
    files_scanned: int
    elapsed_seconds: float


@dataclass
class _ColumnBucket:
    entity: EntityType
    severity: Severity | None
    confidence: float
    path: str
    column: str
    matched: int = 0
    non_null: int = 0
    examples: list[str] = field(default_factory=list)
    sampled: bool = False


def _unit_location(unit: Unit) -> Location:
    return Location(
        path=unit.path,
        line=unit.line,
        column=unit.column,
        cell=unit.cell,
        cell_part=unit.cell_part,
        row=unit.row,
    )


def _finding_from_match(
    match: Match,
    unit: Unit,
    *,
    occurrence_index: int,
) -> Finding:
    return Finding.create(
        entity=match.entity,
        raw_value=match.value,
        location=_unit_location(unit),
        confidence=match.confidence,
        severity=match.severity,
        occurrence_index=occurrence_index,
        sampled=unit.sampled,
    )


def scan_text_matches(
    text: str,
    recognizers: list[Any],
    *,
    context_key: str | None,
    min_confidence: float,
) -> list[Match]:
    matches: list[Match] = []
    for recognizer in recognizers:
        if not _worth_running(recognizer.entity, text, context_key):
            continue
        for match in recognizer.scan(text, context_key=context_key):
            if match.confidence < min_confidence:
                continue
            matches.append(match)
    return matches


def scan_unit_matches(
    unit: Unit,
    registry: RecognizerRegistry,
    *,
    min_confidence: float,
) -> list[Match]:
    return scan_text_matches(
        unit.text,
        registry.enabled_recognizers(),
        context_key=unit.context_key,
        min_confidence=min_confidence,
    )


def _record_aggregate_match(
    buckets: dict[tuple[str, str, EntityType], _ColumnBucket],
    *,
    path: str,
    column: str,
    match: Match,
    sampled: bool,
) -> None:
    key = (path, column, match.entity)
    bucket = buckets.get(key)
    if bucket is None:
        bucket = _ColumnBucket(
            entity=match.entity,
            severity=match.severity,
            confidence=match.confidence,
            path=path,
            column=column,
            sampled=sampled,
        )
        buckets[key] = bucket
    bucket.matched += 1
    bucket.confidence = max(bucket.confidence, match.confidence)
    if len(bucket.examples) < MAX_COLUMN_EXAMPLES:
        bucket.examples.append(match.value)
    bucket.sampled = bucket.sampled or sampled


def _flush_buckets(
    buckets: dict[tuple[str, str, EntityType], _ColumnBucket],
    occurrence_counters: dict[tuple[str, str, str], int],
) -> list[Finding]:
    findings: list[Finding] = []
    for bucket in buckets.values():
        if bucket.matched == 0:
            continue
        example = bucket.examples[0] if bucket.examples else "***"
        key = (bucket.path, bucket.entity.value, example)
        idx = occurrence_counters.get(key, 0)
        occurrence_counters[key] = idx + 1
        extras = {
            "examples": [mask_value(v, bucket.entity) for v in bucket.examples],
            "column_summary": (
                f"{bucket.matched}/{bucket.non_null} non-null rows matched"
                if bucket.non_null
                else f"{bucket.matched} matched"
            ),
        }
        findings.append(
            Finding.create(
                entity=bucket.entity,
                raw_value=example,
                location=Location(path=bucket.path, column=bucket.column),
                confidence=bucket.confidence,
                severity=bucket.severity,
                occurrence_index=idx,
                matched_count=bucket.matched,
                total_non_null=bucket.non_null or None,
                sampled=bucket.sampled,
                extras=extras,
            )
        )
    return findings


def _iter_adapter_stream(
    adapter: Any,
    file_path: Path,
    *,
    rel: str,
    sample_rows: int | None,
) -> tuple[str, Iterator[Any]]:
    """Return ('batches'|'units', iterator)."""
    batch_fn: Callable[..., Any] | None = getattr(adapter, "iter_column_batches", None)
    if batch_fn is not None:
        try:
            return "batches", batch_fn(file_path, rel_path=rel, sample_rows=sample_rows)
        except TypeError:
            return "batches", batch_fn(file_path, rel_path=rel)
    try:
        return "units", adapter.iter_units(file_path, rel_path=rel, sample_rows=sample_rows)
    except TypeError:
        return "units", adapter.iter_units(file_path, rel_path=rel)


def enable_optional_ner(config: Config) -> None:
    """Turn on PERSON/ADDRESS for a --ner run.

    Scan and redact both run matches through ``apply_policy``, which drops
    disabled entities. Enabling recognizers alone is not enough — the config
    used for policy must flip too, or PERSON/ADDRESS spans are found then
    discarded (xlsx redact --ner wrote phones only).
    """
    config.entity_enabled[EntityType.PERSON] = True
    config.entity_enabled[EntityType.ADDRESS] = True


def _build_registry(config: Config, *, enable_ner: bool = False) -> RecognizerRegistry:
    ner_entities = (EntityType.PERSON, EntityType.ADDRESS)
    ner_wanted = enable_ner or any(config.is_entity_enabled(e) for e in ner_entities)
    if ner_wanted:
        # Fail fast with a clear message before scanning (no silent skip).
        from piilint.recognizers.ner import require_ner_ready

        require_ner_ready()

    registry = build_default_registry(
        default_phone_region=config.scan.phone_region,
        phone_regions=list(config.scan.phone_regions),
        enable_ip=config.is_entity_enabled(EntityType.IP_ADDRESS),
        enable_ner=False,
        enable_nino_uk=config.is_entity_enabled(EntityType.NINO_UK),
        enable_bsn_nl=config.is_entity_enabled(EntityType.BSN_NL),
    )
    # Apply entity enable/disable from config; --ner forces PERSON+ADDRESS on for the run.
    for entity in list(EntityType):
        recognizer = registry.get(entity)
        if recognizer is None:
            continue
        enabled = config.is_entity_enabled(entity)
        if entity in ner_entities and enable_ner:
            enabled = True
        registry.enable(entity, enabled)
    return registry


def scan_path(
    target: Path,
    *,
    config: Config | None = None,
    min_confidence: float | None = None,
    enable_ip: bool | None = None,
    enable_ner: bool = False,
    phone_region: str | None = None,
    phone_regions: list[str] | None = None,
    include: list[str] | None = None,
    exclude: list[str] | None = None,
    sample_rows: int | None = None,
    only_paths: list[Path] | None = None,
) -> ScanResult:
    """Scan a file or directory.

    Prefer passing a resolved ``Config``. Legacy kwargs override that config when
    provided (kept for unit tests / callers from Phase 1–2).

    ``only_paths`` restricts the walk to an explicit allowlist (e.g. git-staged
    files). Pass an empty list to scan zero files.
    """
    started = perf_counter()
    cfg = config.copy() if config is not None else default_config()
    if min_confidence is not None:
        cfg.scan.min_confidence = min_confidence
    if enable_ip is not None:
        cfg.entity_enabled[EntityType.IP_ADDRESS] = enable_ip
    if enable_ner:
        enable_optional_ner(cfg)
    if phone_region is not None:
        cfg.scan.phone_region = phone_region
    if phone_regions is not None:
        cfg.scan.phone_regions = [
            r.strip().upper() for r in phone_regions if isinstance(r, str) and r.strip()
        ]
    if exclude is not None:
        cfg.scan.exclude = list(exclude)

    # Pre-policy floor: keep matches that might pass after downweight adjustments
    # are not needed upward; downweight only lowers confidence. Use config floor
    # for recognizer gating, then policy re-applies after downweight.
    effective_min = cfg.scan.min_confidence

    root = target.resolve()
    registry = _build_registry(cfg, enable_ner=enable_ner)
    recognizers = registry.enabled_recognizers()
    adapters = default_adapters()
    findings: list[Finding] = []
    occurrence_counters: dict[tuple[str, str, str], int] = {}
    line_texts: dict[tuple[str, int], str] = {}
    files_scanned = 0

    base = root if root.is_dir() else root.parent
    for file_path in iter_files(
        root,
        include=include,
        exclude=cfg.scan.exclude or None,
        only_paths=only_paths,
    ):
        adapter = select_adapter(file_path, adapters)
        if adapter is None:
            continue
        try:
            rel = file_path.relative_to(base).as_posix()
        except ValueError:
            rel = file_path.name

        mode, stream = _iter_adapter_stream(adapter, file_path, rel=rel, sample_rows=sample_rows)
        buckets: dict[tuple[str, str, EntityType], _ColumnBucket] = {}
        non_null_by_column: dict[str, int] = {}
        saw_item = False

        if mode == "batches":
            for batch in stream:
                assert isinstance(batch, ColumnBatch)
                saw_item = True
                non_null_by_column[batch.column] = non_null_by_column.get(batch.column, 0) + len(
                    batch.values
                )
                for text in batch.values:
                    for match in scan_text_matches(
                        text,
                        recognizers,
                        context_key=batch.column,
                        min_confidence=effective_min,
                    ):
                        _record_aggregate_match(
                            buckets,
                            path=batch.path,
                            column=batch.column,
                            match=match,
                            sampled=batch.sampled,
                        )
        else:
            for unit in stream:
                assert isinstance(unit, Unit)
                saw_item = True
                if unit.aggregate and unit.column is not None:
                    non_null_by_column[unit.column] = non_null_by_column.get(unit.column, 0) + 1
                matches = scan_text_matches(
                    unit.text,
                    recognizers,
                    context_key=unit.context_key,
                    min_confidence=effective_min,
                )
                if unit.aggregate and unit.column is not None:
                    for match in matches:
                        _record_aggregate_match(
                            buckets,
                            path=unit.path,
                            column=unit.column,
                            match=match,
                            sampled=unit.sampled,
                        )
                else:
                    if unit.line is not None:
                        line_texts[(unit.path, unit.line)] = unit.text
                    for match in matches:
                        occ_key = (unit.path, match.entity.value, match.value)
                        idx = occurrence_counters.get(occ_key, 0)
                        occurrence_counters[occ_key] = idx + 1
                        findings.append(_finding_from_match(match, unit, occurrence_index=idx))

        if saw_item:
            files_scanned += 1
            for bucket in buckets.values():
                bucket.non_null = non_null_by_column.get(bucket.column, bucket.matched)
            findings.extend(_flush_buckets(buckets, occurrence_counters))

    findings = apply_policy(findings, cfg, line_texts=line_texts)
    return ScanResult(
        findings=findings,
        files_scanned=files_scanned,
        elapsed_seconds=perf_counter() - started,
    )
