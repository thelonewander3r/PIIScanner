"""Benchmark precision/recall gate against the synthetic corpus manifest."""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path

import pytest
import yaml

from piilint.engine import scan_path
from piilint.findings import EntityType

CORPUS_ROOT = Path(__file__).parent / "corpus"
MANIFEST_PATH = CORPUS_ROOT / "corpus.yaml"

HIGH_SEVERITY = {EntityType.CREDIT_CARD, EntityType.SSN_US, EntityType.IBAN}
CORE_ENTITIES = {
    EntityType.EMAIL,
    EntityType.PHONE,
    EntityType.SSN_US,
    EntityType.CREDIT_CARD,
    EntityType.IBAN,
}

PRECISION_FLOOR = 0.95
RECALL_FLOOR = 0.85


def _load_manifest() -> dict:
    with MANIFEST_PATH.open(encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def _metrics() -> tuple[dict[str, float], dict[str, float], float, float]:
    manifest = _load_manifest()
    expected_counts: dict[EntityType, int] = defaultdict(int)
    for case in manifest["cases"]:
        for exp in case.get("expected") or []:
            expected_counts[EntityType(exp["entity"])] += int(exp["count"])

    # Scan each case file individually so path expectations stay local.
    detected_counts: dict[EntityType, int] = defaultdict(int)
    false_positives: dict[EntityType, int] = defaultdict(int)

    for case in manifest["cases"]:
        rel = case["path"]
        target = CORPUS_ROOT / rel
        result = scan_path(target)
        expected_by_entity = {
            EntityType(e["entity"]): int(e["count"]) for e in (case.get("expected") or [])
        }
        found_by_entity: dict[EntityType, int] = defaultdict(int)
        for finding in result.findings:
            found_by_entity[finding.entity] += 1

        all_entities = set(expected_by_entity) | set(found_by_entity)
        for entity in all_entities:
            exp = expected_by_entity.get(entity, 0)
            got = found_by_entity.get(entity, 0)
            detected_counts[entity] += min(exp, got)
            if got > exp:
                false_positives[entity] += got - exp

    per_entity_precision: dict[str, float] = {}
    per_entity_recall: dict[str, float] = {}

    for entity in CORE_ENTITIES | HIGH_SEVERITY:
        tp = detected_counts[entity]
        fp = false_positives[entity]
        exp = expected_counts[entity]
        precision = tp / (tp + fp) if (tp + fp) else 1.0
        recall = tp / exp if exp else 1.0
        per_entity_precision[entity.value] = precision
        per_entity_recall[entity.value] = recall

    # High-severity micro-averaged precision
    hs_tp = sum(detected_counts[e] for e in HIGH_SEVERITY)
    hs_fp = sum(false_positives[e] for e in HIGH_SEVERITY)
    high_precision = hs_tp / (hs_tp + hs_fp) if (hs_tp + hs_fp) else 1.0

    # Core-entity micro-averaged recall
    core_tp = sum(detected_counts[e] for e in CORE_ENTITIES)
    core_exp = sum(expected_counts[e] for e in CORE_ENTITIES)
    core_recall = core_tp / core_exp if core_exp else 1.0

    return per_entity_precision, per_entity_recall, high_precision, core_recall


def test_benchmark_gate(capsys: pytest.CaptureFixture[str]) -> None:
    per_p, per_r, high_precision, core_recall = _metrics()

    print("\n=== piilint benchmark ===")
    for entity in sorted(set(per_p) | set(per_r)):
        print(f"  {entity}: precision={per_p[entity]:.3f} recall={per_r[entity]:.3f}")
    print(f"  HIGH-severity precision: {high_precision:.3f} (floor {PRECISION_FLOOR})")
    print(f"  CORE recall:             {core_recall:.3f} (floor {RECALL_FLOOR})")

    # Ensure metrics appear in CI logs even under pytest capture.
    captured = capsys.readouterr()
    print(captured.out, end="")

    assert high_precision >= PRECISION_FLOOR, (
        f"High-severity precision {high_precision:.3f} < {PRECISION_FLOOR}"
    )
    assert core_recall >= RECALL_FLOOR, f"Core recall {core_recall:.3f} < {RECALL_FLOOR}"


def test_hard_negatives_clean() -> None:
    result = scan_path(CORPUS_ROOT / "text" / "hard_negatives.txt")
    assert result.findings == []
