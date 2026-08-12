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

**Next (Emanuel 2026-08-12):** Sprint 10 in progress ([#22](https://github.com/thelonewander3r/PIIScanner/issues/22)) — notebooks + parquet redact.  
**Hold:** no `v0.2.0` (or other prod `v*` tags) without Emanuel’s explicit go.

---

## Sprint 10 — Notebook + Parquet redact (IN PROGRESS)

**Goal:** Extend `piilint redact` so the formats that matter most for the product story (`.ipynb` leak demos, Parquet exports) get cleaned copies the same way text/JSON/CSV already do.

**Tracking:** [Issue #22](https://github.com/thelonewander3r/PIIScanner/issues/22)  
**Branch:** off `main` → PR → LGTM → PO merge  
**Version:** land on `main` only; **do not** cut `v0.2.0` unless Emanuel goes.

### In scope

1. **Notebooks (`.ipynb`)** — write a cleaned `.ipynb` under `-o` mirroring relative paths. Redact PII in **code + markdown + outputs** (the classic `df.head()` leak is output cells). Preserve valid notebook JSON structure (nbformat-compatible). Prefer reusing existing notebook adapter scan units / finding spans rather than a parallel parser.
2. **Parquet** — write cleaned `.parquet` copies under `-o`. Redact string (and other textual) column values via the same span/mask path as CSV where practical. Keep binary/schema sane; document any type limitations (e.g. nested/list columns).
3. **CLI / UX** — same `piilint redact PATH -o OUT_DIR`; unsupported types still skip with a clear count. Still **no in-place** default. Update “supported today” docs in README + BUILD_PLAN.
4. **Policy** — same config as scan/redact today (allowlists, `# piilint: ignore` where applicable, entity toggles, min_confidence, excludes).
5. **Deps** — stay on the base wheel if possible (pyarrow already used for Parquet scan?). **Ask before** adding new production deps. No `presidio-anonymizer` unless Lead Dev makes a strong case + optional extra.
6. **Tests** — synthetic fixtures (reuse/extend `tests/corpus/notebook`, parquet corpus); assert no raw corpus PII in outputs; round-trip scan of redacted notebook/parquet finds fewer/no those entities; structure checks (notebook still loads).
7. **Safety** — no raw PII in logs; Windows path-safe; exit 2 on usage/config.

### Out of scope

- In-place overwrite
- xlsx/PDF
- Cutting a PyPI tag
- Paid team/metadata layer

### Acceptance

- [ ] `redact` writes cleaned `.ipynb` and `.parquet` copies to `-o`; sources untouched
- [ ] Output cells in notebooks are covered (not only source)
- [ ] Tests + CI (incl. package-smoke) green; ruff/mypy clean
- [ ] README supported-formats line updated
- [ ] Lead Dev LGTM; PO merge

### Roles

- **Developer:** implement on feature branch; report AC
- **Lead Developer:** open issue, architecture (notebook rewrite + parquet column strategy), review
- **Product Owner:** this scope; merge; still hold tags

---

## Sprint 9 — DONE (summary)

`piilint redact` for text/JSON/CSV + `examples/policies/` — [#21](https://github.com/thelonewander3r/PIIScanner/pull/21).

---

## Later backlog

Team metadata history (paid wedge), xlsx/PDF, locales, IDE/PR UX, signed releases narrative.
