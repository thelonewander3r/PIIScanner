# Phase 3 brief — Policy & noise (for Developer)

**Repo:** `C:\Users\E_man\Documents\Projects\PIIScanner2`  
**Package:** `piilint`  
**Branch:** `feature/phase2-adapters` (local only — no remote, **do not commit unless Emanuel asks**)  
**Source of truth:** `BUILD_PLAN.md` (Policy and noise control + Phase 3)  
**Assigned by:** Lead Developer (via Product Owner priority)  
**Out of scope:** Phase 4+ (baseline, staged mode, JSON/SARIF reporters, distribution, NER)

---

## Goal

Make findings controllable and quiet enough for real repos: config file + precedence, path/value suppressions, allowlists, test-data downweighting, and finalized fail-on / exit codes. Precision over recall. Nothing leaves the machine.

## Non-negotiables

1. **No scan-time network** — pytest-socket stays on; do not add network calls in scan path.
2. **Masked output only** — never print/log raw matched PII (existing masking in `findings.py`).
3. **Architecture boundary** — `adapters/`, `findings.py`, and `reporters/` must **not** import recognizer logic. Put policy in a new layer (`config.py` + `policy.py` or similar). Engine may call policy; adapters stay dumb.
4. **Windows-first** — `pathlib`, UTF-8 `errors="replace"`, CRLF/BOM-safe text reads.
5. **No new deps** without asking Lead Dev / Emanuel. Stick to locked list (`typer`, `rich`, `phonenumbers`, `pathspec`, `pyyaml`, `pyarrow`, `nbformat`). stdlib `tomllib` is fine for TOML.
6. **Do not start Phase 4** (baseline CLI, `--staged`).
7. Update `BUILD_PLAN.md` Phase 3 status when done (same session as the code).

---

## Already in place (do not re-invent)

| Piece | Status | Where |
|---|---|---|
| `.piiignore` + `.gitignore` via pathspec | **Partial — already loads** | `walker.py` `_load_ignore_spec` |
| `--fail-on` + exit 0/1/2 | **Partial — CLI only, no config file** | `cli.py` |
| `--min-confidence` | Present (default 0.6) | `cli.py` → `engine.scan_path` |
| `--enable-ip` | Present | `cli.py` |
| Walker `include` / `exclude` kwargs | Present, not wired from config | `walker.iter_files` |
| Masking + fingerprints | Done | `findings.py` |

Gaps to close: real config loading, entity toggles/severity overrides, allowlists, inline suppressions, test-data downweighting, wiring config exclude into walker, tests + docs for the above.

---

## Ordered work items

### 1. `src/piilint/config.py` — load + merge

- Add a typed config model (dataclass or similar) covering at least:
  - `scan.fail_on`, `scan.min_confidence`, `scan.exclude` (list of globs)
  - `entities.<name>` bool enable/disable (map to `EntityType`; default IP off)
  - `entities.<name>.severity` overrides
  - `allowlist.values`, `allowlist.domains`
- Load order / precedence (**highest wins**):
  1. CLI flags
  2. `piilint.toml` at scan root (or cwd — document choice; prefer **scan root** when scanning a dir)
  3. `[tool.piilint]` in `pyproject.toml`
  4. Built-in defaults
- Invalid config → **exit 2** with a clear message (not exit 1).
- Example shape is in BUILD_PLAN § Policy (copy into a sample `piilint.toml` in repo root or `docs/` only if useful; optional).

### 2. `src/piilint/policy.py` — post-match / pre-report filters

Keep this free of adapter/recognizer imports beyond `Finding` / `EntityType` / `Severity`.

Implement:

**A. Allowlists**
- Exact (normalized) value match against `allowlist.values`
- Email domain match against `allowlist.domains` (case-insensitive host)
- Drop matching findings entirely

**B. Test-data downweighting** (from BUILD_PLAN detection spec)
- Domains: `example.com` / `example.org` / `example.net`, `test.*`, `localhost`
- Phones: `555-01xx` pattern
- Classic fake card: `4111 1111 1111 1111` (and normalized form)
- RFC-5737 IPs if IP enabled
- Apply **−0.4 confidence** and **severity cap at low**; then re-apply `min_confidence` drop

