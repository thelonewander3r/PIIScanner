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

`piilint` **0.1.0** is on PyPI. Sprints 9–12 on `main` (redact, policy packs, `piilint[office]` xlsx/PDF, locales).

**Next (Emanuel 2026-08-12):** Sprint 13 — **docx** scan (+ redact stretch) under `piilint[office]`.  
**Hold:** no `v0.2.0` / prod `v*` tags without Emanuel’s explicit go.

**Queued after (strategic):** paid team / findings-metadata layer design — say if you want that instead of more formats.

---

## Sprint 13 — docx adapters (NEXT)

**Goal:** Cover Word docs the same way we cover Excel — scan (and where practical, redact) `.docx` via the existing optional office extra, without OCR or bloating the base wheel.

**Tracking:** issue to be opened by Lead Dev from this scope call  
**Branch:** off `main` → PR → LGTM → PO merge  
**Version:** land on `main` only; **no tag** unless Emanuel goes.

### In scope

1. **docx scan adapter** — `.docx` paragraph + table cell text (headers/footers if cheap). Chassis boundaries intact. Skip `.doc` (legacy binary) unless trivial — default **no**.
2. **Extra** — fold into existing `piilint[office]` (add python-docx or Lead Dev’s pick). **Ask before** locking the dep. Missing extra → same clear skip pattern as xlsx/PDF.
3. **Redact stretch** — cleaned `.docx` copies under `piilint redact -o` for paragraph/table text if it fits safely; otherwise defer explicitly (don’t corrupt documents).
4. **Corpus + tests** — synthetic `.docx` with fake PII + hard negatives; office smoke extended or parallel; package-smoke still without office.
5. **Docs** — README supported formats; BUILD_PLAN note; no compliance claims.
6. **Windows-first**

### Out of scope

- Legacy `.doc`, macros-as-code analysis, embedded images/OCR
- PDF redact (still deferred)
- Paid team / metadata SaaS
- Cutting a PyPI tag
- More national-ID locales (unless tiny drive-by)

### Acceptance

- [ ] With `piilint[office]`, scan finds PII in synthetic `.docx`
- [ ] Base install unchanged; skip message clear without office
- [ ] Tests + CI green (incl. package-smoke without office)
- [ ] README updated; Lead Dev LGTM; PO merge
- [ ] Redact docx shipped or explicitly deferred in PR body

### Roles

- **Developer:** feature branch; report AC
- **Lead Developer:** open issue; pick docx library; review
- **Product Owner:** this scope; merge; hold tags

---

## Recent done

- Sprint 12 — locales (phone_regions + SIN_CA / NINO_UK / BSN_NL) — [#27](https://github.com/thelonewander3r/PIIScanner/pull/27)
- Sprint 11 — `piilint[office]` xlsx/PDF — [#25](https://github.com/thelonewander3r/PIIScanner/pull/25)
- Sprint 10 — notebook + parquet redact — [#23](https://github.com/thelonewander3r/PIIScanner/pull/23)
- Sprint 9 — redact + policy packs — [#21](https://github.com/thelonewander3r/PIIScanner/pull/21)

---

## Later backlog

Team metadata history (paid wedge) — **design next after formats if Emanuel agrees**; IDE/PR UX; signed releases narrative; PDF redact; more locales.
