---
title: PII Scanner — Agent Build Plan
aliases:
  - PII Scanner
  - piilint Build Plan
tags:
  - project
  - business
  - ai
  - canonical
status: active
updated: 2026-08-11
---

# PII Scanner — Agent Build Plan

> **One-liner:** Find PII in the files developers actually commit and send — notebooks, CSV, JSON, Parquet, and source code. Everything stays local.

**Chosen package name: `piilint`** (Phase 0, 2026-08-11)

| Candidate | PyPI | GitHub name search | Notes |
|---|---|---|---|
| `piiscan` | **TAKEN** (v0.1.7, Presidio wrapper) | — | Original working name; unavailable |
| `leakscan` | **TAKEN** (secrets scanner) | — | Wrong category overlap anyway |
| `piilint` | **AVAILABLE** (404) | 0 repos | **Selected** — developer-familiar “lint” framing |
| `piigate` | AVAILABLE | 0 repos | Strong alternate |
| `pii-patrol` | AVAILABLE | 1 repo | Hyphenated; weaker CLI feel |
| `piiwatch` / `pii-guard` | TAKEN | — | — |

Working name throughout this document historically was `piiscan`; the installable CLI/module is **`piilint`**. Update docs/commands accordingly.

---

## How to use this document (Emanuel)

1. Create a **new repo folder outside the vault** (e.g. `C:\Users\E_man\Documents\Projects\PIIScanner2`) — a Python repo inside the Obsidian vault would pollute Obsidian's index with venv/site-packages files.
2. Copy this file into the repo root as `BUILD_PLAN.md`.
3. Open the agent in that folder and paste the kickoff prompt:

   > Read BUILD_PLAN.md fully. Follow the Agent Operating Instructions section exactly. Execute Phase 0 and Phase 1 only. Stop after Phase 1 and report the real benchmark precision/recall numbers.

4. Run **one phase (or two small ones) per session**. Between phases, you personally check the acceptance criteria — don't take the agent's word for it.
5. Treat this plan as living: when you and the agent change a decision, update this file in the same commit.

---

## Agent operating instructions

You (the agent) are building a production-quality open-source Python CLI. Rules:

- **Work phase by phase.** Do not start a phase that wasn't requested. Stop at each phase boundary and report what was built, what was tested, and the acceptance-criteria status.
- **Never fabricate results.** Run the tests/benchmarks and report actual numbers. If a target is missed, say so and propose a fix — do not lower the gate to pass it.
- **Acceptance criteria are the definition of done.** A phase is not complete until every criterion is demonstrably met.
- **Ask before adding dependencies** beyond the locked list. Every dependency is a maintenance liability in a security-adjacent tool.
- **No network calls at scan time — ever.** This is the product's core promise. The test suite enforces it (see Phase 1). Network is permitted only in explicit setup commands (`setup-ner`) and CI/release workflows.
- **Redaction by default.** No raw matched PII value may appear in any output, log, error message, or test snapshot. Masked samples only.
- **Deterministic output.** Same input → byte-identical output (stable sort order: path, then line/row, then entity). Exit codes are part of the public API.
- **Windows is a first-class target.** The maintainer develops on Windows 11. Use `pathlib` everywhere, read text as UTF-8 with `errors="replace"`, handle BOM and CRLF, and keep the CI matrix green on windows-latest.
- **Compliance language rule:** the tool and all docs you write must never claim to make anyone "GDPR/HIPAA/PCI compliant." Standard disclaimer: *"piilint helps you find sensitive data before it leaks. It is a detection aid, not a compliance certification, and cannot guarantee that all sensitive data is found."*
- Conventional commits; small typed modules; tests accompany the code they test in the same phase.

---

## Product context

**Who it's for:** developers, data engineers, and ML/AI engineers with data samples, notebooks, exports, and repos that must not accidentally contain real customer data.

**The moment it serves:** "Before this file reaches GitHub, an LLM, a vendor, or a fixture directory — tell me if it contains PII, without uploading my data anywhere."

**Why it can win:** enterprise DLP uploads your data to scan it; Presidio is a framework, not a workflow. The gap is a polished, local-first, five-minute experience across the file types data people actually touch (`.ipynb` outputs are the classic leak — a `df.head()` with real customer rows), wired into pre-commit and GitHub Actions.

