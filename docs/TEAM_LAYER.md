---
title: Team layer — design (Sprint 14)
status: design
updated: 2026-08-12
tracking: https://github.com/thelonewander3r/PIIScanner/issues/32
---

# Team layer — design (Sprint 14)

> **Design only.** No hosted API, DB, dashboard, billing, or production backend in this sprint.
> Free `piilint` stays complete and offline-forever. Any future sync is opt-in, metadata-only, and auditable.

**Windows-first:** paths, `pathlib`, UTF-8, and PowerShell-friendly CLI examples below. No compliance certification claims — piilint is a detection aid.

---

## 1. Problem / ICP

**Who:** Engineering and security teams that already run free `piilint` locally (pre-commit, CI, ad-hoc scans on Windows/Linux/macOS).

**What hurts today:**

- Every repo invents its own `piilint.toml`; org standards drift (`fail_on`, entity toggles, allowlists).
- Security/leads cannot answer "what is *new* this week across our repos?" without collecting raw scan dumps (which nobody should upload).
- Local `piilint baseline` works per-repo; there is no org view of "known accepted" vs "new" without sharing files by hand.

**Paid wedge (later build):** org-wide **shared policy** + **findings-metadata** history ("what's new"), still with the hard promise that **raw file contents never leave the machine**.

---

## 2. Non-goals

| Non-goal | Why |
|---|---|
| Cripple or paywall the free CLI | Business model is adoption → paid layer; free scan / `baseline` / `redact` stay complete |
| Upload notebooks, CSV, Parquet, source, or raw text | Core product promise; also a deal-breaker for ICP |
| Login-required-to-scan | Offline forever; auth only for optional team commands |
| Compliance certification (GDPR / HIPAA / PCI / etc.) | Detection aid only; never claim compliance |
| Building SaaS / billing / dashboard UI in this sprint | Design lock first; Emanuel picks slice before any build |
| Secrets scanning | Remains out of scope (pair with gitleaks) |
| Parallel finding model | Reuse `Finding`, `fingerprint_for`, baseline fingerprints, JSON `config_hash` |

---

## 3. Trust boundary

### Hard rule

**Local-first.** Scan, baseline, redact, and reporters work with **zero network** forever.

If a team later opts in to sync, the client may send **findings metadata only**. Never:

- raw matches or `normalized_value`
- `--show-matches` / unmasked values
- `masked_sample` (still derived from real PII; not needed for org "new vs known")
- file bytes, notebook cells, CSV rows, or path *strings* that are not hashed
- full local JSON/SARIF report dumps as-is (those include `path` + `masked_sample`)

### Align with existing code

| Existing piece | Role for team layer |
|---|---|
| `findings.value_hash` / `Finding.value_sha256` | **Value fingerprint** (SHA-256 of `normalize_value`) — already used |
| `findings.fingerprint_for` | Stable finding id: `SHA-256(path\|entity\|value_sha256\|occurrence_index)` — line-number independent (same tradeoff as local baseline) |
| `baseline.write_baseline` | Stores **fingerprints only** — org baselines should follow the same discipline |
| `reporters.json_.config_hash` | SHA-256 of canonical effective Config — proves which policy produced a run |
| JSON reporter schema_version 1 | Local/full report stays as today; **sync payload is a stricter subset** (below) |

### Sync metadata schema (proposed, schema_version TBD at build time)

Per finding (or per "new finding" event):

| Field | Source | Notes |
|---|---|---|
| `entity` | `Finding.entity` | e.g. `EMAIL`, `SSN_US` |
| `severity` | `Finding.severity` | after policy |
| `finding_fingerprint` | `Finding.fingerprint` | primary dedup key |
| `path_fingerprint` | `SHA-256(normalized relative path)` | **do not** sync raw `location.path` |
| `value_fingerprint` | `Finding.value_sha256` | already a hash; never raw/normalized value |
| `config_hash` | `config_hash(effective Config)` | same function as JSON reporter |
| `scanned_at` | client timestamp (UTC) | run time |
| `repo_id` | optional | opaque id from workspace binding (not a git remote URL unless user opts in) |
| `tool_version` | `__version__` | support / drift |
| `occurrence_index` | optional | already inside finding fingerprint; include only if needed for debug |

