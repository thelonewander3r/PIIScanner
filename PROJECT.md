---
title: piilint — Project management
status: active
updated: 2026-08-17
owner: Product Owner
---

# piilint — Project management

**GitHub:** https://github.com/thelonewander3r/PIIScanner  
**PyPI:** https://pypi.org/project/piilint/ (`0.1.0` published; `0.2.0` prep — not tagged)  
**Local:** `C:\Users\E_man\Documents\Projects\PIIScanner2`

---

## Status

`piilint` **0.1.0** is on PyPI. Sprints 9–15 on `main` (redact, policy packs, office, locales, team-layer **design**, Slice B local metadata history via [#38](https://github.com/thelonewander3r/PIIScanner/pull/38)).

**IN PROGRESS (2026-08-17):** Sprint 16 — **0.2.0 release prep**. Tracking [#40](https://github.com/thelonewander3r/PIIScanner/issues/40). No tag until explicit go.  
**Paused:** further team-layer / hosted sync (Slice B local MVP already shipped; no SaaS).  
**Verify:** Local Tester (Windows); **no GHA**.

---

## Sprint 16 — 0.2.0 release prep (IN PROGRESS)

**Goal:** Make `main` (sprints 9–13 + Slice B local MVP) installable as `piilint` 0.2.0, without publishing until Emanuel goes.

**Tracking:** [#40](https://github.com/thelonewander3r/PIIScanner/issues/40)  
**Branch:** `feature/sprint16-0.2.0-prep` → PR → Local Tester green + Lead LGTM → PO merge  
**Hard rule:** do **not** push `v0.2.0` or publish until Emanuel's explicit go.  
**Verify:** Local Tester (no GHA).

### In scope

1. Version bump `0.1.0` → `0.2.0` (`pyproject.toml`, `__init__.py`, any other pins)
2. CHANGELOG: fold Unreleased (redact, policy packs, office xlsx/pdf/docx, locales + Slice B local MVP already on main via #38) into `[0.2.0]`; **omit** unfinished team-layer / hosted sync
3. README: what's new + supported formats; PyPI install still primary (do not claim 0.2.0 is on PyPI)
4. `docs/RELEASE.md`: 0.2.0 prep checklist; Local Tester gates (not GHA); same tag runbook as 0.1.0 with tag/publish unchecked until Emanuel go
5. Local `uv build` dry-run; Local Tester: ruff/mypy/pytest + package-smoke + office
6. PROJECT.md this sprint

### Out of scope

- Cutting `v0.2.0` / PyPI publish
- TestPyPI unless Emanuel asks
- Further Slice B / team SaaS
- New features

### Acceptance

- [ ] Prep PR opened (Developer does not merge)
- [ ] Version is `0.2.0` in package metadata
- [ ] CHANGELOG has dated `[0.2.0]` covering sprints 9–13 + Slice B already on main
- [ ] README + `docs/RELEASE.md` updated; Local Tester path documented
- [ ] Local Tester green on the prep branch (required + package-smoke + office)
- [ ] Lead Dev LGTM
- [ ] Written stop-before-tag (PO waits for Emanuel go)

### Roles

- **Developer:** prep PR
- **Lead Developer:** review
- **Local Tester:** full local gate
- **Product Owner:** merge prep; **stop before tag**
- **Emanuel:** explicit go to tag

---

## Shipped — Sprint 15 Slice B (local MVP)

[#38](https://github.com/thelonewander3r/PIIScanner/pull/38) / [#37](https://github.com/thelonewander3r/PIIScanner/issues/37) — local metadata history on `main`: `report --metadata-only`, `history --since`, `sync --metadata --dry-run`. No network / no SaaS. Further team-layer paused until after 0.2.0.

---

## Recent done

- Sprint 15 Slice B — local metadata history — [#38](https://github.com/thelonewander3r/PIIScanner/pull/38)
- Sprint 14 — team layer design — [#35](https://github.com/thelonewander3r/PIIScanner/pull/35)
- Sprint 13 — docx — [#30](https://github.com/thelonewander3r/PIIScanner/pull/30)
- Sprint 9–12 — redact, office, locales

---

## Later backlog

Ship 0.2.0 on go → adoption → then further team-layer / hosted sync. IDE/PR UX; PDF redact; more locales.
