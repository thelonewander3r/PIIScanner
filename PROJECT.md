---
title: piilint — Project management
status: active
updated: 2026-08-17
owner: Product Owner
---

# piilint — Project management

**GitHub:** https://github.com/thelonewander3r/PIIScanner  
**PyPI:** https://pypi.org/project/piilint/ (`0.1.0`)  
**Local:** `C:\Users\E_man\Documents\Projects\PIIScanner2`

---

## Status

`piilint` **0.1.0** is on PyPI. Sprints 9–14 on `main` (redact, policy packs, office, locales, team-layer **design**).

**Next (Emanuel 2026-08-17):** Sprint 16 — **0.2.0 release prep**. No tag until explicit go.  
**Paused:** Slice B / team-layer build ([#37](https://github.com/thelonewander3r/PIIScanner/issues/37) parked). Get the CLI to the wild first.  
**Verify:** Local Tester (Windows); not GitHub Actions.

---

## Sprint 16 — 0.2.0 release prep (NEXT)

**Goal:** Make `main` (sprints 9–13) installable as `piilint` 0.2.0, without publishing until Emanuel goes.

**Tracking:** issue to be opened by Lead Dev from this scope call  
**Branch:** off `main` → PR → Local Tester green + Lead LGTM → PO merge  
**Hard rule:** do **not** push `v0.2.0` or publish until Emanuel’s explicit go.

### In scope

1. Version bump `0.1.0` → `0.2.0` (`pyproject.toml`, `__init__.py`, any other pins)
2. CHANGELOG: fold Unreleased (redact, policy packs, office xlsx/pdf/docx, locales) into `[0.2.0]`; **omit** unfinished Slice B
3. README: what’s new + supported formats; PyPI install still primary
4. `docs/RELEASE.md`: 0.2.0 prep checklist; Local Tester gates (not GHA); same tag runbook as 0.1.0
5. Local `uv build` dry-run; Local Tester: ruff/mypy/pytest + package-smoke + office
6. PROJECT.md this sprint

### Out of scope

- Cutting `v0.2.0` / PyPI publish
- TestPyPI unless Emanuel asks
- Slice B / team SaaS
- New features

### Acceptance

- [ ] Prep PR merged (version + changelog + docs)
- [ ] Local Tester green on the prep branch
- [ ] Lead Dev LGTM
- [ ] Written stop-before-tag (PO waits for Emanuel go)

### Roles

- **Developer:** prep PR
- **Lead Developer:** open issue, review
- **Local Tester:** full local gate
- **Product Owner:** merge prep; **stop before tag**
- **Emanuel:** explicit go to tag

---

## Paused — Sprint 15 Slice B

[#37](https://github.com/thelonewander3r/PIIScanner/issues/37) — local metadata history. Parked; branch `feature/sprint15-metadata-history` exists, no PR. Resume only if Emanuel reorders.

---

## Recent done

- Sprint 14 — team layer design — [#35](https://github.com/thelonewander3r/PIIScanner/pull/35)
- Sprint 13 — docx — [#30](https://github.com/thelonewander3r/PIIScanner/pull/30)
- Sprint 9–12 — redact, office, locales

---

## Later backlog

Ship 0.2.0 on go → adoption → then Slice B / team infra. IDE/PR UX; PDF redact; more locales.
