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

`piilint` **0.1.0** is on PyPI. Sprint 9 (text/JSON/CSV redact + policy packs) and **Sprint 10** (notebook + parquet redact) are on `main` ([#22](https://github.com/thelonewander3r/PIIScanner/issues/22) / [#23](https://github.com/thelonewander3r/PIIScanner/pull/23)).

**Hold:** no `v0.2.0` (or other prod `v*` tags) without Emanuel’s explicit go.

---

## Sprint 10 — Notebook + Parquet redact (DONE)

**Merged:** [PR #23](https://github.com/thelonewander3r/PIIScanner/pull/23) · closes [#22](https://github.com/thelonewander3r/PIIScanner/issues/22)

### Shipped

- `piilint redact` writes cleaned `.ipynb` copies (source + outputs; binary/image payloads left alone)
- Cleaned `.parquet` for string / large_string / dictionary-string columns via existing pyarrow; nested/non-string left as-is (documented)
- README supported-formats updated; still no in-place; still no new deps

---

## Sprint 9 — DONE (summary)

`piilint redact` for text/JSON/CSV + `examples/policies/` — [#21](https://github.com/thelonewander3r/PIIScanner/pull/21).

---

## Later backlog

Team metadata history (paid wedge), xlsx/PDF, locales, IDE/PR UX, signed releases narrative.
