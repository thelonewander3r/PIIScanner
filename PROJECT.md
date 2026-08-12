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

`piilint` **0.1.0** is on PyPI. Sprints 9–11 on `main` (redact + policy packs + `piilint[office]`).

**Next (Emanuel 2026-08-12):** Sprint 12 — **locale coverage** (phones + a few non-US national IDs).  
**Hold:** no `v0.2.0` / prod `v*` tags without Emanuel’s explicit go.

---

## Sprint 12 — Locale coverage (NEXT)

**Goal:** Stop being “US startup only.” Improve phone multi-region behavior and add a **small, precision-first** set of non-US national-ID recognizers with real validators where they exist. No compliance claims.

**Tracking:** issue to be opened by Lead Dev from this scope call  
**Branch:** off `main` → PR → LGTM → PO merge  
**Version:** land on `main` only; **no tag** unless Emanuel goes.

### In scope

1. **Phone multi-region** — today default region is US (`phone_region` / `PhoneRecognizer`). Extend so orgs can set one primary region **and** optionally extra regions (or document a clear multi-region story Lead Dev designs). Must not explode false positives on US corpora. Keep using `phonenumbers` (already a base dep).
2. **National IDs (pick ~2–4, checksum/context required)** — examples Lead Dev may choose from (not a mandate to do all):
   - Canada SIN (Luhn) as e.g. `SIN_CA`
   - UK National Insurance (strict format + strong context words; precision over recall)
   - One EU national ID **with** a known checksum (e.g. NL BSN 11-check) if it fits cleanly
   - Prefer **off by default** or region-gated if noise risk is high — Lead Dev decides; document defaults
3. **Config / policy** — `entity_enabled` toggles; wire into severity/allowlists/baseline fingerprints like other entities. Example policy pack note or a fourth pack only if cheap.
4. **Corpus + gates** — synthetic true positives + hard negatives per new entity; **core US gates must not regress** (email/phone/ssn/card/iban). New entities may have separate metrics if not in the core recall gate.
5. **Docs** — README: how to set regions / enable IDs; hard disclaimer (detection aid, not legal ID verification, not GDPR/HIPAA/PCI). Update BUILD_PLAN “more locales” note.
6. **Redact** — new entities must mask via existing `mask_value` path (no raw PII in outputs).
7. **Deps** — prefer no new packages; **ask before** adding any.

### Out of scope

- Exhaustive world catalog of national IDs
- OCR / address localization / non-English NER models
- PDF redact, docx
- Paid team / metadata layer
- Cutting a PyPI tag
- Compliance certification language anywhere

### Acceptance

- [ ] Multi-region phone story works and is documented; US default behavior stays sane
- [ ] ≥2 new national-ID (or clearly scoped locale) recognizers with validators/context; tests prove precision on hard negatives
- [ ] Core benchmark gates still green with real numbers
- [ ] Config toggles + masking work; ruff/mypy/CI green
- [ ] README + disclaimer updated
- [ ] Lead Dev LGTM; PO merge

### Roles

- **Developer:** feature branch; report AC + gate numbers
- **Lead Developer:** open issue; choose exact ID set + on/off defaults; review
- **Product Owner:** this scope; merge; hold tags

---

## Recent done

- Sprint 11 — `piilint[office]` xlsx/PDF — [#25](https://github.com/thelonewander3r/PIIScanner/pull/25)
- Sprint 10 — notebook + parquet redact — [#23](https://github.com/thelonewander3r/PIIScanner/pull/23)
- Sprint 9 — redact + policy packs — [#21](https://github.com/thelonewander3r/PIIScanner/pull/21)

---

## Later backlog

Team metadata history (paid wedge), IDE/PR UX, signed releases narrative; PDF redact; docx; more locales beyond this sprint.
