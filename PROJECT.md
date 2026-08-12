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

`piilint` **0.1.0** is on PyPI. Sprints 9–13 on `main` (redact, policy packs, office, locales).

**Next (Emanuel 2026-08-12):** Sprint 14 — **team / findings-metadata layer design** (the paid wedge — design only).  
**Hold:** no `v0.2.0` / prod `v*` tags without Emanuel’s explicit go.  
**Verify:** Local Tester (Windows); not GitHub Actions.

---

## Sprint 14 — Team layer design (NEXT)

**Goal:** Lock a buildable design for the paid wedge **without** building SaaS yet: shared org policy + findings-**metadata** history, with the hard promise that **raw file contents never leave the machine**.

**Source:** BUILD_PLAN business model + “Team layer” post-MVP notes.  
**Tracking:** issue to be opened by Lead Dev from this scope call  
**Branch:** off `main` → PR → Local Tester (docs-light) + Lead LGTM → PO merge  
**Version:** docs only on `main`; **no tag**; **no production backend**.

### In scope (design deliverables)

1. **`docs/TEAM_LAYER.md`** (or similar) covering:
   - **Problem / ICP:** eng + security teams that already use free `piilint` and need org-wide policy + “what’s new this week”
   - **Non-goals:** crippling the free CLI; uploading notebooks/CSV/raw text; compliance certification
   - **Trust boundary:** client stays local-first; only **findings metadata** may sync (entity, severity, path fingerprint, config_hash, timestamps, optional repo id) — never raw matches / never `--show-matches` values
   - **MVP product slices (pick 1–2 for a later build sprint):** (A) shared policy packs distribution, (B) metadata history / “new findings” feed, (C) org baselines — recommend order
   - **Auth / tenancy sketch:** GitHub org or simple workspace; no over-spec
   - **CLI touchpoints:** e.g. `piilint login`, `piilint policy pull`, `piilint report --metadata-only` — proposals only
   - **Open questions** for Emanuel (pricing, host vs self-host, GitHub App vs token)
2. **Threat / privacy notes** — what we refuse to store; retention sketch
3. **PROJECT.md / BUILD_PLAN** — link the design; mark “design in progress / done”
4. **Optional spike (only if Lead Dev wants):** a **local** JSON “metadata export” CLI flag that proves the schema (still no network) — nice-to-have, not required

### Out of scope

- Building hosted API, DB, dashboard UI, billing
- Changing free CLI to require accounts
- PDF redact, more locales, IDE UX (backlog)
- Cutting a PyPI tag

### Acceptance

- [ ] Design doc merged on `main` with clear MVP slice recommendation + trust boundary
- [ ] Free CLI remains complete / unc crippled by design
- [ ] Open questions listed for Emanuel
- [ ] Lead Dev LGTM; Local Tester docs-light OK (or N/A if docs-only); PO merge

### Roles

- **Developer:** draft design doc (+ optional metadata-export spike)
- **Lead Developer:** open issue; architecture review; recommend MVP slice order
- **Product Owner:** this scope; merge; next build sprint only after Emanuel picks slice / answers open Qs

---

## Recent done

- Sprint 13 — docx — [#30](https://github.com/thelonewander3r/PIIScanner/pull/30)
- Sprint 12 — locales — [#27](https://github.com/thelonewander3r/PIIScanner/pull/27)
- Sprint 11 — xlsx/PDF — [#25](https://github.com/thelonewander3r/PIIScanner/pull/25)

---

## Later backlog

IDE/PR UX; signed releases narrative; PDF redact; more locales; implement team layer **after** this design + Emanuel go on slice.
