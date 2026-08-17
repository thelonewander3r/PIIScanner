# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.2.0] — 2026-08-17

Prep for the next PyPI release of `piilint`. **Not tagged or published** until Emanuel's explicit go. `0.1.0` remains the published version on [PyPI](https://pypi.org/p/piilint).

### Added

- Sprint 15 Slice B (local MVP, shipped on `main` via [#38](https://github.com/thelonewander3r/PIIScanner/pull/38)): metadata-only report/history/sync dry-run — `piilint report --metadata-only` (auto-records local SQLite), `piilint history --since`, `piilint sync --metadata --dry-run` (no network). Trust-boundary fields only; default scan path unchanged. Tracking [#37](https://github.com/thelonewander3r/PIIScanner/issues/37).
- Sprint 14 (design): [`docs/TEAM_LAYER.md`](./docs/TEAM_LAYER.md) — team / findings-metadata layer design (trust boundary, MVP slice order A→B→C, CLI proposals, open questions). Docs only; no SaaS/backend. Tracking [#32](https://github.com/thelonewander3r/PIIScanner/issues/32).
- Sprint 13: `.docx` scan under optional `piilint[office]` (`python-docx`); paragraph + table + header/footer text; legacy `.doc` not supported; missing extra skips with the same one-time stderr hint as xlsx/PDF.
- `piilint redact` stretch: cleaned `.docx` copies (paragraph/table/header/footer string runs via `paragraph.text = …`; sources never modified).
- Sprint 12 locale coverage: multi-region phones via `scan.phone_region` + `scan.phone_regions`; national IDs `SIN_CA` (on, Luhn), `NINO_UK` (off, context-required), `BSN_NL` (off, 11-proef). Detection aid only — not legal ID verification / not GDPR-HIPAA-PCI compliance.
- Optional `piilint[office]` (`openpyxl` + `pypdf` + `python-docx`): scan `.xlsx`/`.xlsm`, `.docx`, and PDF **embedded text** (no OCR / no `.doc`); missing extra skips those files with a stderr hint.
- `piilint redact` stretch: cleaned `.xlsx` copies. PDF redact deferred.
- `piilint redact PATH -o OUT_DIR` — write cleaned **copies** with PII spans rewritten via existing `mask_value` (text + json/jsonl + csv/tsv; no in-place; no new base deps).
- Example org policy packs under `examples/policies/` (`strict-ci`, `data-eng`, `open-source-lib`) + disclaimer README.
- `piilint redact` now also cleans **`.ipynb`** (source + outputs) and **`.parquet`** string columns (Sprint 10).

## [0.1.0] — 2026-08-12

First public release on [PyPI](https://pypi.org/p/piilint). Published via OIDC trusted publisher (`.github/workflows/release.yml`) after tag `v0.1.0`.

### Added

- Local-first CLI `piilint` (Phases 0–1): deterministic recognizers (email, phone, SSN, credit card, IBAN, IP), text adapter, walker with `.gitignore` / `.piiignore`, console reporter, synthetic benchmark corpus + CI precision/recall gates, suite-wide network block.
- Tabular + notebook adapters (Phase 2): CSV/TSV, JSON/JSONL, Parquet, `.ipynb` (source **and** outputs), column aggregation, DOB with context-key signal, sampling/size guards.
- Policy & noise controls (Phase 3): `piilint.toml` / `[tool.piilint]` precedence, allowlists, inline `# piilint: ignore`, entity enable/severity overrides, test-data downweight, `--fail-on` exit codes 0/1/2.
- Baseline + staged mode (Phase 4): `piilint baseline`, `--baseline` subtraction (fingerprint without line numbers), `--staged` via git index.
- Reporters (Phase 5): `--format json` (schema_version 1 + `config_hash`), `--format sarif` (SARIF 2.1.0), `--show-matches` refused when `CI=true`.
- Distribution (Phase 6): CI matrix workflow, OIDC PyPI release workflow (unused until tag), `.pre-commit-hooks.yaml`, composite GitHub Action (`action.yml`), install docs.
- Optional NER (`piilint[ner]`): Presidio/spaCy PERSON + ADDRESS, `piilint setup-ner`, `--ner` flag (off by default).
- Launch collateral: CONTRIBUTING, SECURITY, examples pointer, README five-minute path and Demo section.

### Notes

- Optional NER is available as `piilint[ner]` (not pulled by the base install).
- Package name is `piilint` (`piiscan` was taken on PyPI).
