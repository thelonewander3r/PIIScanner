---
title: piilint — Project management
status: active
updated: 2026-08-11
owner: Product Owner
---

# piilint — Project management

Living PO doc for **scope**, **requirements**, and **sprints**. Technical build detail stays in [`BUILD_PLAN.md`](./BUILD_PLAN.md).

**One-liner:** Find PII in the files developers actually commit and send — notebooks, CSV, JSON, Parquet, and source code. Everything stays local.

**GitHub:** https://github.com/thelonewander3r/PIIScanner  
**Local:** `C:\Users\E_man\Documents\Projects\PIIScanner2`

---

## Status

Phases **0–6 + 8** are done on `main`. Next ordered by Emanuel (2026-08-11):

1. **Sprint 6 — Phase 7 optional NER** (now)
2. **First PyPI / `v*` release** (after NER; still needs explicit go + trusted publisher)

| Phase | Theme | Status |
|---|---|---|
| 0–6, 8 | MVP + launch collateral | Done |
| 7 | Optional NER | **Done (Sprint 6)** — [issue #12](https://github.com/thelonewander3r/PIIScanner/issues/12) |
| — | First PyPI publish | Queued after Sprint 6 |

---

## Sprint 6 — Optional NER (DONE)

**Goal:** Add PERSON/ADDRESS detection as a heavy optional extra without bloating the base install or breaking the no-scan-time-network promise.

**Source:** `BUILD_PLAN.md` locked NER decision + Phase 7 + entity table  
**Tracking:** [Issue #12](https://github.com/thelonewander3r/PIIScanner/issues/12)

### In scope

1. **Optional extra** — populate `piilint[ner]` in `pyproject.toml` with `presidio-analyzer` + spaCy (versions pinned/compatible with Python 3.10–3.13); base install stays lean (`ner = []` today)
2. **`piilint setup-ner`** — explicit command to fetch/install the English model; **only** allowed network path besides CI/release; clear errors if model missing when `--ner` is used
3. **Recognizer** — PERSON + ADDRESS via Presidio/spaCy; default **off**; require both `[ner]` extra **and** `--ner` (and/or config toggle) to emit
4. **Severity / confidence** — default medium; integrate with existing policy (allowlists, min_confidence, fail-on, baseline fingerprints)
5. **Chassis rules** — keep adapters/findings/baseline/reporters free of recognizer imports; NER lives under `recognizers/`
6. **Corpus + tests** — synthetic NER true positives in prose (per BUILD_PLAN corpus note); hard negatives stay clean; benchmark gates must not regress for core entities; document NER metrics separately if not in the core recall gate
7. **Docs** — README: install `[ner]`, `setup-ner`, `--ner` examples; disclaimer unchanged; mark Phase 7 done in `BUILD_PLAN.md` when AC met
8. **Windows-first** — setup and scan path work on Windows 11

### Out of scope (Sprint 6)

- Non-English NER models
- PyPI / `v*` tag (next package after this)
- `--redact` / anonymizer
- Turning NER on by default

### Acceptance

- [x] `pip`/`uv` install without `[ner]` does not pull Presidio/spaCy
- [x] `piilint[ner]` + `setup-ner` enables `--ner` scans for PERSON/ADDRESS
- [x] Without setup/model, `--ner` fails clearly (exit 2), not silently
- [x] Default scans (no `--ner`) unchanged vs current MVP
- [x] pytest + core benchmark gates still hold with real numbers; ruff/mypy clean
- [x] No scan-time network except inside `setup-ner`
- [ ] Lead Dev review; PO merge

### Roles

- **Developer:** feature branch off `main`; report AC + numbers on the issue
- **Lead Developer:** open issue, architecture review
- **Product Owner:** this scope; cleanup/PR; then scope PyPI release package

---

## Queued after Sprint 6 — First PyPI release

Prep trusted publisher + `pypi` environment, confirm 0.1.0 metadata, dry-run build, then cut `v*` **only** on Emanuel’s explicit go. No publish work starts until NER merges (unless he reorders).

---

## How we work

1. Product Owner owns scope (this file)
2. Lead Dev ↔ Developer via GitHub issues + DMs
3. Developer implements on a feature branch
4. Lead Dev reviews
5. Product Owner merges, then scopes next package
