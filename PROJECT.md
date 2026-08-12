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

`piilint` **0.1.0** is on PyPI. Phases 0–8 + release hardening done. Post-release docs done (#18/#19).

**Next (Emanuel 2026-08-12):** Sprint 9 — `--redact` + example org policy packs.

---

## Sprint 9 — Redact + example policy packs (NEXT)

**Goal:** (1) Let users write cleaned copies of files with PII masked/replaced, not only detect. (2) Ship shareable example `piilint.toml` policy packs teams can copy.

**Tracking:** issue to be opened by Lead Dev from this scope call  
**Branch:** off `main` → PR → LGTM → PO merge (no direct-to-main)  
**Version:** land on `main` as post-0.1.0 work; **do not** cut `v0.2.0` unless Emanuel explicitly goes.

### A. `--redact` (primary)

1. **CLI:** something like `piilint redact PATH -o OUT_DIR` (exact UX Lead Dev / Developer can refine; must be documented). Prefer **write copies** into an output directory — **never overwrite sources by default**. Optional `--in-place` only with an explicit scary flag if included at all (default off; PO preference: skip in-place for v1 of redact).
2. **Behavior:** for supported adapters (start with **text + json/jsonl + csv/tsv**; notebooks/parquet if straightforward in same sprint, else follow-up). Replace matched spans with the same masking style as findings (or stable placeholders like `[EMAIL]` / last-4 cards) so output is useful and deterministic.
3. **Deps:** prefer staying lean. If `presidio-anonymizer` is needed, put it behind an optional extra (e.g. `piilint[redact]`) — don’t bloat the base wheel. Deterministic recognizers can redact without Presidio; NER redact may require the ner/redact extra — document clearly.
4. **Safety:** no raw PII in logs/errors; refuse `--show-matches`-style unmask when writing; Windows path-safe; exit codes consistent (2 on usage/config).
5. **Tests:** unit tests for rewrite correctness on synthetic fixtures; assert output contains no raw corpus PII; round-trip scan of redacted output finds fewer/no findings for those entities.
6. **Docs:** README section + examples; update BUILD_PLAN post-MVP note to “in progress/done.”

### B. Example org policy packs (same sprint)

1. **Layout:** e.g. `examples/policies/` with a short README explaining copy-to-repo-root as `piilint.toml` (or include path docs).
2. **Packs (at least 3):** 
   - `strict-ci.toml` — fail on medium+, IP off, tight min_confidence
   - `data-eng.toml` — tabular-friendly excludes for fixtures, allowlist example.com-style already handled by downweight; document baseline pairing
   - `open-source-lib.toml` — noisier codebases: IP off, higher min_confidence, sample allowlist domains
3. **Hard rule:** no pack may claim GDPR/HIPAA/PCI compliance. Disclaimer in the policies README.
4. **Wire from main README** — one paragraph + links.

### Out of scope (Sprint 9)

- Paid team layer / metadata history SaaS
- New file formats (xlsx/PDF)
- Cutting a PyPI release tag (ask Emanuel after merge if we should ship 0.2.0)
- In-place overwrite as the default path

### Acceptance

- [ ] `redact` command writes cleaned copies to `-o` dir; sources untouched by default
- [ ] Tests prove masking and no raw PII in outputs
- [ ] Optional extra decision documented (base vs `[redact]`)
- [ ] ≥3 example policy packs + policies README + main README links
- [ ] pytest / ruff / mypy / package-smoke still green
- [ ] Lead Dev LGTM; PO merge

### Roles

- **Developer:** implement on feature branch; report AC
- **Lead Developer:** open issue, architecture (redact design + extra), review
- **Product Owner:** this scope; merge; ask Emanuel about 0.2.0 tag after

---

## Later backlog (unchanged)

Team metadata history (paid wedge), xlsx/PDF, locales, IDE/PR UX, signed releases narrative.
