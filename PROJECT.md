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
| R7 | Chassis boundary | adapters / findings / reporters do not import recognizers |
| R8 | Small locked dependency set | Ask before adding deps |
| R9 | Config precedence | CLI > `piilint.toml` > `[tool.piilint]` > defaults |
| R10 | Noise controls | `.piiignore`, inline suppressions, allowlists, test-data downweight, baseline |

Full entity/adapter/reporter specs: see `BUILD_PLAN.md`.

---

## Phase map → sprints

| Phase | Theme | Status (as of 2026-08-11) |
|---|---|---|
| 0 | Bootstrap | Done (on `main`) |
| 1 | Corpus + engine core | Done |
| 2 | Tabular + notebook adapters | Done |
| 3 | Policy & noise | **Done — Lead Dev approved** ([issue #1](https://github.com/thelonewander3r/PIIScanner/issues/1), branch `feature/phase3-policy`) |
| 4 | Baseline + staged mode | **Next (Sprint 2)** |
| 5 | Reporters & DX polish | Not started |
| 6 | Distribution | Not started |
| 7 | Optional NER | After launch OK |
| 8 | Launch collateral | Not started |

---

## Sprint 1 — Policy & noise (COMPLETE)

**Goal:** Make findings controllable and quiet enough for real repos.

**Tracking:** [Issue #1](https://github.com/thelonewander3r/PIIScanner/issues/1)  
**Branch:** `feature/phase3-policy`  
**Brief:** [`PHASE3_DEV_BRIEF.md`](./PHASE3_DEV_BRIEF.md)

### Definition of done

- [x] Phase 3 acceptance checklist met
- [x] Lead Developer review / approve (47 pytest passed; ruff/mypy clean; benchmark gates hold)
- [ ] PO cleanup; PR merged to `main`

---

## Sprint 2 — Baseline + staged (NEXT)

**Goal:** Teams can adopt without fixing history first, and pre-commit only scans what is about to land.

**Source:** `BUILD_PLAN.md` § Policy (baseline) + Phase 4  
**Tracking:** GitHub issue to be opened by Lead Dev from this scope call

### In scope

1. **Baseline command:** `piilint baseline . -o piilint-baseline.json` — fingerprint current findings
2. **Baseline subtract:** `piilint . --baseline piilint-baseline.json` — report **new findings only**
3. **Fingerprint design:** SHA-256(relative path, entity, normalized-value hash, occurrence index) — deliberately excludes line numbers so ordinary edits do not resurrect old findings; document the tradeoff
4. **`--staged`:** scan only git-staged files (pre-commit friendly); implement via `gitutil` as sketched in BUILD_PLAN layout
5. **Tests:** unit tests for fingerprint stability (line-number independence), baseline subtract, staged file selection; benchmark gates remain green
6. **Docs:** README section for baseline + staged; mark Phase 4 done in `BUILD_PLAN.md` when AC met

### Out of scope (Sprint 2)

- JSON / SARIF reporters (Phase 5)
- GitHub Action packaging / pre-commit hook publish (Phase 6 — may *use* `--staged` earlier, but distribution waits)
- NER extra (Phase 7)
- Changing Phase 3 policy behavior unless a baseline bug forces a tiny fix

### Acceptance (Sprint 2 done when)

- [ ] `piilint baseline` writes a stable, versioned baseline file
- [ ] Scan with `--baseline` suppresses known findings and surfaces only new ones
- [ ] Fingerprints ignore line numbers (documented + tested)
- [ ] `--staged` limits scan to staged paths; clear error if not in a git repo / nothing staged as appropriate
- [ ] `uv run pytest` green; ruff + mypy strict clean; benchmark gates hold with real numbers
- [ ] Lead Developer review approved
- [ ] PO cleanup; PR to `main`

### Roles

- **Developer:** implement on a feature branch off `main` (or off merged Phase 3); report AC + numbers on the issue
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
| GitHub PAT missing `workflow` scope | `.github/workflows/ci.yml` still untracked locally; CI cannot run on GitHub yet | Emanuel (re-auth PAT with `workflow`) |
| Sprint 1 PR not yet merged | Phase 3 not on `main` | Product Owner |

---

## Later sprints (preview)

- **Sprint 3 — Reporters & DX (Phase 5):** JSON (schema v1) + SARIF 2.1.0, console polish
- **Sprint 4 — Distribution (Phase 6):** PyPI, pre-commit hook, GitHub Action, release workflow
