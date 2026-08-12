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

`piilint` **0.1.0** is on PyPI. Sprints 9–13 on `main` (redact, policy packs, office xlsx/PDF/docx, locales).

**Hold:** no `v0.2.0` / prod `v*` tags without Emanuel’s explicit go.

**Verify:** GitHub Actions offline — Local Tester runs the former CI suite locally (Windows); Lead Dev LGTMs on review + local green.

---

## Sprint 13 — docx adapters (DONE)

**Merged:** [PR #30](https://github.com/thelonewander3r/PIIScanner/pull/30) · closes [#29](https://github.com/thelonewander3r/PIIScanner/issues/29)  
**Verified:** Local Tester GREEN @ `ed1952e` (required + office + package-smoke); Lead Dev LGTM; merged without GHA (Emanuel go).

### Shipped

- `.docx` scan under `piilint[office]` (`python-docx`): paragraphs, tables, headers/footers
- Cleaned-copy redact for `.docx`
- Corpus + tests; office smoke extended

---

## Recent done

- Sprint 12 — locales — [#27](https://github.com/thelonewander3r/PIIScanner/pull/27)
- Sprint 11 — xlsx/PDF — [#25](https://github.com/thelonewander3r/PIIScanner/pull/25)
- Sprint 10 — notebook + parquet redact — [#23](https://github.com/thelonewander3r/PIIScanner/pull/23)
- Sprint 9 — redact + policy packs — [#21](https://github.com/thelonewander3r/PIIScanner/pull/21)

---

## Later backlog

Team metadata history (paid wedge) — design next if Emanuel agrees; IDE/PR UX; signed releases narrative; PDF redact; more locales.