**Business model (context only — do not build the paid layer now):** free, complete, open-source CLI → organic adoption via PyPI/pre-commit/GitHub Marketplace/SEO → later paid team layer (shared policy, findings-metadata history, org baselines). The free tool must never be crippled to upsell.

---

## Non-goals and scope boundaries (v0)

- **Not a secrets scanner.** No API keys, tokens, or passwords — gitleaks/trufflehog own that. Docs recommend pairing with gitleaks. This keeps positioning sharp.
- **Detect-first.** v0 was detect-only; **`piilint redact`** (Sprint 9) writes cleaned **copies** via base-wheel span rewrite (`mask_value`) ? no `presidio-anonymizer` / no new base deps. Notebooks/parquet redact still follow-up.
- **No databases, PDFs, docx/xlsx, images/OCR** in v0. File formats listed below only.
- **No telemetry** in v0. If ever added, opt-in only.
- **English-first** detection; NER for other languages is post-MVP.

---

## Locked decisions

| Decision | Choice | Notes |
|---|---|---|
| Language | Python, floor 3.10, test 3.10–3.13 | Presidio/spaCy compatible; broad user base |
| Packaging | `pyproject.toml`, `src/` layout, hatchling, managed with `uv` | `uvx piilint` / `pipx` friendly |
| CLI | Typer + Rich | UX requirement: `piilint .` scans cwd; `piilint baseline .` writes baseline |
| Core detection | Deterministic recognizers (regex + validators) in base install | Luhn, IBAN mod-97, SSN rules, `phonenumbers` lib |
| NER (names/addresses) | Optional extra `piilint[ner]` → presidio-analyzer + spaCy | Heavy deps stay out of base install; model fetched via explicit `piilint setup-ner` |
| Data engines | `pyarrow` only (parquet + streaming CSV), `nbformat` (notebooks), stdlib json | Keep the dependency tree small |
| Other deps | `typer`, `rich`, `phonenumbers`, `pathspec` (.gitignore), `pyyaml` (corpus manifest) | Anything else: ask first |
| License | Apache-2.0 | Patent grant; standard for security tooling. (MIT acceptable if Emanuel prefers) |
| Lint/type/test | ruff (lint+format), mypy (strict on `src/`), pytest + pytest-socket | pytest-socket blocks network in the whole suite |
| CI | GitHub Actions: {ubuntu, windows, macos} × {3.10, 3.13}, lint, mypy, tests, benchmark gate | Release via PyPI trusted publishing (OIDC) |
| Repo | New standalone public GitHub repo, named after the final package name | Not inside the Obsidian vault |
| **Package name** | **`piilint`** | Recorded Phase 0 after PyPI/GitHub checks |

---

## Architecture

```text
paths / --staged
      ↓
  file walker  ── .gitignore + .piiignore + size/binary guards
      ↓
  adapters     ── text | notebook | csv | json | parquet   (yield Units: line / cell / column-chunk)
      ↓
  engine       ── runs recognizer registry over Units, applies context signals
      ↓
  findings     ── entity, severity, confidence, location, masked sample, fingerprint
      ↓
  policy       ── allowlists, suppressions, baseline subtraction, severity overrides
      ↓
  reporters    ── console (Rich) | JSON (versioned schema) | SARIF 2.1.0
      ↓
  exit code    ── 0 clean/below threshold · 1 findings ≥ --fail-on · 2 config/usage error
```

Design constraint: `adapters/`, `findings.py`, `baseline.py`, and `reporters/` must not import recognizer logic — they are a generic "scan files, emit findings, gate CI" chassis. (Reason: a future sibling product — dataset diffing — reuses this chassis. Keep the boundary clean.)

### Repo layout

```text
piilint/
├── pyproject.toml            ├── LICENSE (Apache-2.0)
├── README.md                 ├── BUILD_PLAN.md (this file)
├── CONTRIBUTING.md SECURITY.md CHANGELOG.md PROJECT.md
├── examples/README.md        # pointer to synthetic notebook demo
├── .pre-commit-hooks.yaml    ├── action.yml (composite GitHub Action)
├── .github/workflows/        #   ci.yml, release.yml
├── src/piilint/
│   ├── cli.py  config.py  engine.py  findings.py  baseline.py  gitutil.py
│   ├── recognizers/   # registry + email, phone, ssn, credit_card, iban, ip, dob, ner(optional)
│   ├── adapters/      # base.py + text, notebook, csv_, json_, parquet
│   └── reporters/     # console, json_, sarif
├── tests/
│   ├── corpus/        # synthetic labeled corpus + corpus.yaml manifest
│   ├── test_benchmark.py     # precision/recall CI gate
│   └── unit tests per module
└── scripts/perf_smoke.py     # manual perf check, not in CI
```

