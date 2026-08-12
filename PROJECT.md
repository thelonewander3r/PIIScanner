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

`piilint` **0.1.0** is on PyPI. Sprint 9–10 redact work is on `main` (text/JSON/CSV/notebook/parquet + policy packs).

**Next (Emanuel 2026-08-12):** Sprint 11 in progress ([#24](https://github.com/thelonewander3r/PIIScanner/issues/24)) — xlsx + PDF via `piilint[office]`.  
**Hold:** no `v0.2.0` / prod `v*` tags without Emanuel’s explicit go.

---

## Sprint 11 — xlsx + PDF adapters (IN PROGRESS)

**Goal:** Scan (and where practical, redact) the Office/PDF files data and ops teams actually pass around — without bloating the default install or adding OCR complexity.

**Tracking:** [Issue #24](https://github.com/thelonewander3r/PIIScanner/issues/24) · `piilint[office]` = openpyxl + pypdf  
**Branch:** off `main` → PR → LGTM → PO merge  
**Version:** land on `main` only; **no tag** unless Emanuel goes.

### In scope

1. **xlsx scan adapter** — `.xlsx` (and `.xlsm` if cheap); emit findings from cell text (and optionally sheet names / headers). Preserve chassis boundaries (adapters → scan units → recognizers).
2. **PDF scan adapter** — extract **embedded text** only (no OCR / no images). Document that scanned-image PDFs won’t yield text. Clear skip/warn if a file has no extractable text.
3. **Optional extras** — keep base wheel lean. Prefer something like `piilint[office]` (or `[xlsx]` / `[pdf]`) with pinned deps (e.g. openpyxl / pypdf — Lead Dev picks). Missing extra → clear exit-2 / skip message, not a hard crash mid-walk if possible (document behavior).
4. **Redact (stretch, same sprint if it fits)** — `piilint redact` cleaned `.xlsx` copies for string cells (mirror parquet/csv story). **PDF redact** only if Lead Dev judges it safe/simple in this sprint; otherwise explicit follow-up (rewriting PDFs is easy to get wrong).
5. **Corpus + tests** — synthetic xlsx + PDF fixtures with fake PII; hard negatives; no real customer data; CI gate still holds for core entities.
6. **Docs** — README supported formats + install extras; disclaimer unchanged (not compliance); BUILD_PLAN “more formats” note updated.
7. **Windows-first** — path + encoding behavior sane on Windows 11.

### Out of scope

- docx (unless trivial piggyback — default **no**)
- OCR / image-only PDFs
- Cutting a PyPI tag
- Paid team / metadata layer
- Locales / national ID packs

### Acceptance

- [ ] `piilint` with the office extra finds PII in synthetic `.xlsx` and text-based `.pdf`
- [ ] Base install stays lean (extra documented; no surprise heavy deps)
- [ ] Tests + CI green (package-smoke still passes without office extra)
- [ ] README documents install + limitations (no OCR)
- [ ] Lead Dev LGTM; PO merge
- [ ] Redact xlsx either shipped or explicitly deferred in the PR body / PROJECT note

### Roles

- **Developer:** feature branch; report AC + any deferred redact
- **Lead Developer:** open issue; pick deps/extra layout; review architecture
- **Product Owner:** this scope; merge; hold tags

---

## Recent done

- Sprint 10 — notebook + parquet redact — [#23](https://github.com/thelonewander3r/PIIScanner/pull/23)
- Sprint 9 — redact + policy packs — [#21](https://github.com/thelonewander3r/PIIScanner/pull/21)

---

## Later backlog

Team metadata history (paid wedge), locales, IDE/PR UX, signed releases narrative; PDF redact if deferred; docx.
