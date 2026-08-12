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

All BUILD_PLAN phases **0–8** are on `main` (including optional NER). **Sprint 7 prep** merged via [#15](https://github.com/thelonewander3r/PIIScanner/pull/15). **Sprint 8** (release hardening) is in progress on `feature/sprint8-release-hardening` — [issue #16](https://github.com/thelonewander3r/PIIScanner/issues/16). Package is **not published**; no `v*` tag without Emanuel’s explicit go.

| Area | Status |
|---|---|
| Phases 0–6, 8 | Done |
| Phase 7 NER | Done — [#12](https://github.com/thelonewander3r/PIIScanner/issues/12) / [#13](https://github.com/thelonewander3r/PIIScanner/pull/13) |
| Sprint 7 PyPI prep | **Done (prep)** — [#14](https://github.com/thelonewander3r/PIIScanner/issues/14) / [#15](https://github.com/thelonewander3r/PIIScanner/pull/15); **not published** |
| Sprint 8 release hardening | **In progress** — [#16](https://github.com/thelonewander3r/PIIScanner/issues/16); branch `feature/sprint8-release-hardening` |
| First PyPI / `v0.1.0` | **Blocked on Emanuel go** after hardening + UI publisher; no tag yet |

---

## Sprint 8 — Release hardening (IN PROGRESS)

**Goal:** Prove strangers can install a built `piilint` artifact — not only that `uv sync --extra dev` tests pass on a checkout — before any production `v*` tag.

**Tracking:** [Issue #16](https://github.com/thelonewander3r/PIIScanner/issues/16) · branch `feature/sprint8-release-hardening` · runbook [`docs/RELEASE.md`](./docs/RELEASE.md)  
**Hard rule:** Do **not** push a production `v*` tag or upload to prod PyPI. TestPyPI dry-run upload only with Emanuel go.

### In scope

1. **CI package build + install-from-wheel smoke** — `package-smoke` on ubuntu + windows: `uv build` → clean venv → install wheel → `piilint --version` → scan corpus with expected exit 1 + masked output
2. **Optional NER smoke** — separate `ner-smoke` job (ubuntu); must not break default matrix
3. **TestPyPI docs** — trusted-publisher dry-run path in `docs/RELEASE.md` (no upload without go)
4. **Action / pre-commit smoke** — CI `action-smoke` (`uses: ./`, YAML parse)
5. **Docs** — “How we know releases are good”; status here + BUILD_PLAN

### Out of scope

- Production `v0.1.0` tag / prod PyPI upload
- New detection features / NER quality campaigns
- Paid team layer / business backlog items unless explicitly pulled forward

### Acceptance

- [x] CI YAML proves `uv build` + clean-install smoke on ≥2 OSes (`package-smoke`)
- [x] Default (no-ner) smoke is a **required** separate job (not `continue-on-error`)
- [x] `docs/RELEASE.md` updated (hardening + TestPyPI notes + “How we know releases are good”)
- [x] Local `uv run pytest` green (verified on hardening branch)
- [ ] Lead Dev LGTM; PO merge; still stop before prod tag
- [ ] Remote CI green on PR (pending push)

### Roles

- **Developer:** implement on `feature/sprint8-release-hardening`; open PR; comment on #16
- **Lead Developer:** review
- **Product Owner:** merge; hold tag until Emanuel go
- **Emanuel:** TestPyPI dry-run go (if wanted); prod tag go after hardening

---

## Sprint 7 — First PyPI release prep (DONE — prep merged)

**Goal:** Make `piilint` installable via PyPI (`pipx`/`uvx`/`pip`) with a clean 0.1.0 release, without surprising publishes.

**Tracking:** [Issue #14](https://github.com/thelonewander3r/PIIScanner/issues/14) · PR [#15](https://github.com/thelonewander3r/PIIScanner/pull/15) merged · runbook [`docs/RELEASE.md`](./docs/RELEASE.md)  
**Hard rule:** Do **not** push a `v*` tag or publish until Emanuel explicitly says go.

### Prep status

| Item | Status |
|---|---|
| `pyproject.toml` 0.1.0 metadata | Done (merged #15) |
| Trusted publisher checklist | Documented in README + `docs/RELEASE.md`; **blocked on Emanuel UI** |
| Local `uv build` dry-run | Done on prep branch |
| CHANGELOG fold Unreleased → `[0.1.0]` | Done (date `TBD` until tag day) |
| README install | PyPI primary **once published**; git/local fallback until then |
| `docs/RELEASE.md` runbook | Added (extended in Sprint 8) |
| Tag / PyPI publish | **Not done** — wait for hardening + Emanuel go |

### Acceptance

- [x] Metadata reviewed/fixed (`0.1.0`, urls, classifiers, entry point, `[ner]`, hatch sdist excludes)
- [x] Trusted publisher checklist in README + `docs/RELEASE.md`; **blocked on Emanuel UI**
- [x] Local `uv build` dry-run + artifact inspection
- [x] CHANGELOG folded for `[0.1.0]` (date TBD; includes NER)
- [x] README install wording
- [x] Written runbook [`docs/RELEASE.md`](./docs/RELEASE.md)
- [x] Release prep PR merged (#15); CI green path for prep
- [ ] Trusted publisher / `pypi` env completed in UI by Emanuel
- [ ] Tag/publish only after Emanuel’s explicit go — **not published yet**

---

## How we work

1. Product Owner owns scope  
2. Lead Dev ↔ Developer via issues + DMs  
3. Developer on feature branch  
4. Lead Dev reviews  
5. Product Owner merges, then next package (here: wait for go to tag)
