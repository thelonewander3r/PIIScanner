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

`piilint` **0.1.0** is on PyPI. Sprints 9–11 on `main`: redact (text/JSON/CSV/notebook/parquet) + policy packs + optional **xlsx/PDF** via `piilint[office]`.

**Hold:** no `v0.2.0` / prod `v*` tags without Emanuel’s explicit go.

---

## Sprint 11 — xlsx + PDF adapters (DONE)

**Merged:** [PR #25](https://github.com/thelonewander3r/PIIScanner/pull/25) · closes [#24](https://github.com/thelonewander3r/PIIScanner/issues/24)

### Shipped

- Optional `piilint[office]` (openpyxl + pypdf); base wheel stays lean
- `.xlsx` / `.xlsm` scan + cleaned-copy redact for string cells
- PDF **text** scan only (no OCR); blank/image PDFs skip cleanly
- Synthetic corpus + unit tests; CI optional office smoke; package-smoke still without office

### Follow-ups

- PDF redact (deferred — rewrite risk)
- docx, OCR, locales, paid team/metadata layer

---

## Recent done

- Sprint 10 — notebook + parquet redact — [#23](https://github.com/thelonewander3r/PIIScanner/pull/23)
- Sprint 9 — redact + policy packs — [#21](https://github.com/thelonewander3r/PIIScanner/pull/21)

---

## Later backlog

Team metadata history (paid wedge), locales, IDE/PR UX, signed releases narrative; PDF redact; docx.