---

## Detection spec

### Entities (v0)

| Entity | Validator | Default severity | Default state |
|---|---|---|---|
| `CREDIT_CARD` | Luhn + brand prefix + length | high | on |
| `SSN_US` | Format + area rules (no 000/666/9xx), context words boost | high | on |
| `IBAN` | mod-97 checksum | high | on |
| `EMAIL` | RFC-lite pattern; `@` pre-filter | medium | on |
| `PHONE` | `phonenumbers` validation (default region US, configurable) | medium | on |
| `DOB` | Date pattern **+ column/key-name signal only** (tabular/JSON) | medium | on |
| `IP_ADDRESS` | v4/v6 syntactic | low | **off** (noisy in code) |
| `PERSON`, `ADDRESS` | Presidio/spaCy NER | medium | **off**; requires `[ner]` extra + `--ner` flag |

### Confidence and severity

- Each finding gets `confidence ∈ [0,1]`. Base confidence from validator strength (checksum pass ≈ 0.95; bare pattern ≈ 0.5), adjusted by context signals:
  - **Column/key-name signal** (tabular/JSON): header like `ssn`, `email`, `dob`, `phone`, `card_number` ⇒ +0.2–0.3. Header matches but values don't validate ⇒ emit nothing (don't guess).
  - **Test-data downweight:** domains `example.com/org/net`, `test.*`, `localhost`, RFC-5737 IPs, and the classic fake numbers (`555-01xx` phones, `4111 1111 1111 1111`) ⇒ −0.4 and severity cap at low.
- Findings below `min_confidence` (default 0.6) are dropped. Severity map is config-overridable per entity.
- Default posture is **precision over recall**. A noisy scanner gets uninstalled; a quiet one gets trusted.

### Masking (all outputs)

- Email `j***@a***.com` · phone last 2 digits · card last 4 (`**** **** **** 1234`) · SSN fully masked · names first initial. JSON/SARIF carry masked sample + SHA-256 of normalized value (for dedup), never the raw value.
- `--show-matches` unmasks console output for local triage only; refuse it when `CI=true`.

---

## Adapter spec

| Adapter | Files | Behavior |
|---|---|---|
| text | `.py .md .txt .sql .yml .yaml .toml .env` + extensionless text | Line-by-line; binary sniff (null bytes) skips file; cheap pre-filters (e.g. `@` for email) before regex |
| notebook | `.ipynb` | Via `nbformat`. Scan **source cells and outputs** (`text/plain`, stream text). Location = cell index + source/output. Outputs are the headline feature — say so in docs |
| csv | `.csv .tsv` | `pyarrow.csv.open_csv` streaming reader; header-aware; per-column aggregation |
| json | `.json .jsonl` | Key names act like column headers; `.jsonl` line-streamed; guard: files > 50 MB `.json` get sampled |
| parquet | `.parquet` | `ParquetFile.iter_batches` (~64k rows); scan string-typed columns first; column pruning |

**Column aggregation (tabular):** never emit 10,000 row-level findings for one column. Emit one column-level finding: `customers.csv · column "email" · EMAIL · 9,987/10,000 non-null rows matched · 3 masked examples`. Cap examples at 3.

**Sampling:** full scan by default; files over 250 MB (or with `--sample N`) scan first N + reservoir rows per column and mark the finding `sampled: true`.

**Walker:** respects `.gitignore` (via `pathspec`) and `.piiignore`; `--include/--exclude` globs; `--staged` scans only git-staged files (for pre-commit).

---

## Policy and noise control

- **Config:** `piilint.toml` at repo root (fallback: `[tool.piilint]` in `pyproject.toml`). Precedence: CLI flags > `piilint.toml` > pyproject > defaults.

