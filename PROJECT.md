---
title: piilint — Project management
status: active
updated: 2026-08-12
owner: Product Owner
---

# piilint — Project management

**GitHub:** https://github.com/thelonewander3r/PIIScanner  
**PyPI:** https://pypi.org/project/piilint/ (`0.1.0`)  
**Local:** `C:\Users\E_man\Documents\Projects\PIIScanner2`

---

## Status

`piilint` **0.1.0** is on PyPI. Sprint 9 (`redact` + policy packs) done on `main` ([#20](https://github.com/thelonewander3r/PIIScanner/issues/20) / [#21](https://github.com/thelonewander3r/PIIScanner/pull/21)).

**Next:** Sprint 10 in progress ([#22](https://github.com/thelonewander3r/PIIScanner/issues/22)) ? notebook + parquet redact.  
**Hold:** no `v0.2.0` (or other prod `v*` tags) without Emanuel?s explicit go.

---


## Sprint 10 ? Notebook + Parquet redact (IN PROGRESS)

**Goal:** Extend `piilint redact` so `.ipynb` (incl. output cells) and `.parquet` get cleaned copies like text/JSON/CSV.

**Tracking:** [Issue #22](https://github.com/thelonewander3r/PIIScanner/issues/22) ? branch `feature/sprint10-notebook-parquet-redact`  
**Version:** land on `main` only; **do not** cut `v0.2.0` unless Emanuel goes.

### In scope

1. Notebooks ? source + outputs; nbformat-compatible copy under `-o`
2. Parquet ? string / dictionary-string columns; document nested limits
3. Same policy/mask path; no in-place; no new base deps
4. Tests + README ?supported today?

### Acceptance

- [ ] Cleaned `.ipynb` + `.parquet` copies; sources untouched
- [ ] Notebook **outputs** covered
- [ ] Tests / CI / ruff / mypy green
- [ ] README updated
- [ ] Lead Dev LGTM; PO merge

---

## Sprint 9 — Redact + example policy packs (DONE)

**Merged:** [PR #21](https://github.com/thelonewander3r/PIIScanner/pull/21) · closes [#20](https://github.com/thelonewander3r/PIIScanner/issues/20)

### Shipped

- `piilint redact PATH -o OUT_DIR` — cleaned **copies** only (no in-place v1); text + json/jsonl + csv/tsv; base wheel, no new deps
- `examples/policies/` — `strict-ci`, `data-eng`, `open-source-lib` + README (no compliance claims); linked from main README
- Notebooks/parquet redact left as follow-up

### Follow-ups (not blocking)

- Redact for notebooks / parquet
- Ask Emanuel whether to cut `v0.2.0` for this work

---

## Later backlog

Team metadata history (paid wedge), xlsx/PDF, locales, IDE/PR UX, signed releases narrative; notebook/parquet redact.
