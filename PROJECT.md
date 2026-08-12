---
title: piilint — Project management
status: active
updated: 2026-08-11
owner: Product Owner
---

# piilint — Project management

Living PO doc for **scope**, **requirements**, and **sprints**. Technical detail: [`BUILD_PLAN.md`](./BUILD_PLAN.md).

**GitHub:** https://github.com/thelonewander3r/PIIScanner  
**Local:** `C:\Users\E_man\Documents\Projects\PIIScanner2`

---

## Status

All BUILD_PLAN phases **0–8** are on `main` (including optional NER). Next: **first PyPI release** — prep only until Emanuel’s explicit go to cut a `v*` tag.

| Area | Status |
|---|---|
| Phases 0–6, 8 | Done |
| Phase 7 NER | Done — [#12](https://github.com/thelonewander3r/PIIScanner/issues/12) / [#13](https://github.com/thelonewander3r/PIIScanner/pull/13) |
| First PyPI / `v0.1.0` | **In progress (Sprint 7)** — [issue #14](https://github.com/thelonewander3r/PIIScanner/issues/14); no tag without Emanuel go |

---

## Sprint 7 — First PyPI release (IN PROGRESS)

**Goal:** Make `piilint` installable via PyPI (`pipx`/`uvx`/`pip`) with a clean 0.1.0 release, without surprising publishes.

**Tracking:** [Issue #14](https://github.com/thelonewander3r/PIIScanner/issues/14) · branch `feature/sprint7-pypi-prep`  
**Hard rule:** Do **not** push a `v*` tag or publish until Emanuel explicitly says go.

### In scope

1. **Version / metadata** — confirm `pyproject.toml` version `0.1.0` (or agreed), name `piilint`, classifiers, entry points, `project.urls`, optional `[ner]` extra documented
2. **Trusted publishing checklist** — document/verify GitHub `pypi` environment + PyPI trusted publisher for `thelonewander3r/PIIScanner` → `release.yml` OIDC job (Emanuel may need to click through PyPI/GitHub UI)
3. **Release dry-run** — `uv build` locally; sanity-check sdist/wheel contents (no secrets, corpus note OK); optional TestPyPI dry-run if Emanuel wants
4. **CHANGELOG** — move Unreleased notes into `0.1.0` section dated for release day
5. **README** — install from PyPI as primary path; keep git/dev install secondary
6. **Release PR** — version bump + changelog/README only; CI green; **tag is a separate, explicit step** after merge + Emanuel go
7. **Post-go runbook** (for PO/Emanuel): `git tag v0.1.0 && git push origin v0.1.0` → watch `release.yml` → verify PyPI + `uvx piilint --version`

### Out of scope

- Cutting the tag in this sprint without Emanuel’s go
- Marketplace listing / SEO deep dive
- New features

### Acceptance

- [ ] Release prep PR merged (version + changelog + docs)
- [ ] Trusted publisher / `pypi` env ready or blocked with a clear Emanuel checklist
- [ ] Local `uv build` succeeds; CI green on the prep PR
- [ ] Written runbook for the tag step
- [ ] Lead Dev review on prep PR
- [ ] Tag/publish only after Emanuel’s explicit go

### Roles

- **Developer:** prep PR (version/changelog/docs); help verify build
- **Lead Developer:** open issue, review prep PR, advise on publisher setup
- **Product Owner:** this scope; merge prep; **stop before tag** until Emanuel go
- **Emanuel:** PyPI/GitHub publisher UI; explicit go to tag

---

## How we work

1. Product Owner owns scope  
2. Lead Dev ↔ Developer via issues + DMs  
3. Developer on feature branch  
4. Lead Dev reviews  
5. Product Owner merges, then next package (here: wait for go to tag)