```toml
[scan]
fail_on = "high"            # high | medium | low | never
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

- **`.piiignore`:** gitignore-syntax path excludes.
- **Inline suppression:** trailing `# piilint: ignore` or `# piilint: ignore[EMAIL]` suppresses that line (code/text adapters).
- **Baseline:** `piilint baseline . -o piilint-baseline.json` fingerprints current findings; `piilint . --baseline piilint-baseline.json` reports **new findings only** — teams adopt without fixing history first. Fingerprint = SHA-256(relative path, entity, normalized-value hash, occurrence index) — deliberately excludes line numbers so ordinary edits don't resurrect old findings. Document this tradeoff.

---

## Output spec

- **Console:** Rich summary grouped by file → findings table (severity color, entity, location, masked sample, confidence) → totals line: `3 high · 12 medium · 0 low — 41 files scanned in 2.1s`.
- **`--format json`:** stable versioned schema (`schema_version: 1`), includes tool version, config hash, per-finding records, summary block.
- **`--format sarif`:** valid SARIF 2.1.0, uploadable via `github/codeql-action/upload-sarif` so findings appear in the GitHub Security tab.
- **Exit codes:** `0` no findings at/above `--fail-on` · `1` findings at/above threshold · `2` usage/config error. Uncaught exceptions must not masquerade as `1`.

---

## Benchmark corpus and quality gates — build FIRST

The corpus is the spine of the project; recognizers are written against it, not before it.

- `tests/corpus/` — **100% synthetic** data (generated, never real; state this in the README):
  - **True positives per entity per adapter:** emails in code comments and CSV columns; SSNs in a CSV; valid-Luhn cards inside a **notebook output cell**; phones in JSON; IBANs in text; DOB columns in parquet; (NER set: names/addresses in prose).
  - **Hard negatives:** UUIDs, git SHAs, timestamps, semver strings, `1.2.3.4`-style versions, order numbers shaped like phones, 16-digit numbers that fail Luhn, EIN-formatted numbers (not SSNs), base64 blobs, lockfile integrity hashes, Faker-style obvious test data.
- `tests/corpus/corpus.yaml` manifest lists every file's expected findings (path, entity, count, location hints).
- `tests/test_benchmark.py` computes per-entity and overall precision/recall from the manifest and **fails CI** if:
  - precision (high-severity entities) < **0.95**
  - recall (core entities: email, phone, ssn, credit_card, iban) < **0.85**
- Benchmark results print in CI logs on every run. New recognizers/corpus additions must not drop existing metrics.

---

## Phases

### Phase 0 — Bootstrap (½ day) — DONE 2026-08-11
Name availability check completed; package **`piilint`** selected. Scaffolded repo (`pyproject`, `src/` layout, uv, ruff, mypy, pytest+pytest-socket, LICENSE, CI skeleton on 3 OSes); `piilint --version` works.

**AC:** CI green on ubuntu/windows/macos; `uv run pytest` passes; `uvx --from . piilint --version` prints version; chosen name recorded here. *(Local AC verified in Phase 0+1 session; remote CI pending first push.)*

### Phase 1 — Corpus + engine core (2–3 days) — DONE 2026-08-11
`Finding` model with masking + fingerprints; recognizer protocol + registry; deterministic recognizers (email, phone, ssn, credit_card, iban, ip); text adapter; walker with ignore rules; console reporter (basic); **benchmark corpus + gate**; suite-wide network block (pytest-socket) proving no scan-time network.

**AC:** benchmark gate passes with real reported numbers; `piilint tests/corpus/text` finds planted findings and exits 1; masked output verified (a test asserts no raw corpus value appears in any output).

### Phase 2 — Tabular + notebook adapters (2–3 days) — DONE 2026-08-11
csv/parquet/json/jsonl/ipynb adapters; column aggregation; column-name confidence signals; sampling + size guards; DOB recognizer (context-key only).

**AC:** corpus cases pass per format; notebook-output leak detected (the demo case); `scripts/perf_smoke.py` shows 100 MB CSV ≤ 60 s and 1 GB parquet streamed with < 500 MB peak memory.

