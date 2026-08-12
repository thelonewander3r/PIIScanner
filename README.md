# piilint

Local-first PII scanner for the files developers actually commit and send — notebooks, CSV, JSON, Parquet, and source code. **Nothing leaves your machine.**

> **Disclaimer:** piilint helps you find sensitive data before it leaks. It is a detection aid, not a compliance certification, and cannot guarantee that all sensitive data is found. It does not make anyone GDPR/HIPAA/PCI compliant.

**Package name:** `piilint` (PyPI name `piiscan` was already taken).

## Install (dev)

```bash
uv sync --extra dev
uv run piilint --version
uv run piilint tests/corpus/text
```

## Configuration (Phase 3)

Precedence (**highest wins**): CLI flags → `piilint.toml` at the scan root → `[tool.piilint]` in `pyproject.toml` → built-in defaults.

```toml
# piilint.toml
[scan]
fail_on = "high"
min_confidence = 0.6
exclude = ["tests/fixtures/**"]

[entities]
ip_address = false
[entities.email]
severity = "medium"

[allowlist]
values  = ["support@mycompany.com"]
domains = ["example.com", "mycompany.dev"]
```

- **`.piiignore`** — gitignore-syntax path excludes (combined with `.gitignore`).
- **Inline suppressions** (text/code lines): `# piilint: ignore` or `# piilint: ignore[EMAIL]` (comma-list). Not applied to tabular/column-aggregated findings in v0.
- **Allowlists** — exact normalized values and email domains drop matching findings.
- **Test-data downweight** — obvious fixtures (example.com, 555-01xx, 4111…, RFC5737 IPs) get −0.4 confidence and severity capped at low, then `min_confidence` is re-applied.

## Baseline + staged (Phase 4)

Adopt without fixing history first, and scan only what is about to land in git.

```bash
# Capture current findings as a baseline (fingerprints only — never raw PII)
uv run piilint baseline . -o piilint-baseline.json

# Report NEW findings only (subtract known fingerprints)
uv run piilint . --baseline piilint-baseline.json

# Pre-commit friendly: scan only git-staged files (Added/Copied/Modified/Renamed)
uv run piilint . --staged
```

**Fingerprint design:** SHA-256(relative path, entity, normalized-value hash, occurrence index).
Line numbers are **excluded** so ordinary edits do not resurrect old findings.

**Tradeoff:** an edit that only moves a value to a different line will not reappear as “new.”
Moved or duplicated values may still match by occurrence index. Commit a fresh baseline when
you intentionally accept a new set of findings.

Exit codes: `0` clean / nothing staged · `1` findings ≥ `--fail-on` · `2` usage/config/git error.

## Output formats (Phase 5)

Default output is a Rich **console** report (grouped by file → severity-colored table → totals).

```bash
# Machine-readable JSON (schema_version 1) — masked samples + value hashes only
uv run piilint . --format json

# SARIF 2.1.0 for GitHub code scanning (upload via github/codeql-action/upload-sarif)
uv run piilint . --format sarif > piilint.sarif

# Compose with baseline / staged / fail-on
uv run piilint . --format json --baseline piilint-baseline.json --fail-on high
```

JSON includes a `config_hash`: SHA-256 of a canonical JSON snapshot of the **effective**
scan config fields that affect detection/policy (`fail_on`, `min_confidence`, `exclude`,
`entity_enabled`, `severity_overrides`, allowlists, `phone_region`). Paths and timestamps
are excluded so the hash is stable across identical policy runs.

`--show-matches` unmasks the console Sample column for local triage only. It is **refused**
when `CI=true` (exit 2) and does not apply to JSON/SARIF (those formats never emit raw PII).

## Status

Phases 0–5 complete: deterministic recognizers, text + tabular + notebook adapters, console / JSON / SARIF reporters, synthetic benchmark corpus + CI gate, config/policy/noise controls, baseline subtraction, and `--staged` mode.

## Pairing

This is **not** a secrets scanner. Pair with [gitleaks](https://github.com/gitleaks/gitleaks) / trufflehog for API keys and tokens.

## License

Apache-2.0

## Corpus note

`tests/corpus/` contains **100% synthetic** labeled data, generated for tests. It never contains real personal data.
