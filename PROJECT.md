---
title: piilint — Project management
status: active
updated: 2026-08-11
owner: Product Owner
---

# piilint — Project management

**GitHub:** https://github.com/thelonewander3r/PIIScanner  
**Local:** `C:\Users\E_man\Documents\Projects\PIIScanner2`  
**Technical truth:** [`BUILD_PLAN.md`](./BUILD_PLAN.md) · **Release runbook:** [`docs/RELEASE.md`](./docs/RELEASE.md)

---

## Status

Phases **0–8** on `main`. Sprint 7 PyPI prep merged ([#15](https://github.com/thelonewander3r/PIIScanner/pull/15)). **No `v*` tag** until Emanuel go + trusted publisher.

**Next (Emanuel):** Sprint 8 in progress ([#16](https://github.com/thelonewander3r/PIIScanner/issues/16)), then publish when ready.  
**Also tracked:** business-value backlog (below) — prioritize after hardening / first publish unless Emanuel reorders.

---

## Sprint 8 — Release hardening (IN PROGRESS)

**Goal:** Prove the artifact strangers install — not only that `uv sync --extra dev` tests pass on a checkout.

**Tracking:** [Issue #16](https://github.com/thelonewander3r/PIIScanner/issues/16) · branch `feature/sprint8-release-hardening`  
**Still no production `v*` tag** without Emanuel go.

### In scope

1. **CI: package build** — job (or step) that runs `uv build` on at least ubuntu + windows; upload/artifacts optional; fail on build errors
2. **CI: install-from-wheel smoke** — create a clean venv, `pip install dist/*.whl` (no editable, no `--extra dev`), run `piilint --version`, scan `tests/corpus/text` (or a tiny fixture), assert exit 1 + masked output (no raw PII)
3. **Optional NER smoke (CI, marked/extra)** — one job with `piilint[ner]` + `setup-ner` + `--ner` on synthetic prose; allow skipping if too heavy, but document; must not break default matrix
4. **TestPyPI path (docs + optional dry-run)** — document trusted publisher for TestPyPI *or* a maintainer script; prefer a dry-run upload only with Emanuel go (separate from prod tag)
5. **Action / pre-commit smoke** — minimal workflow or documented manual check that composite `action.yml` runs on a sample path; pre-commit hook config snippet validated
6. **Docs** — short “How we know releases are good” section in `docs/RELEASE.md`; mark Sprint 8 done in PROJECT/BUILD_PLAN notes when AC met

### Out of scope

- Production `v0.1.0` tag (after this + Emanuel go)
- New detection features / NER quality campaigns
- Paid team layer

### Acceptance

- [ ] CI proves build + clean-install smoke on ≥2 OSes
- [ ] Default (no-ner) smoke is required green on PRs
- [ ] RELEASE.md updated with hardening + TestPyPI notes
- [ ] Lead Dev LGTM; PO merge; still stop before prod tag

---

## Business value — what we have vs what’s missing

### What already delivers value (developer / small team)

| Capability | Why it matters |
|---|---|
| Local-first scan, no upload | Trust barrier for real data samples |
| Notebook + tabular adapters | Catches the classic `df.head()` leak |
| Pre-commit + `--staged` + GHA + SARIF | Fits how eng teams already gate merges |
| Baseline | Adopt without boiling the ocean |
| Policy / allowlists / suppressions | Noise control so it doesn’t get turned off |
| Precision-first + CI benchmark gate | Credibility for a security-adjacent tool |
| Optional NER | Names/addresses when someone opts in |

### Gaps that block or weaken *business* value

Ordered by “unlocks paying / serious org adoption” vs nice-to-have:

1. **Public install + proven release path (now)** — PyPI + hardening + publisher. Without this, adoption stays “clone the repo.”
2. **`--redact` / clean-copy export** — BUILD_PLAN’s most-requested post-MVP; businesses need “fix the leak,” not only “find it.”
3. **Org policy packs** — shareable `piilint.toml` / allowlists / severity maps as versioned artifacts (even as a folder of examples before a SaaS).
4. **Findings-metadata history (team layer)** — trend “new PII introduced this week” without centralizing raw files; this is the paid wedge in BUILD_PLAN.
5. **More formats teams actually ship** — xlsx, PDF (and later docx); data/ops orgs live here.
6. **Locale coverage** — non-US national IDs, phone regions beyond US default; otherwise “works for US startups” only.
7. **Enterprise trust packaging** — signed releases/provenance, support channel, SOC2-friendly story (“we never see your data”), clear severity→ticket mapping examples for Jira/ServiceNow (docs/integrations, not necessarily product).
8. **IDE / PR review UX** — inline annotations or richer PR comments from SARIF; reduces “another CLI to remember.”
9. **Performance / scale story** — published numbers for large parquet/CSV; SLAs for CI minute cost.
10. **Sibling chassis (later)** — dataset diffing; don’t build until piilint is adopted.

### Recommended sequencing (PO view)

| When | What |
|---|---|
| **Now** | Sprint 8 release hardening → trusted publisher → `v0.1.0` on go |
| **Right after publish** | `--redact` MVP + example org policy packs (docs/examples) |
| **First paid wedge** | Team metadata history + shared policy (design before build) |
| **Parallel opportunistic** | xlsx/PDF adapters; locale packs |
| **Defer** | Full SaaS UI, speculative chassis reuse |

---

## How we work

1. Product Owner owns scope (this file)  
2. Lead Dev ↔ Developer via GitHub issues + DMs  
3. Developer on feature branch  
4. Lead Dev reviews  
5. Product Owner merges; next package / hold for Emanuel go on tags  