### Phase 3 — Policy & noise (1–2 days) — DONE 2026-08-11
Config file + precedence (`config.py` overlay merge so unspecified keys do not reset lower layers); `.piiignore` tested; inline `# piilint: ignore` / `ignore[ENTITY]` (text/code only; tabular skipped in v0); allowlists (values + email domains); test-data downweight (−0.4, severity ≤ low) then `min_confidence`; entity enable/severity overrides; `--fail-on` + exit 0/1/2 (config errors → 2); `scan.exclude` wired into walker. `Finding.normalized_value` + `normalize_value()` support policy without recognizer imports. Optional `tomli` for Python 3.10 TOML.

**AC verified:** precedence CLI > `piilint.toml` > `[tool.piilint]` > defaults (partial-file overlay tested); bad TOML exit 2; unit tests for allowlist/downweight/suppressions/`.piiignore`/exclude; `uv run pytest` + benchmark gates; ruff + mypy strict on `src/`; no recognizer imports in adapters/findings/reporters; sample `piilint.toml` + README notes. Benchmark 2026-08-11 (local): HIGH-severity precision 1.000; CORE recall 1.000; all core entities P/R 1.000; 47 pytest passed.

### Phase 4 — Baseline + staged mode (1–2 days) — DONE 2026-08-11
`baseline.py` (versioned JSON fingerprints; write/load/subtract; no recognizer imports) + `gitutil.py` (stdlib subprocess; `staged_files` via `git diff --cached --name-only --diff-filter=ACMR`). CLI: `piilint baseline [PATH] -o/--output`, `piilint . --baseline PATH`, `piilint . --staged`. Walker/engine `only_paths` allowlist; baseline subtract after policy, before reporter. Fingerprints reuse `findings.fingerprint_for` (line-number independent). Empty staged → exit 0; not a git repo → exit 2.

**AC verified:** baseline write stable versioned schema (fingerprints only); `--baseline` surfaces new findings only; fingerprint line-number independence unit-tested; `--staged` limits to staged paths; `uv run pytest` + benchmark gates; ruff + mypy strict on `src/`; README tradeoff documented.

### Phase 5 — Reporters & DX polish (1–2 days) — DONE 2026-08-11
`--format json` (schema_version 1: tool version, config_hash, masked findings, summary; deterministic `sort_keys` + finding sort by path/line/entity/fingerprint); `--format sarif` (SARIF 2.1.0, severity→level mapping, physical locations, partialFingerprints); console moved to `reporters/console.py` with Output-spec totals; `--show-matches` console-only, refused when `CI=true`. Modules: `reporters/json_.py`, `reporters/sarif.py`; re-exports from `__init__.py`. No recognizer imports in reporters. `config_hash` = SHA-256 of canonical effective Config (fail_on, min_confidence, exclude, entity_enabled, severity_overrides, allowlists, phone_region).

**AC verified:** JSON schema_version 1 + masking + determinism unit-tested; SARIF 2.1.0 structure + severity mapping; console totals line shape; CLI `--format` composes with baseline/staged/fail-on; exit codes unchanged; ruff + mypy strict on `src/`; pytest + benchmark gates with real numbers.

### Phase 6 — Distribution (1–2 days) — DONE 2026-08-11

CI matrix workflow (`.github/workflows/ci.yml`: ubuntu/windows/macos × 3.10/3.13 — ruff check/format, mypy via `[tool.mypy] files=src/piilint`, pytest+benchmark, `piilint --version`). Release workflow (`.github/workflows/release.yml`) builds with `uv build` / hatchling and publishes via `pypa/gh-action-pypi-publish@release/v1` with OIDC (`id-token: write`, environment `pypi`) on tag `v*` / release published — **no production tag/publish in this phase**. Root `.pre-commit-hooks.yaml` (`id: piilint`, `--staged`, default `--fail-on medium`, `pass_filenames: false`). Root composite `action.yml` (inputs: path/fail-on/format/baseline/staged/extra-args/version/sarif-file; SARIF upload left to caller). Packaging polish: `project.urls` → `thelonewander3r/PIIScanner`; README install via pipx/uvx/pip + pre-commit + Action docs + CI badge + PyPI trusted-publisher checklist.

**AC verified (local):** workflows + hook + action YAML present and parse; `uv run pytest` / ruff / mypy green; `piilint --version`; hatchling build smoke. **Remote CI green** pending workflow YAML on `main` (PAT may lack `workflow` scope — Emanuel blocker). First PyPI publish deferred to explicit go.


