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

All BUILD_PLAN phases **0–8** are on `main` (including optional NER). **Sprint 7 prep** (metadata, CHANGELOG, README, `docs/RELEASE.md`, `uv build` dry-run) is underway on `feature/sprint7-pypi-prep`. Package is **not published**; no `v*` tag without Emanuel’s explicit go.

| Area | Status |
|---|---|
| Phases 0–6, 8 | Done |
| Phase 7 NER | Done — [#12](https://github.com/thelonewander3r/PIIScanner/issues/12) / [#13](https://github.com/thelonewander3r/PIIScanner/pull/13) |
| First PyPI / `v0.1.0` | **Prep in progress (Sprint 7)** — [issue #14](https://github.com/thelonewander3r/PIIScanner/issues/14); **not published**; no tag without Emanuel go |

---

## Sprint 7 — First PyPI release prep (IN PROGRESS)

**Goal:** Make `piilint` installable via PyPI (`pipx`/`uvx`/`pip`) with a clean 0.1.0 release, without surprising publishes.

**Tracking:** [Issue #14](https://github.com/thelonewander3r/PIIScanner/issues/14) · branch `feature/sprint7-pypi-prep` · runbook [`docs/RELEASE.md`](./docs/RELEASE.md)  
**Hard rule:** Do **not** push a `v*` tag or publish until Emanuel explicitly says go.

### Prep status (this sprint)

| Item | Status |
|---|---|
| `pyproject.toml` 0.1.0 metadata | Ready for review (authors, urls, classifiers, hatch targets, `[ner]` extra) |
| Trusted publisher checklist | Documented in README + `docs/RELEASE.md`; **blocked on Emanuel UI** (PyPI pending publisher + GitHub `pypi` env) |
| Local `uv build` dry-run | Done on prep branch; inspect sdist/wheel; do not commit `dist/` |
| CHANGELOG fold Unreleased → `[0.1.0]` | Prepped (date `TBD` until tag day; includes NER) |
| README install | PyPI primary **once published**; git/local fallback until then; does not claim published |
| `docs/RELEASE.md` runbook | Added |
| Tag / PyPI publish | **Not done** — wait for Emanuel go |

### In scope

1. **Version / metadata** — confirm `pyproject.toml` version `0.1.0` (or agreed), name `piilint`, classifiers, entry points, `project.urls`, optional `[ner]` extra documented
2. **Trusted publishing checklist** — document/verify GitHub `pypi` environment + PyPI trusted publisher for `thelonewander3r/PIIScanner` → `release.yml` OIDC job (**Emanuel-only** UI steps)
3. **Release dry-run** — `uv build` locally; sanity-check sdist/wheel contents (no secrets, corpus excluded from sdist); optional TestPyPI dry-run if Emanuel wants
4. **CHANGELOG** — fold Unreleased notes into `0.1.0` section (date on tag day)
5. **README** — install from PyPI as primary path once published; git/dev install until then
6. **Release PR** — version/changelog/README/runbook only; CI green; **tag is a separate, explicit step** after merge + Emanuel go
7. **Post-go runbook** — [`docs/RELEASE.md`](./docs/RELEASE.md): trusted publisher → wait for go → `git tag v0.1.0 && git push origin v0.1.0` → watch `release.yml` → verify `uvx`/`pipx`

### Out of scope

- Cutting the tag in this sprint without Emanuel’s go
- Marketplace listing / SEO deep dive
- New features
- Claiming the package is on PyPI before the tag succeeds

### Acceptance

- [x] Metadata reviewed/fixed on prep branch (`0.1.0`, urls, classifiers, entry point, `[ner]`, hatch sdist excludes)
- [x] Trusted publisher checklist confirmed in README + `docs/RELEASE.md`; **blocked on Emanuel UI** (PyPI pending publisher + GitHub `pypi` env)
- [x] Local `uv build` dry-run + artifact inspection (prep branch; `dist/` untracked / cleaned)
- [x] CHANGELOG folded for `[0.1.0]` (date TBD until tag day; includes NER)
- [x] README install wording (PyPI primary once published; git until then; does not claim published)
- [x] Written runbook [`docs/RELEASE.md`](./docs/RELEASE.md)
- [ ] Release prep PR merged; CI green; Lead Dev review
- [ ] Trusted publisher / `pypi` env completed in UI by Emanuel
- [ ] Tag/publish only after Emanuel’s explicit go — **not published yet**

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
