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

`piilint` **0.1.0** is on PyPI. Sprints 9–14 on `main`. **Sprint 15 IN PROGRESS** — Slice B local metadata history MVP (no network), tracking [#37](https://github.com/thelonewander3r/PIIScanner/issues/37).

**Hold:** no `v0.2.0` / prod `v*` tags without Emanuel’s explicit go.  
**Verify:** Local Tester (Windows) full local gate; **not** GitHub Actions.


## Sprint 15 — Slice B local metadata history (IN PROGRESS)

**Tracking:** [#37](https://github.com/thelonewander3r/PIIScanner/issues/37) · branch `feature/sprint15-metadata-history`

### Scope

- Local SQLite history (`%LOCALAPPDATA%\piilint\history.sqlite3` on Windows; XDG on Unix)
- `piilint report --metadata-only` (emit + auto-record; no network)
- `piilint history --since`
- `piilint sync --metadata --dry-run` (counts / bytes / `<not configured>`; send nothing)
- Tests enforce forbidden metadata fields; default scan does not write history

### Verify

Local Tester (Windows) — full `uv sync --extra dev` + ruff / mypy / pytest / `piilint --version`. **Not GHA.**

## Sprint 14 — Team layer design (DONE)

**Merged:** [PR #35](https://github.com/thelonewander3r/PIIScanner/pull/35) · closes [#32](https://github.com/thelonewander3r/PIIScanner/issues/32)

### Shipped

- [`docs/TEAM_LAYER.md`](./docs/TEAM_LAYER.md) — ICP, trust boundary (metadata only), MVP slice order **A→B→C** (shared policy → metadata history → org baselines), CLI proposals, privacy notes, open questions
- Free CLI stays complete / offline forever by design
- Optional metadata-export spike skipped (docs-only)

### Follow-on

Slice pick: **B first** (see Sprint 15 / [#37](https://github.com/thelonewander3r/PIIScanner/issues/37)). Remaining TEAM_LAYER §8 host/auth/pricing Qs still open before real sync.

---

## Recent done

- Sprint 13 — docx — [#30](https://github.com/thelonewander3r/PIIScanner/pull/30)
- Sprint 12 — locales — [#27](https://github.com/thelonewander3r/PIIScanner/pull/27)
- Sprint 11 — xlsx/PDF — [#25](https://github.com/thelonewander3r/PIIScanner/pull/25)

---

## Later backlog

Implement team layer after Emanuel go; IDE/PR UX; signed releases narrative; PDF redact; more locales.
