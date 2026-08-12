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

`piilint` **0.1.0** is on PyPI. Phases 0–8 + release hardening done. Post-release docs done (#18/#19). **Sprint 9 done** — `piilint redact` + example policy packs on `main` ([#20](https://github.com/thelonewander3r/PIIScanner/issues/20) / [#21](https://github.com/thelonewander3r/PIIScanner/pull/21)).

**Hold:** further prod `v*` tags (e.g. `v0.2.0`) still need Emanuel’s explicit go.

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