### Phase 7 — Optional NER extra (1–2 days, after launch is fine) — DONE 2026-08-11

Optional `piilint[ner]` → `presidio-analyzer` + spaCy for PERSON/ADDRESS; explicit `piilint setup-ner` downloads `en_core_web_sm` (only scan-adjacent network path); off by default; enable with `--ner` (or config `entities.person` / `entities.address`). Presidio `LOCATION` mapped to piilint `ADDRESS`. Lazy imports keep base install lean. Core benchmark gates exclude `requires_ner` corpus cases.

### Phase 8 — Launch collateral — DONE 2026-08-11

README five-minute path (install via uvx/pipx/pip → `piilint .` → pre-commit + Action/SARIF → baseline adoption); Demo section pointing at synthetic notebook leak (`tests/corpus/notebook/leak_demo.ipynb` + `examples/README.md`); CI badge verified for `thelonewander3r/PIIScanner` `ci.yml`; `CONTRIBUTING.md` (uv setup, pytest/ruff/mypy, conventional commits, Windows-first); `SECURITY.md` (GitHub Security Advisories preferred; no bounty; never paste real PII); `CHANGELOG.md` Keep a Changelog stub (Unreleased + 0.1.0 prep for Phases 0–6 — **not published**). No PyPI publish / `v*` tag / NER in this phase.

**AC verified:** README five-minute path + disclaimer + pairing; CI badge URL correct; CONTRIBUTING + SECURITY present; CHANGELOG stub; synthetic-only demo pointer; `uv run pytest` / ruff / mypy green locally.

---

### Sprint 7 — First PyPI release prep (DONE prep merged #15, 2026-08-11)

Prep for `piilint` `0.1.0` merged via [#15](https://github.com/thelonewander3r/PIIScanner/pull/15) ([issue #14](https://github.com/thelonewander3r/PIIScanner/issues/14)). Metadata polish (`pyproject.toml`), CHANGELOG fold into `[0.1.0]` (date TBD), README install + trusted-publisher checklist, maintainer runbook [`docs/RELEASE.md`](./docs/RELEASE.md), local `uv build` dry-run. **Not published** — no `v*` tag without Emanuel’s explicit go. Trusted publisher + GitHub environment `pypi` remain **Emanuel UI** steps. See [`PROJECT.md`](./PROJECT.md).

---

### Sprint 8 — Release hardening (IN PROGRESS, 2026-08-11)

Prove install-from-wheel before any production `v*` tag ([issue #16](https://github.com/thelonewander3r/PIIScanner/issues/16), branch `feature/sprint8-release-hardening`). Extends `.github/workflows/ci.yml` with required `package-smoke` (ubuntu + windows: `uv build` → clean venv → wheel install → `--version` → corpus scan exit 1 + masked output), separate optional `ner-smoke` (ubuntu: `--extra ner` + `setup-ner` + `--ner`), and `action-smoke` (local composite `uses: ./` with `fail-on: never` + YAML parse of `action.yml` / `.pre-commit-hooks.yaml`). Docs: `docs/RELEASE.md` “How we know releases are good” + TestPyPI trusted-publisher dry-run path (**no upload** without Emanuel go). Default matrix `test` unchanged. **Hard stop:** no production `v*` tag / no prod PyPI upload. See [`PROJECT.md`](./PROJECT.md).

---

## Post-MVP roadmap (do NOT build now)

- ~~`--redact` writing anonymized copies~~ ? **done (Sprint 9)** as `piilint redact PATH -o OUT` (base-wheel span rewrite; notebooks/parquet follow-up). No `presidio-anonymizer`.
- Team layer (the paid product): shared policy packs, org-wide baselines, findings-**metadata** history dashboard (raw data never leaves the machine — only findings metadata).
- More formats: xlsx, PDF; more locales (non-US SSN equivalents, phone regions).
- **Chassis reuse:** the adapter/findings/baseline/reporter chassis is deliberately generic. Candidate sibling product: dataset diffing (DataDiff CI). Revisit after this ships; do not speculatively generalize now.

## Name candidates (Phase 0 verifies) — RESOLVED

`piiscan` · `piilint` · `piigate` · `leakscan` · `pii-patrol` — **Winner: `piilint`**.