**C. Inline suppressions** (text/code units only)
- Trailing `# piilint: ignore` → suppress all entities on that line
- `# piilint: ignore[EMAIL]` or comma-list → suppress those entities only
- Apply using unit line text / location; do not require adapters to know about policy beyond exposing source line text (text adapter already line-based)
- Tabular/column-aggregated findings: skip inline suppressions for v0 of Phase 3 (document that)

**D. Entity enable + severity overrides**
- Disabled entities never emit
- Severity map from config overrides `DEFAULT_SEVERITY`

### 3. Wire into engine + CLI

- `scan_path` / CLI accept a resolved `Config` (or kwargs built from it)
- Pass `exclude` globs into `walker.iter_files`
- Run policy **after** recognizers produce findings (and after column aggregation), **before** reporter
- Keep deterministic sort: path, then line/row, then entity
- Finalize exit codes (already mostly correct):
  - `0` — no findings at/above fail-on
  - `1` — findings at/above fail-on
  - `2` — usage/config/path errors; unexpected exceptions must stay **2**, never **1**

### 4. `.piiignore` verification

- Walker already reads it — add **unit tests** proving `.piiignore` excludes paths that `.gitignore` alone would not, and that CLI/`scan.exclude` also works
- If root resolution is wrong when scanning a single file, fix carefully with pathlib

### 5. Tests (same phase as code)

Add under `tests/unit/` (suggested names — adjust to fit existing style):

- `test_config.py` — precedence matrix (CLI > piilint.toml > pyproject > defaults); bad TOML → exit 2
- `test_policy.py` — allowlist value/domain; test-data downweight; entity disable; severity override
- `test_suppressions.py` — `# piilint: ignore` and `# piilint: ignore[EMAIL]`
- Extend walker tests for `.piiignore` + config exclude
- Existing benchmark gate must still pass — **do not lower thresholds**. If test-data downweight changes corpus expectations, update `corpus.yaml` only with justification and keep precision/recall gates green
- Masking regression: no raw corpus PII in any output

### 6. Docs / plan hygiene

- README: short note on `piilint.toml`, `.piiignore`, inline ignore, allowlists
- Mark Phase 3 **DONE** in `BUILD_PLAN.md` with date + real AC notes (what was verified)
- Conventional commits only if Emanuel asks you to commit

---

## Acceptance checklist (Phase 3 done when)

- [ ] Config loads with documented precedence; CLI wins
- [ ] `piilint.toml` and `[tool.piilint]` both work
- [ ] `.piiignore` tested
- [ ] Inline `# piilint: ignore` / `# piilint: ignore[ENTITY]` work on text/code lines
- [ ] Allowlist values + domains drop findings
- [ ] Test-data downweight applied (−0.4, severity ≤ low) then min_confidence
- [ ] `--fail-on` + exit codes 0/1/2 correct; config errors → 2
- [ ] `uv run pytest` green; benchmark gates still hold with **real** printed numbers
- [ ] ruff + mypy strict on `src/` clean
- [ ] No recognizer imports in adapters / findings / reporters
- [ ] `BUILD_PLAN.md` Phase 3 marked done

---

## Suggested file touch list

```
src/piilint/config.py          (new)
src/piilint/policy.py          (new)
src/piilint/cli.py             (load config, pass through)
src/piilint/engine.py          (apply policy; entity enable)
src/piilint/walker.py          (only if .piiignore/exclude gaps)
src/piilint/findings.py        (only if severity helper needed — keep chassis-clean)
tests/unit/test_config.py      (new)
tests/unit/test_policy.py      (new)
tests/unit/test_suppressions.py (new)
tests/unit/test_core.py / test_adapters.py (extend as needed)
README.md
BUILD_PLAN.md
piilint.toml                   (optional example)
```

---

## Report back when finished

1. What you implemented (file list)
2. AC checklist with pass/fail evidence
3. Real `pytest` + benchmark numbers (no fabrication)
4. Any BUILD_PLAN ambiguities you resolved (and how)
5. Blockers for Phase 4

Questions → Lead Developer. Product scope questions → Product Owner.
