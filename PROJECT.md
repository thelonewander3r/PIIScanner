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
| 6 | Distribution | **Next (Sprint 4)** — blocked on PAT `workflow` scope until ci/release YAML can push |
| 7 | Optional NER | After launch OK |
| 8 | Launch collateral | Not started |

---

## Sprint 3 — Reporters & DX (COMPLETE)

**Tracking:** [Issue #5](https://github.com/thelonewander3r/PIIScanner/issues/5) (closed)  
**Merged:** [PR #6](https://github.com/thelonewander3r/PIIScanner/pull/6) → `main`  
**Verified:** 72 pytest; mypy; benchmark gates; ruff clean

---

## Sprint 4 — Distribution (NEXT)

**Goal:** Make `piilint` installable and wireable in 5 minutes — PyPI, pre-commit, GitHub Action, and green CI/release automation.

**Source:** `BUILD_PLAN.md` locked decisions (CI matrix, PyPI OIDC, repo layout) + Phase 6  
**Tracking:** GitHub issue to be opened by Lead Dev from this scope call  
**Hard blocker:** GitHub PAT must include `workflow` scope before `.github/workflows/*.yml` can be pushed. Emanuel owns unblocking.

### In scope

1. **CI workflow** — land `.github/workflows/ci.yml`: `{ubuntu, windows, macos} × {3.10, 3.13}` running ruff, mypy, pytest, benchmark gate (draft may already exist locally under `.github/workflows/ci.yml`)
2. **Release workflow** — `.github/workflows/release.yml` with PyPI **trusted publishing (OIDC)** on tag/release; no long-lived PyPI token in secrets if avoidable
3. **Pre-commit hook** — `.pre-commit-hooks.yaml` exposing a hook that runs `piilint` (prefer `--staged`); document `.pre-commit-config.yaml` snippet in README
4. **GitHub Action** — root `action.yml` composite action wrapping the CLI for PR/CI use (SARIF upload optional/documented, not required inside the action)
5. **Packaging polish** — confirm `pyproject.toml` / hatchling metadata ready for PyPI (`piilint` name, classifiers, entry point); README install via `pipx` / `uvx` / `pip`
6. **Docs** — README: install, pre-commit, Action usage, CI badge once workflows are on `main`; mark Phase 6 done in `BUILD_PLAN.md` when AC met

### Out of scope (Sprint 4)

- Actually publishing the **first** PyPI release to production without Emanuel’s explicit go (prepare workflows + dry-run; cut the tag only when he says)
- GitHub Marketplace listing copy / screenshots (Phase 8 launch collateral)
- NER extra (Phase 7)
- New runtime dependencies

### Acceptance (Sprint 4 done when)

- [ ] `ci.yml` on `main` and green on the matrix (or documented waiver if a platform flake is filed)
- [ ] `release.yml` present with OIDC trusted publishing configured (PyPI project / environment ready or checklist for Emanuel)
- [ ] `.pre-commit-hooks.yaml` works in a smoke test; README snippet correct
- [ ] `action.yml` runnable from a workflow; documented inputs/outputs
- [ ] Package metadata consistent with public `piilint` name
- [ ] Lead Developer review approved
- [ ] PO cleanup; PR to `main`

### Roles

- **Emanuel:** add PAT `workflow` scope (blocker); approve first real PyPI publish
- **Developer:** implement on a feature branch off `main`; report AC on the issue
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
| GitHub PAT missing `workflow` scope | Cannot push `.github/workflows/ci.yml` or `release.yml`; Sprint 4 partially blocked | Emanuel (re-auth PAT with `workflow`) |

---

## Later sprints (preview)

- **Sprint 5 — Optional NER (Phase 7):** `piilint[ner]` + `setup-ner` (after launch OK)
- **Sprint 6 — Launch collateral (Phase 8):** README polish, examples, Marketplace/SEO notes