**Explicitly omitted from sync:** `path`, `line` / `row` / `column` / `cell`, `masked_sample`, `normalized_value`, `confidence` (optional later; not required for MVP "new this week"), file contents.

### Opt-in + auditability

- Sync commands are separate from `piilint .` / `scan` / `baseline` / `redact`.
- Default: no credentials, no endpoints contacted at scan time (unchanged; pytest-socket remains the guardrail for the core suite).
- When sync is used: print a one-line summary of **what** will be sent (counts by entity/severity, byte size, destination host) and require confirmation unless `--yes` in CI with an explicit env/flag.
- Local audit log (optional file under user config dir): timestamp, action (`policy pull` / `sync metadata`), counts, `config_hash`, destination — still no PII.

---

## 4. MVP slice order

**Recommendation: adopt Lead Dev starting order A → B → C.** No strong argument to reorder.

| Order | Slice | Why this order |
|---|---|---|
| **1 — A** | **Shared policy packs distribution** | Lowest trust risk: ships TOML/policy only, **no findings leave the machine**. Builds directly on `examples/policies/` (`strict-ci`, `data-eng`, `open-source-lib`). Clear "team" value (one org standard, `piilint policy pull`). |
| **2 — B** | **Metadata history / new-findings feed** | The "what's new this week" wedge. Needs the sync schema + opt-in client above. Depends on teams already sharing policy (`config_hash` meaningful across repos). |
| **3 — C** | **Org baselines** | Powerful, but overlaps local `piilint baseline` (fingerprints only). Do after A/B so policy identity + history exist; org baseline = shared fingerprint set keyed by workspace/repo, not a second fingerprint algorithm. |

**Later build sprint:** implement **one** slice (prefer A) only after Emanuel answers open questions / picks the slice. Do not start B/C until A is proven with real teams.

### Slice A — sketch (build-ready intent)

- Host or git-backed **policy pack registry** (versioned TOML + changelog).
- Client: `piilint policy pull [--pack NAME] [--version]` writes/updates local `piilint.toml` or a pinned include path (exact UX at build time; Windows path-safe).
- Packs start as curated evolution of `examples/policies/`; orgs can publish private packs in a later iteration.
- No findings upload. Offline scan still uses whatever local TOML is present.

### Slice B — sketch

- After a local scan, optional `piilint sync --metadata` (or `report --metadata-only` emitting the sync subset to stdout/file **without network**, plus a separate upload step).
- Server stores metadata rows; UI or CLI feed: "new `finding_fingerprint`s since T for workspace W".
- Diff semantics mirror local baseline subtract (`subtract_baseline`) but across time/repos using the **same** fingerprints.

### Slice C — sketch

- Org baseline artifact = versioned list of `finding_fingerprint`s (same as `baseline.py`), scoped to workspace ± repo_id.
- `piilint baseline pull` / `push` (names TBD) — still fingerprints only.
- Local `--baseline` continues to work offline with a file path; org pull is convenience, not a requirement to scan.

---

## 5. Auth / tenancy sketch (keep light)

**MVP preference:** bind a **workspace** to a **GitHub org** (or a single user) via device/OAuth login. Alternative: invite-code workspace with API token for CI.

