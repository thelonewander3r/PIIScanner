---
title: piilint — Project management
status: active
updated: 2026-08-11
owner: Product Owner
---

# piilint — Project management

Living PO doc for **scope**, **requirements**, and **sprints**. Technical build detail stays in [`BUILD_PLAN.md`](./BUILD_PLAN.md). Developer handoffs live in phase briefs (e.g. [`PHASE3_DEV_BRIEF.md`](./PHASE3_DEV_BRIEF.md)).

**One-liner:** Find PII in the files developers actually commit and send — notebooks, CSV, JSON, Parquet, and source code. Everything stays local.

**Package:** `piilint` | **License:** Apache-2.0

**GitHub:** https://github.com/thelonewander3r/PIIScanner

**Local:** `C:\Users\E_man\Documents\Projects\PIIScanner2`

---

## Scope (v0 / MVP)

### In scope

- Local-first CLI (`piilint`) — no scan-time network
- File types: text/source, notebooks (incl. outputs), CSV/TSV, JSON/JSONL, Parquet
- Deterministic recognizers: credit card, SSN (US), IBAN, email, phone, DOB (context-key), IP (off by default)
- Optional NER (`piilint[ner]`) post-MVP / Phase 7 — not current sprint
- Policy and noise control (config, ignore, allowlists, suppressions, fail-on)
- Baseline + staged/pre-commit mode
- Console + JSON + SARIF reporters
- Synthetic benchmark corpus with precision/recall CI gates
- Windows, macOS, Linux; Python 3.10–3.13

### Out of scope (v0)

- Secrets scanning (pair with gitleaks / trufflehog)
- Anonymization / rewrite (`--redact` is post-MVP)
- Databases, PDF, docx/xlsx, images/OCR
- Telemetry
- Non-English NER as default
- Claiming GDPR / HIPAA / PCI "compliance"

### Product promise

> Before this file reaches GitHub, an LLM, a vendor, or a fixture directory — tell me if it contains PII, without uploading my data anywhere.

Disclaimer (required in all user-facing docs): *piilint helps you find sensitive data before it leaks. It is a detection aid, not a compliance certification, and cannot guarantee that all sensitive data is found.*

---

## Requirements (must-have for MVP)

| ID | Requirement | Notes |
|---|---|---|
| R1 | Zero scan-time network | Enforced by pytest-socket |
| R2 | Redaction by default | No raw PII in outputs, logs, or snapshots |
| R3 | Deterministic output | Same input → byte-identical results; stable sort |
| R4 | Exit codes are public API | `0` clean / below threshold · `1` findings ≥ fail-on · `2` config/usage error |
| R5 | Precision over recall | High-severity precision ≥ 0.95; core recall ≥ 0.85 (CI gate) |
| R6 | Windows first-class | pathlib, UTF-8 replace, BOM/CRLF |
| R7 | Chassis boundary | adapters / findings / baseline / reporters do not import recognizers |
| R8 | Small locked dependency set | Ask before adding deps |
| R9 | Config precedence | CLI > `piilint.toml` > `[tool.piilint]` > defaults |
| R10 | Noise controls | `.piiignore`, inline suppressions, allowlists, test-data downweight, baseline |

Full entity/adapter/reporter specs: see `BUILD_PLAN.md`.

---

## Phase map → sprints

