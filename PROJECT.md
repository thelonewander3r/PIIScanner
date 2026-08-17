---
title: piilint — Project management
status: active
updated: 2026-08-17
owner: Product Owner
---

# piilint — Project management

**GitHub:** https://github.com/thelonewander3r/PIIScanner  
**PyPI:** https://pypi.org/project/piilint/ (`0.2.0` published)  
**Local:** `C:\Users\E_man\Documents\Projects\PIIScanner2`

---

## Status

`piilint` **0.2.0** is on PyPI (tag `v0.2.0` @ `5b889db`, OIDC Actions run [32043477260](https://github.com/thelonewander3r/PIIScanner/actions/runs/32043477260)). Repo is public. Sprints 9–16 on `main` (redact, policy packs, office, locales, team-layer **design**, Slice B local metadata history, 0.2.0 publish).

**IN PROGRESS (2026-08-17):** Sprint 17 — **xlsx NER redact** ([#49](https://github.com/thelonewander3r/PIIScanner/issues/49)): `piilint redact --ner` must mask PERSON/ADDRESS that scan-with-NER already finds in xlsx. Parent [#44](https://github.com/thelonewander3r/PIIScanner/issues/44). Slice A xlsx numeric-cell redact **done** ([#47](https://github.com/thelonewander3r/PIIScanner/pull/47) / [#45](https://github.com/thelonewander3r/PIIScanner/issues/45)). Slice B PDF embedded-text redact **done** on `main` ([#46](https://github.com/thelonewander3r/PIIScanner/issues/46)). Local AI chats + PDF-layout parked.  
**DONE (2026-08-17):** Sprint 16 — **0.2.0 published**. Tracking [#40](https://github.com/thelonewander3r/PIIScanner/issues/40). Post-publish docs: [#42](https://github.com/thelonewander3r/PIIScanner/issues/42).  
**Paused:** further team-layer / hosted sync (Slice B local MVP already shipped; no SaaS).  
**Verify:** Local Tester (Windows); **no GHA**.

---

## Sprint 17 — redact gaps (IN PROGRESS)

**Goal:** `piilint redact` should clean the same PII `scan` already finds in office files.  
**Tracking:** [#44](https://github.com/thelonewander3r/PIIScanner/issues/44) (parent). Slice A **done** ([#47](https://github.com/thelonewander3r/PIIScanner/pull/47) / [#45](https://github.com/thelonewander3r/PIIScanner/issues/45)). Slice B PDF embedded-text **done** on `main` ([#46](https://github.com/thelonewander3r/PIIScanner/issues/46)). **This slice:** xlsx NER redact ([#49](https://github.com/thelonewander3r/PIIScanner/issues/49)).  
**Parked:** local AI chats; PDF-layout-preserving redact.  
**Verify:** Local Tester (Windows); **no GHA**.  
**Hard stop:** no new `v*` tag / PyPI until Emanuel go.

### In scope (xlsx NER redact — #49)

1. `piilint redact --ner` masks PERSON/ADDRESS in xlsx/xlsm text cells (and any cell type scan already reports)
2. Scan and redact stay consistent when `--ner` is on; `--ner` stays optional / off by default
3. Synthetic fixture only (fake Agent-column names + numeric phones); copies via `-o` only
4. No new production deps (Presidio/spaCy already in `[ner]`); existing office + NER tests stay green

### Out of scope

- Making NER default
- PDF layout-preserving redact (parked)
- Local AI chats (parked)
- Team layer / SaaS
- In-place overwrite
- New production deps
- New `v*` tag

---

## Sprint 16 — 0.2.0 release (DONE)

**Goal:** Make `main` (sprints 9–13 + Slice B local MVP) installable as `piilint` 0.2.0.

**Tracking:** [#40](https://github.com/thelonewander3r/PIIScanner/issues/40)  
**Published:** tag `v0.2.0` @ `5b889db` via OIDC (Actions run [32043477260](https://github.com/thelonewander3r/PIIScanner/actions/runs/32043477260)).  
**Hard rule:** do **not** push the next `v*` tag or publish until Emanuel's explicit go.  
**Verify:** Local Tester (no GHA).

### In scope (completed)

1. Version bump `0.1.0` → `0.2.0` (`pyproject.toml`, `__init__.py`, any other pins)
2. CHANGELOG: fold Unreleased (redact, policy packs, office xlsx/pdf/docx, locales + Slice B local MVP already on main via #38) into `[0.2.0]`; **omit** unfinished team-layer / hosted sync
3. README: what's new + supported formats; PyPI install still primary
4. `docs/RELEASE.md`: 0.2.0 checklist; Local Tester gates (not GHA); same tag runbook as 0.1.0
5. Local `uv build` dry-run; Local Tester: ruff/mypy/pytest + package-smoke + office
6. PROJECT.md this sprint
7. Tag `v0.2.0` + OIDC PyPI publish (after Emanuel go)

### Out of scope

- Next `v*` tag / republish
- TestPyPI unless Emanuel asks
- Further Slice B / team SaaS
- Sprint 17 / local AI chats
- New features

### Acceptance

- [x] Prep PR opened (Developer does not merge)
- [x] Version is `0.2.0` in package metadata
- [x] CHANGELOG has dated `[0.2.0]` covering sprints 9–13 + Slice B already on main
- [x] README + `docs/RELEASE.md` updated; Local Tester path documented
- [x] Local Tester green on the prep branch (required + package-smoke + office)
- [x] Lead Dev LGTM
- [x] Emanuel go; `v0.2.0` tagged and published via OIDC

### Roles

- **Developer:** prep PR
- **Lead Developer:** review
- **Local Tester:** full local gate
- **Product Owner:** merge prep; **stop before tag**
- **Emanuel:** explicit go to tag

---

## Shipped — Sprint 15 Slice B (local MVP)

[#38](https://github.com/thelonewander3r/PIIScanner/pull/38) / [#37](https://github.com/thelonewander3r/PIIScanner/issues/37) — local metadata history on `main`: `report --metadata-only`, `history --since`, `sync --metadata --dry-run`. No network / no SaaS. Further team-layer paused.

---

## Recent done

- Sprint 16 — 0.2.0 published on PyPI — [#40](https://github.com/thelonewander3r/PIIScanner/issues/40)
- Sprint 15 Slice B — local metadata history — [#38](https://github.com/thelonewander3r/PIIScanner/pull/38)
- Sprint 14 — team layer design — [#35](https://github.com/thelonewander3r/PIIScanner/pull/35)
- Sprint 13 — docx — [#30](https://github.com/thelonewander3r/PIIScanner/pull/30)
- Sprint 9–12 — redact, office, locales

---

## Later backlog

0.2.0 is shipped. Sprint 17 = redact gaps (#44; Slice A #47 done; Slice B #46 PDF embedded-text done; #49 xlsx NER redact in progress); local AI chats + PDF-layout parked. Adoption → then further team-layer / hosted sync. IDE/PR UX; more locales.