| Concern | Sketch |
|---|---|
| Identity | `piilint login` → browser/device flow; store refresh token in OS user config dir (Windows: under `%LOCALAPPDATA%\piilint\` or equivalent) |
| Tenancy | Workspace = billing/policy boundary; repos bind by optional `repo_id` or GitHub `owner/name` if user opts in |
| CI | Fine-grained PAT or GitHub App installation token with **minimal** scopes (read org membership + write only team-layer API) — **Emanuel chooses App vs token** |
| Self-host | Same API shape; different base URL via env `PIILINT_TEAM_URL` / config — decide host vs self-host before build |

No SSO/SAML in first build. No "scan as service account uploads files."

---

## 6. CLI proposals only

Free offline forever. These commands are **proposals** for a later build — not implemented in Sprint 14.

```text
piilint login                      # opt-in auth; opens browser / device code
piilint logout

piilint policy list                # list packs available to workspace
piilint policy pull [PACK]         # fetch pack → local TOML (Slice A)
piilint policy status              # show local pack pin + config_hash

piilint report --metadata-only     # write sync-shaped JSON locally (no network)
piilint sync --metadata            # opt-in upload of metadata-only payload (Slice B)
piilint sync --dry-run             # show counts / destination; send nothing

piilint baseline pull|push         # org fingerprint set (Slice C; after A/B)
```

**Unchanged forever without login:**

```text
piilint .
piilint scan
piilint baseline .
piilint redact
piilint --format json|sarif
```

Scan-time network remains forbidden except existing explicit setup (`setup-ner`) and these opt-in team commands.

---

## 7. Privacy / retention

### Refuse to store (server and sync path)

- Raw or normalized match values
- Masked samples
- File contents / notebooks / exports
- Raw filesystem paths (use `path_fingerprint` only)
- `--show-matches` output
- Allowlist *values* that are themselves PII (policy packs should prefer domains/patterns; document the risk if orgs put real addresses in TOML — pack distribution is config, not findings)

### Retention sketch (product policy; not a legal opinion)

| Data | Sketch |
|---|---|
| Findings metadata | Rolling **90 days** default for "new this week" feed; configurable per workspace later |
| Aggregates (counts by entity/severity/week) | Longer (e.g. 13 months) for trend sparklines — still no paths/values |
| Org baselines (fingerprint sets) | Until deleted by admin; versioned |
| Policy packs | Version history retained; deletes are soft-delete + tombstone |
| Auth tokens | Standard short-lived access + rotatable refresh; revoke on logout |
| Audit of sync events | Align with metadata retention |

Deletion: workspace admin can purge metadata and baselines; client should support "forget this repo_id." Export for customer: metadata JSON only.

---

## 8. Open questions for Emanuel

1. **Which slice first for the first build sprint?** Design recommends **A (policy packs)** — confirm or override.
2. **Pricing:** per seat, per workspace, per active repo, or flat team tier? Free tier limits (e.g. one pack, no history)?
3. **Hosted vs self-host:** SaaS-only MVP, self-host image in v1, or SaaS first with self-host later?
4. **GitHub App vs fine-grained PAT** (and required scopes) for org binding + CI?
5. **Policy pack source of truth:** our registry, customer git repo, or both?
6. **Path fingerprint salt:** global salt vs per-workspace salt (workspace salt prevents cross-customer path correlation but breaks cross-workspace dedup — usually fine)?
7. **CI sync default:** off unless `PIILINT_SYNC=1` + token, or allow Action input later?
8. **Brand / product name** for the paid layer (keep `piilint` team vs separate SKU)?

**Gate:** next **build** sprint only after answers (at least 1–4) and an explicit slice pick.

---

## Architecture constraints (checklist)

- [x] Free CLI fully usable **offline forever**
- [x] Sync **opt-in** + auditable; never required to scan
- [x] Reuse `fingerprint_for` / `value_sha256` / baseline fingerprints / `config_hash` — **no parallel model**
- [x] No crippleware; no login-required-to-scan
- [x] No compliance certification language
- [x] Docs-only this sprint; optional local metadata-export spike **skipped** (nice-to-have; keep Local Tester docs-light / N/A)

---

## References

- Issue [#32](https://github.com/thelonewander3r/PIIScanner/issues/32)
- [`PROJECT.md`](../PROJECT.md) § Sprint 14
- [`BUILD_PLAN.md`](../BUILD_PLAN.md) — business model + post-MVP team layer note
- [`examples/policies/`](../examples/policies/) — starting packs for Slice A
- `src/piilint/findings.py` — `normalize_value`, `value_hash`, `fingerprint_for`
- `src/piilint/baseline.py` — fingerprints-only baseline
- `src/piilint/reporters/json_.py` — `config_hash` + schema_version 1
