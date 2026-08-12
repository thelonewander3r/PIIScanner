# piilint

[![CI](https://github.com/thelonewander3r/PIIScanner/actions/workflows/ci.yml/badge.svg)](https://github.com/thelonewander3r/PIIScanner/actions/workflows/ci.yml)

Local-first PII scanner for the files developers actually commit and send — notebooks, CSV, JSON, Parquet, and source code. **Nothing leaves your machine.**

> **Disclaimer:** piilint helps you find sensitive data before it leaks. It is a detection aid, not a compliance certification, and cannot guarantee that all sensitive data is found. It does not make anyone GDPR/HIPAA/PCI compliant.

**Package:** `piilint` (PyPI name `piiscan` was already taken) · **License:** Apache-2.0 · **Repo:** [thelonewander3r/PIIScanner](https://github.com/thelonewander3r/PIIScanner)

**Not a secrets scanner.** Pair with [gitleaks](https://github.com/gitleaks/gitleaks) or [trufflehog](https://github.com/trufflesecurity/trufflehog) for API keys and tokens.

---

## Five-minute path

### 1. Install

```bash
# recommended for CLI use
pipx install piilint
# or one-off
uvx piilint --version
# or classic
pip install piilint
```

Until the first PyPI release is cut, install from git or a local checkout:

```bash
pipx install git+https://github.com/thelonewander3r/PIIScanner.git
# or
uv sync --extra dev
uv run piilint --version
```

### 2. Scan

```bash
piilint .                     # scan the current directory
piilint . --fail-on high      # fail CI/pre-commit on high-severity findings
```

Exit codes: `0` clean / nothing staged · `1` findings at or above `--fail-on` · `2` usage/config/git error.

### 3. Wire into git / CI (optional)

**Pre-commit** — add to `.pre-commit-config.yaml`:

```yaml
repos:
  - repo: https://github.com/thelonewander3r/PIIScanner
    rev: v0.1.0   # pin to a release tag when available
    hooks:
      - id: piilint
        # Default: --staged --fail-on medium
```

**GitHub Action + SARIF** — drop into a workflow:

```yaml
- uses: actions/checkout@v4
- name: Run piilint
  id: piilint
  uses: thelonewander3r/PIIScanner@main   # pin to a tag when available
  with:
    path: .
    fail-on: high
    format: sarif
- name: Upload SARIF
  if: always()
  uses: github/codeql-action/upload-sarif@v3
  with:
    sarif_file: ${{ steps.piilint.outputs.sarif-path }}
```

### 4. Adopt without boiling the ocean

```bash
piilint baseline . -o piilint-baseline.json   # fingerprints only — never raw PII
piilint . --baseline piilint-baseline.json    # report NEW findings only
piilint . --staged                            # scan only git-staged files
```

---

## Demo

The classic leak: a notebook runs `df.head()` and the **output cell** still holds customer rows when you commit the `.ipynb`.

Synthetic demo (no real PII): [`tests/corpus/notebook/leak_demo.ipynb`](./tests/corpus/notebook/leak_demo.ipynb)

```bash
piilint tests/corpus/notebook
```

See also [`examples/README.md`](./examples/README.md) for a short pointer and expected story.

All of `tests/corpus/` is **100% synthetic** labeled data generated for tests.

---

## Configuration

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

---

## Baseline + staged

Adopt without fixing history first, and scan only what is about to land in git.

```bash
piilint baseline . -o piilint-baseline.json
piilint . --baseline piilint-baseline.json
piilint . --staged
```

**Fingerprint design:** SHA-256(relative path, entity, normalized-value hash, occurrence index).
Line numbers are **excluded** so ordinary edits do not resurrect old findings.

**Tradeoff:** an edit that only moves a value to a different line will not reappear as "new."
Moved or duplicated values may still match by occurrence index. Commit a fresh baseline when
you intentionally accept a new set of findings.

---

## Output formats

Default output is a Rich **console** report (grouped by file → severity-colored table → totals).

```bash
piilint . --format json
piilint . --format sarif > piilint.sarif
piilint . --format json --baseline piilint-baseline.json --fail-on high
```

JSON includes a `config_hash`: SHA-256 of a canonical JSON snapshot of the **effective**
scan config fields that affect detection/policy (`fail_on`, `min_confidence`, `exclude`,
`entity_enabled`, `severity_overrides`, allowlists, `phone_region`). Paths and timestamps
are excluded so the hash is stable across identical policy runs.

`--show-matches` unmasks the console Sample column for local triage only. It is **refused**
when `CI=true` (exit 2) and does not apply to JSON/SARIF (those formats never emit raw PII).

---

## Pre-commit hook

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

---

## GitHub Action

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

---

## CI & release

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

---

## Optional NER (names & addresses)

PERSON/ADDRESS detection is **off by default** and lives behind an optional extra so the base install stays lean and scan-time stays offline.

```bash
pip install "piilint[ner]"    # or: uv sync --extra ner
piilint setup-ner             # downloads en_core_web_sm (network; once)
piilint . --ner               # enable PERSON + ADDRESS for this run
```

- Without `[ner]` installed, normal scans are unchanged; `piilint . --ner` exits **2** with an install hint.
- With `[ner]` but no model, `--ner` exits **2** asking you to run `setup-ner`.
- Config toggles `entities.person` / `entities.address` default to **false**; `--ner` enables both for the run.
- Only English (`en_core_web_sm`) is supported in this phase. No scan-time network — model download is setup-only.

---

## Status

Phases 0–8 are complete, including **Phase 7 optional NER** (`piilint[ner]`, `setup-ner`, `--ner` for PERSON/ADDRESS). Deterministic recognizers, text + tabular + notebook adapters, console / JSON / SARIF reporters, synthetic benchmark corpus + CI gate, config/policy/noise controls, baseline subtraction, `--staged` mode, CI/release workflows, pre-commit hook, GitHub Action, and launch docs. First production PyPI publish is intentionally deferred until maintainer go + OIDC publisher setup.

## Contributing & security

- Contributors: see [`CONTRIBUTING.md`](./CONTRIBUTING.md)
- Vulnerability reports: see [`SECURITY.md`](./SECURITY.md)
- Changelog: [`CHANGELOG.md`](./CHANGELOG.md)

## License

Apache-2.0