| Phase | Theme | Status (as of 2026-08-11) |
|---|---|---|
| 0 | Bootstrap | Done |
| 1 | Corpus + engine core | Done |
| 2 | Tabular + notebook adapters | Done |
| 3 | Policy & noise | Done — [issue #1](https://github.com/thelonewander3r/PIIScanner/issues/1) / [PR #2](https://github.com/thelonewander3r/PIIScanner/pull/2) |
| 4 | Baseline + staged mode | Done — [issue #3](https://github.com/thelonewander3r/PIIScanner/issues/3) / [PR #4](https://github.com/thelonewander3r/PIIScanner/pull/4) |
| 5 | Reporters & DX polish | **Done (Sprint 3)** — [issue #5](https://github.com/thelonewander3r/PIIScanner/issues/5) |
| 6 | Distribution | Not started |
| 7 | Optional NER | After launch OK |
| 8 | Launch collateral | Not started |

---

## Sprint 2 — Baseline + staged (COMPLETE)

**Tracking:** [Issue #3](https://github.com/thelonewander3r/PIIScanner/issues/3) (closed)  
**Merged:** [PR #4](https://github.com/thelonewander3r/PIIScanner/pull/4) → `main`  
**Verified:** 60 pytest; mypy; benchmark gates; ruff E501 cleaned before merge

---

## Sprint 3 — Reporters & DX polish (COMPLETE — pending Lead Dev review / PR)

**Goal:** Machine-readable outputs for CI/Security tab, plus console polish — without breaking deterministic, masked-by-default reporting.

**Source:** `BUILD_PLAN.md` § Output spec + Phase 5 + reporters layout  
**Tracking:** [Issue #5](https://github.com/thelonewander3r/PIIScanner/issues/5)

### In scope

1. **`--format json`** — stable versioned schema (`schema_version: 1`): tool version, config hash, per-finding records (masked sample + value hash, never raw PII), summary block; byte-stable key order / sort
2. **`--format sarif`** — valid SARIF 2.1.0 suitable for `github/codeql-action/upload-sarif` (GitHub Security tab)
3. **Console polish** — Rich summary grouped by file → findings table (severity color, entity, location, masked sample, confidence) → totals line (`N high · M medium · K low — F files scanned in Ts`)
4. **CLI wiring** — `--format {console,json,sarif}` (console default); formats compose with `--baseline`, `--staged`, `--fail-on`
5. **Chassis** — implement under `src/piilint/reporters/` (`json_.py`, `sarif.py`; extend `console.py`); no recognizer imports in reporters
6. **Tests** — schema/fixture tests for JSON; SARIF structural validation (or golden with stable fields); masking regression (no raw corpus PII in any format); console snapshot or key substring asserts; benchmark gates stay green
7. **Docs** — README examples for JSON/SARIF; mark Phase 5 done in `BUILD_PLAN.md` when AC met

### Out of scope (Sprint 3)

- PyPI / pre-commit hook publish / GitHub Action packaging (Phase 6) — SARIF should be *usable* by upload-sarif, but shipping `action.yml` waits
- NER extra (Phase 7)
- `--show-matches` unmask behavior beyond what BUILD_PLAN already specifies (if missing, add only the documented refuse-when-`CI=true` rule)
- New dependencies without Lead Dev / Emanuel approval (prefer stdlib + existing stack)

### Acceptance (Sprint 3 done when)

- [x] `--format json` emits schema_version 1, masked-only findings, deterministic output
- [x] `--format sarif` is valid SARIF 2.1.0 and maps severities/locations usefully
- [x] Console matches the Output spec summary shape
- [x] Exit codes unchanged (0/1/2); reporters never turn exceptions into exit 1
- [x] `uv run pytest` green; ruff + mypy strict on `src/`; benchmark gates hold with real numbers
- [x] No recognizer imports in `reporters/`
- [ ] Lead Developer review approved
- [ ] PO cleanup; PR to `main`

### Roles

- **Developer:** implement on a feature branch off `main`; report AC + numbers on the issue
- **Lead Developer:** open issue from this scope, review, guidance
- **Product Owner:** this scope call; cleanup/PR after approval

---

## How we work (agent loop)

1. **Product Owner** owns project scope (this file): priorities, which phase/package is next
2. **Lead Developer ↔ Developer** coordinate via **GitHub issues + DMs**
3. **Developer** implements on a feature branch off `main`
4. **Lead Developer** reviews architecture + AC
5. **Product Owner** cleans up, opens/merges PR cadence, then defines the next work package (Lead Dev opens the issue from that scope call)

Technical source of truth: `BUILD_PLAN.md`. Sprint/scope board: this file. Phase handoffs: `PHASE*_DEV_BRIEF.md`.

---

## Open blockers

| Blocker | Impact | Owner |
|---|---|---|
| GitHub PAT missing `workflow` scope | `.github/workflows/ci.yml` still local-only; CI cannot run on GitHub yet | Emanuel (re-auth PAT with `workflow`) |

---

## Later sprints (preview)

- **Sprint 4 — Distribution (Phase 6):** PyPI, pre-commit hook, GitHub Action, release workflow (needs `workflow` PAT scope)
- **Sprint 5 — Optional NER (Phase 7):** `piilint[ner]` + `setup-ner` (after launch OK)
