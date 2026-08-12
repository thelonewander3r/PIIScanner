# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

<!-- Post-0.1.0 notes go here. -->

## [0.1.0] — TBD (tag day)

First public release. **Not on PyPI until** maintainer go → `git tag v0.1.0` → OIDC trusted publisher via `.github/workflows/release.yml`.

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

