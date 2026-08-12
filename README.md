# piilint

[![CI](https://github.com/thelonewander3r/PIIScanner/actions/workflows/ci.yml/badge.svg)](https://github.com/thelonewander3r/PIIScanner/actions/workflows/ci.yml)

Local-first PII scanner for the files developers actually commit and send — notebooks, CSV, JSON, Parquet, and source code. **Nothing leaves your machine.**

> **Disclaimer:** piilint helps you find sensitive data before it leaks. It is a detection aid, not a compliance certification, and cannot guarantee that all sensitive data is found. It does not make anyone GDPR/HIPAA/PCI compliant.

**Package name:** `piilint` (PyPI name `piiscan` was already taken).

**Repo:** https://github.com/thelonewander3r/PIIScanner

## Install

```bash
# recommended for CLI use
pipx install piilint
# or
uvx piilint --version

# classic
pip install piilint
```

Until the first PyPI release is cut, install from a clone / git:

```bash
pipx install git+https://github.com/thelonewander3r/PIIScanner.git
# or from a local checkout
uv sync --extra dev
uv run piilint --version
```

## Quick start

```bash
piilint --version
piilint tests/corpus/text
piilint . --fail-on high
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
piilint baseline . -o piilint-baseline.json

# Report NEW findings only (subtract known fingerprints)
piilint . --baseline piilint-baseline.json

# Pre-commit friendly: scan only git-staged files (Added/Copied/Modified/Renamed)
piilint . --staged
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
piilint . --format json

# SARIF 2.1.0 for GitHub code scanning (upload via github/codeql-action/upload-sarif)
piilint . --format sarif > piilint.sarif

# Compose with baseline / staged / fail-on
piilint . --format json --baseline piilint-baseline.json --fail-on high
```

JSON includes a `config_hash`: SHA-256 of a canonical JSON snapshot of the **effective**
scan config fields that affect detection/policy (`fail_on`, `min_confidence`, `exclude`,
`entity_enabled`, `severity_overrides`, allowlists, `phone_region`). Paths and timestamps
are excluded so the hash is stable across identical policy runs.

`--show-matches` unmasks the console Sample column for local triage only. It is **refused**
when `CI=true` (exit 2) and does not apply to JSON/SARIF (those formats never emit raw PII).

## Pre-commit hook (Phase 6)

This repo ships a pre-commit hook definition in [`.pre-commit-hooks.yaml`](./.pre-commit-hooks.yaml).

Add to your consuming project's `.pre-commit-config.yaml`:

```yaml
repos:
  - repo: https://github.com/thelonewander3r/PIIScanner
    rev: v0.1.0   # pin to a release tag when available
    hooks:
      - id: piilint
        # Default args from the hook repo: --staged --fail-on medium
        # Override fail-on (or drop --staged) by replacing args:
        # args: ["--staged", "--fail-on", "high"]
```

Notes:

- The hook runs `piilint --staged` and sets `pass_filenames: false` so pre-commit does not append paths (staged mode reads the git index).
- `fail-on` defaults to **medium** in the hook; change via `args` as shown above.
- Requires a git repository at hook time (same as CLI `--staged`).

## GitHub Action (Phase 6)

Composite action at [`action.yml`](./action.yml). Example workflow:

```yaml
name: piilint
on:
  pull_request:
  push:
    branches: [main]

jobs:
  scan:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      # needed only if you upload SARIF:
      # security-events: write
    steps:
      - uses: actions/checkout@v4

      - name: Run piilint
        id: piilint
        uses: thelonewander3r/PIIScanner@main   # pin to a tag when available
        with:
          path: .
          fail-on: high
          format: sarif          # console | json | sarif
          # baseline: piilint-baseline.json
          # staged: "false"
          # version: "0.1.0"     # install from PyPI; omit to pip-install action checkout
          # extra-args: "--exclude 'vendor/**'"

      # SARIF upload is the caller's job — the action only writes the file.
      - name: Upload SARIF
        if: always()
        uses: github/codeql-action/upload-sarif@v3
        with:
          sarif_file: ${{ steps.piilint.outputs.sarif-path }}
```

### Action inputs

| Input | Default | Description |
|---|---|---|
| `path` | `.` | Path to scan |
| `fail-on` | _(empty)_ | `high` / `medium` / `low` / `never` (empty → config/default) |
| `format` | `console` | `console` / `json` / `sarif` |
| `baseline` | _(empty)_ | Optional baseline JSON path |
| `staged` | `false` | Scan only git-staged files |
| `extra-args` | _(empty)_ | Extra CLI args (space-separated) |
| `version` | _(empty)_ | PyPI version; empty installs from `github.action_path` |
| `sarif-file` | `piilint.sarif` | Output path when `format=sarif` |
| `python-version` | `3.12` | Python for the composite runner |

### Action outputs

| Output | Description |
|---|---|
| `sarif-path` | Path to written SARIF when `format=sarif`; empty otherwise |

## CI & release (Phase 6)

- **CI:** [`.github/workflows/ci.yml`](./.github/workflows/ci.yml) — `{ubuntu, windows, macos} × {3.10, 3.13}` with ruff, mypy (`files=src/piilint`), pytest (incl. benchmark gate), and `piilint --version`.
- **Release:** [`.github/workflows/release.yml`](./.github/workflows/release.yml) — on tag `v*` / GitHub Release published: build with `uv build` (hatchling), publish via [`pypa/gh-action-pypi-publish`](https://github.com/pypa/gh-action-pypi-publish) using **OIDC trusted publishing** (no long-lived PyPI token).

### PyPI trusted publisher checklist (maintainer)

Before the first real publish (tag `v0.1.0` only with explicit go):

1. Create the PyPI project `piilint` (or register a pending publisher that creates it on first upload).
2. On PyPI → Publishing → Trusted publishers, add a GitHub publisher:
   - **Owner:** `thelonewander3r`
   - **Repository:** `PIIScanner`
   - **Workflow name:** `release.yml`
   - **Environment name:** `pypi` (must match the workflow `environment:`)
3. In GitHub repo Settings → Environments, create environment **`pypi`** (optional protection rules / required reviewers recommended for production tags).
4. Do **not** store a PyPI API token in Actions secrets for this flow.
5. Cut a tag only when ready: `git tag v0.1.0 && git push origin v0.1.0` (triggers release workflow).

> **Note:** Pushing `.github/workflows/*.yml` requires a GitHub PAT (or credentials) with the `workflow` scope. If CI/release YAML cannot land yet, non-workflow distribution files (`action.yml`, `.pre-commit-hooks.yaml`, README) can still merge; re-auth the PAT and push workflows afterward.

## Status

Phases 0–6 complete (locally): deterministic recognizers, text + tabular + notebook adapters, console / JSON / SARIF reporters, synthetic benchmark corpus + CI gate, config/policy/noise controls, baseline subtraction, `--staged` mode, CI/release workflows, pre-commit hook, and GitHub Action. First production PyPI publish is intentionally deferred until maintainer go + OIDC publisher setup.

## Pairing

This is **not** a secrets scanner. Pair with [gitleaks](https://github.com/gitleaks/gitleaks) / trufflehog for API keys and tokens.

## License

Apache-2.0

## Corpus note

`tests/corpus/` contains **100% synthetic** labeled data, generated for tests. It never contains real personal data.
