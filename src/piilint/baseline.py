"""Baseline read/write and subtraction.

Chassis module: must not import recognizer logic (same boundary as adapters,
findings, and reporters).

Fingerprint tradeoff (see also ``findings.fingerprint_for``):
fingerprints deliberately exclude line numbers so ordinary edits do not
resurrect old findings. Side effect: moved/duplicated values may still match
by occurrence index, and an edit that only changes location will not surface
as "new."
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from piilint.findings import Finding

BASELINE_VERSION = 1


class BaselineError(Exception):
    """Invalid or missing baseline file."""


def write_baseline(path: Path | str, findings: list[Finding]) -> None:
    """Write a versioned baseline of sorted unique finding fingerprints.

    The baseline stores fingerprints only — never raw or masked PII values.
    """
    fingerprints = sorted({f.fingerprint for f in findings})
    payload: dict[str, Any] = {
        "version": BASELINE_VERSION,
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "fingerprints": fingerprints,
    }
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    # sort_keys for stable key order; fingerprints already sorted uniquely
    out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def load_baseline(path: Path | str) -> set[str]:
    """Load fingerprint set from a baseline file. Raises BaselineError on problems."""
    src = Path(path)
    if not src.is_file():
        raise BaselineError(f"Baseline file not found: {src}")
    try:
        data: Any = json.loads(src.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise BaselineError(f"Invalid baseline file {src}: {exc}") from exc

    if not isinstance(data, dict):
        raise BaselineError(f"Invalid baseline file {src}: expected a JSON object")

    version = data.get("version")
    if version != BASELINE_VERSION:
        raise BaselineError(
            f"Unsupported baseline version {version!r} in {src} (expected {BASELINE_VERSION})"
        )

    fps = data.get("fingerprints")
    if not isinstance(fps, list) or not all(isinstance(x, str) for x in fps):
        raise BaselineError(
            f"Invalid baseline file {src}: 'fingerprints' must be a list of strings"
        )
    return set(fps)


def subtract_baseline(findings: list[Finding], fingerprints: set[str]) -> list[Finding]:
    """Return findings whose fingerprint is not present in the baseline set."""
    return [f for f in findings if f.fingerprint not in fingerprints]
