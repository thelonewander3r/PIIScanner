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
- Distribution: PyPI, pre-commit hook, GitHub Action, CI/release workflows

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
| 5 | Reporters & DX polish | Done — [issue #5](https://github.com/thelonewander3r/PIIScanner/issues/5) / [PR #6](https://github.com/thelonewander3r/PIIScanner/pull/6) |
| 6 | Distribution | **Implemented on branch** — [issue #7](https://github.com/thelonewander3r/PIIScanner/issues/7); workflows ready locally; push of `.github/workflows/*.yml` still blocked until PAT has `workflow` scope |
| 7 | Optional NER | After launch OK |
| 8 | Launch collateral | Not started |

---

## Sprint 3 — Reporters & DX (COMPLETE)

**Tracking:** [Issue #5](https://github.com/thelonewander3r/PIIScanner/issues/5) (closed)  
**Merged:** [PR #6](https://github.com/thelonewander3r/PIIScanner/pull/6) → `main`  
**Verified:** 72 pytest; mypy; benchmark gates; ruff clean

---

## Sprint 4 — Distribution (IMPLEMENTATION COMPLETE — MERGE PENDING)

**Goal:** Make `piilint` installable and wireable in 5 minutes — PyPI, pre-commit, GitHub Action, and green CI/release automation.

**Source:** `BUILD_PLAN.md` locked decisions (CI matrix, PyPI OIDC, repo layout) + Phase 6  
**Tracking:** [Issue #7](https://github.com/thelonewander3r/PIIScanner/issues/7)  
**Branch:** `feature/phase6-distribution`  
**Hard blocker (push):** GitHub PAT must include `workflow` scope before `.github/workflows/*.yml` can be pushed. Emanuel owns unblocking. Non-workflow files (`action.yml`, `.pre-commit-hooks.yaml`, README, pyproject urls, docs) are ready regardless.

### Delivered on branch

1. **CI workflow** — `.github/workflows/ci.yml`: `{ubuntu, windows, macos} × {3.10, 3.13}` — ruff check/format, mypy, pytest+benchmark, version smoke (`uv sync --extra dev`)
2. **Release workflow** — `.github/workflows/release.yml` with PyPI OIDC trusted publishing (`pypa/gh-action-pypi-publish`, environment `pypi`); no long-lived token; no tag cut in this sprint
3. **Pre-commit hook** — `.pre-commit-hooks.yaml` (`piilint --staged --fail-on medium`); README consumer snippet
4. **GitHub Action** — root `action.yml` composite; SARIF write + upload documented as caller’s job
5. **Packaging polish** — `project.urls` → `thelonewander3r/PIIScanner`; README pipx/uvx/pip; hatchling build smoke
6. **Docs** — BUILD_PLAN Phase 6 DONE; this board updated; PyPI trusted-publisher checklist in README

### Out of scope (Sprint 4) — unchanged

- First production PyPI publish / release tag without Emanuel’s explicit go
- Marketplace / launch copy (Phase 8)
- NER (Phase 7)
- New runtime dependencies

### Acceptance (Sprint 4)

- [x] `ci.yml` prepared on feature branch (green on matrix once workflows can run on GitHub)
- [x] `release.yml` present with OIDC trusted publishing + README checklist for Emanuel’s PyPI/environment setup
- [x] `.pre-commit-hooks.yaml` smoke-tested (YAML parse / hook fields); README snippet correct
- [x] `action.yml` documented (inputs/outputs); SARIF upload left to caller
- [x] Package metadata consistent with public `piilint` name + corrected GitHub URLs
- [ ] Lead Developer review approved
- [ ] PO cleanup; PR to `main` (may need two-step push if PAT still lacks `workflow`)
- [ ] Remote CI green on `main` (blocked on workflow push until PAT has `workflow` scope)

### Roles

- **Emanuel:** add PAT `workflow` scope (blocker); configure PyPI trusted publisher; approve first real PyPI publish
- **Developer:** implement on `feature/phase6-distribution`; report AC on the issue
- **Lead Developer:** review / guidance
- **Product Owner:** cleanup/PR after approval

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
| GitHub PAT missing `workflow` scope | Cannot push `.github/workflows/ci.yml` or `release.yml` yet; files are prepared on `feature/phase6-distribution` | Emanuel (re-auth PAT with `workflow`) |

---

## Later sprints (preview)

- **Sprint 5 — Optional NER (Phase 7):** `piilint[ner]` + `setup-ner` (after launch OK)
- **Sprint 6 — Launch collateral (Phase 8):** README polish, examples, Marketplace/SEO notes
