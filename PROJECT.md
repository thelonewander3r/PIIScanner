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
- Deterministic recognizers + optional NER post-launch
- Policy / baseline / staged / reporters (console, JSON, SARIF)
- Distribution: PyPI, pre-commit, GitHub Action, CI/release workflows

### Out of scope (v0)

- Secrets scanning · `--redact` · databases/PDF/Office/OCR · telemetry · compliance claims

### Product promise

> Before this file reaches GitHub, an LLM, a vendor, or a fixture directory — tell me if it contains PII, without uploading my data anywhere.

Disclaimer: *piilint helps you find sensitive data before it leaks. It is a detection aid, not a compliance certification, and cannot guarantee that all sensitive data is found.*

---

## Phase map → sprints

| Phase | Theme | Status |
|---|---|---|
| 0–2 | Bootstrap → adapters | Done |
| 3 | Policy & noise | Done — [#1](https://github.com/thelonewander3r/PIIScanner/issues/1) / [#2](https://github.com/thelonewander3r/PIIScanner/pull/2) |
| 4 | Baseline + staged | Done — [#3](https://github.com/thelonewander3r/PIIScanner/issues/3) / [#4](https://github.com/thelonewander3r/PIIScanner/pull/4) |
| 5 | Reporters & DX | Done — [#5](https://github.com/thelonewander3r/PIIScanner/issues/5) / [#6](https://github.com/thelonewander3r/PIIScanner/pull/6) |
| 6 | Distribution | **Done** — [#7](https://github.com/thelonewander3r/PIIScanner/issues/7) / [#8](https://github.com/thelonewander3r/PIIScanner/pull/8) + [#9](https://github.com/thelonewander3r/PIIScanner/pull/9) |
| 7 | Optional NER | After launch OK |
| 8 | Launch collateral | **In progress (Sprint 5)** — [issue #10](https://github.com/thelonewander3r/PIIScanner/issues/10) |

---

## Sprint 4 — Distribution (COMPLETE)

**Merged:** [PR #8](https://github.com/thelonewander3r/PIIScanner/pull/8) (pre-commit, Action, docs) + [PR #9](https://github.com/thelonewander3r/PIIScanner/pull/9) (CI + release workflows)  
**CI:** matrix green (ubuntu/windows/macos × 3.10/3.13)  
**Hold:** no `v*` tag / PyPI publish without Emanuel’s explicit go; configure PyPI trusted publisher + `pypi` environment first

---

## Sprint 5 — Launch collateral (IN PROGRESS)

**Goal:** Make the public repo look launch-ready so first adopters succeed in five minutes.

**Source:** `BUILD_PLAN.md` Phase 8  
**Tracking:** [Issue #10](https://github.com/thelonewander3r/PIIScanner/issues/10)

### In scope

1. **README launch pass** — crisp install (`uvx`/`pipx`/`pip`), quickstart (`piilint .`), pre-commit + Action + SARIF upload examples, baseline adoption path, disclaimer + “not a secrets scanner” pairing note
2. **Examples / demo** — point at (or add) a tiny synthetic demo path (notebook leak story); no real PII
3. **CI badge + status** — README badge once workflows are on `main`
4. **CONTRIBUTING / SECURITY** — short contributor notes; how to report issues (no bounty required)
5. **Changelog stub** — `CHANGELOG.md` starting at unreleased / 0.1.0 prep (no publish yet)
6. **BUILD_PLAN** — mark Phase 8 done when AC met; leave Phase 7 NER explicitly “post-launch”

### Out of scope (Sprint 5)

- Cutting a PyPI release / `v*` tag (Emanuel go + trusted publisher only)
- Implementing NER (Phase 7)
- Paid/team layer features

### Acceptance

- [ ] README is a complete five-minute path (install → scan → pre-commit/Action)
- [ ] CI badge works; disclaimer + pairing guidance present
- [ ] CONTRIBUTING + SECURITY present and accurate
- [ ] CHANGELOG stub ready for 0.1.0
- [ ] Lead Dev review; PO merge

### Roles

- **Developer:** implement on branch off `main`
- **Lead Developer:** open issue, review
- **Product Owner:** this scope; cleanup/PR; **Emanuel** owns first publish go

---

## How we work

1. Product Owner owns scope (this file)
2. Lead Dev ↔ Developer via GitHub issues + DMs
3. Developer implements on a feature branch
4. Lead Dev reviews
5. Product Owner merges, then scopes next package

---

## Open blockers / holds

| Item | Owner |
|---|---|
| First PyPI publish (`v*` tag) — needs explicit go + trusted publisher / `pypi` env | Emanuel |
| Phase 7 NER — deferred until after launch | Product Owner |
