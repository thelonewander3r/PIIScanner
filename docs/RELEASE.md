# Release runbook

Maintainer steps for PyPI publishes of `piilint`.

**First publish (done):** `v0.1.0` → [PyPI `piilint`](https://pypi.org/p/piilint) on **2026-08-12** via OIDC (`release.yml`).  
**Hard stop for future tags:** do **not** cut a new `v*` tag or publish until **Emanuel** gives an explicit go.

See also: [issue #14](https://github.com/thelonewander3r/PIIScanner/issues/14), [issue #16](https://github.com/thelonewander3r/PIIScanner/issues/16) (Sprint 8 hardening, closed), [`PROJECT.md`](../PROJECT.md), README trusted-publisher checklist.

---

## How we know releases are good

Before any production `v*` tag, CI and local checks must prove that a **built artifact** (not only an editable checkout) works:

| Gate | Where | What it proves |
|---|---|---|
| Default matrix `test` | `.github/workflows/ci.yml` | ruff / mypy / pytest+benchmark / `piilint --version` on ubuntu + windows + macos × Python 3.10 + 3.13 |
| `package-smoke` (**required**) | same workflow | `uv build` → clean venv → `uv pip install --python .smoke-venv` **wheel only** (no editable, no `--extra dev`) on **ubuntu + windows** → `piilint --version` → scan `tests/corpus/text` with `--fail-on low` → **exit 1** + **no raw corpus PII** in stdout/stderr |
| `action-smoke` | same workflow | `action.yml` + `.pre-commit-hooks.yaml` parse; composite action `uses: ./` on `tests/corpus/text` with `fail-on: never` |
| `ner-smoke` (separate) | same workflow (ubuntu) | optional `uv sync --extra ner` → `piilint setup-ner` → `--ner` scan of synthetic prose; must **not** break default matrix |
| Local | maintainer machine | `uv run pytest -q` still green on the release commit |

**Hard stop:** no production `v*` tag and no prod PyPI upload without Emanuel’s explicit go. TestPyPI dry-run only with Emanuel go (see below).

---

## 0. Preconditions (prep PR)

For **`v0.1.0` (done 2026-08-12)** these were met. Re-check the list before any **future** tag:

- [x] Prep PR merged to `main` (metadata, CHANGELOG fold, README install wording, this runbook).
- [x] CI green on `main` (including **package-smoke** on ubuntu + windows).
- [x] Local `uv build` previously succeeded; wheel entry point `piilint` present.
- [x] Version is `0.1.0` in `pyproject.toml` and `src/piilint/__init__.py` *(bump for next release)*.
- [x] Sprint 8 release-hardening AC met ([issue #16](https://github.com/thelonewander3r/PIIScanner/issues/16)).

---

## 1. Trusted publisher + GitHub environment

These clicks require PyPI + GitHub org/repo admin access.

### Emanuel-only — PyPI UI

1. Sign in at [https://pypi.org](https://pypi.org) (account that will own `piilint`).
2. Prefer a **pending publisher** (creates the project on first upload):
   - Publishing → Trusted publishers → Add a new publisher → GitHub
   - **PyPI project name:** `piilint`
   - **Owner:** `thelonewander3r`
   - **Repository:** `PIIScanner`
   - **Workflow name:** `release.yml` (filename only, not path)
   - **Environment name:** `pypi`
3. If the project already exists, add the same trusted publisher under that project’s Publishing settings.
4. **Do not** create or store a long-lived PyPI API token for this flow.

### Emanuel-only — GitHub UI

1. Repo **Settings → Environments → New environment** named exactly `pypi` (matches `release.yml`).
2. Recommended: require reviewers (Emanuel) and/or wait timer before the publish job can run.
3. Confirm Actions can use the environment (no unexpected deployment branch restrictions that would block tags).

### Anyone — verify docs match workflow

Confirm [`.github/workflows/release.yml`](../.github/workflows/release.yml):

- Triggers on `push` tags `v*` (and `release` published).
- `publish` job: `environment: name: pypi`, `permissions.id-token: write`.
- Uses `pypa/gh-action-pypi-publish@release/v1` (OIDC; no password/token input).

---

## 1b. TestPyPI trusted publisher (dry-run path)

Optional rehearsal **before** the production tag. **Do not upload** unless Emanuel explicitly says go.

### Why

TestPyPI lets maintainers prove OIDC trusted publishing end-to-end without publishing `0.1.0` to production PyPI.

### Emanuel-only — TestPyPI UI

1. Sign in at [https://test.pypi.org](https://test.pypi.org) (often the same account as prod, but a separate index).
2. Add a **pending publisher** (or project publisher) for GitHub:
   - **Project name:** `piilint` (TestPyPI namespace is independent of prod)
   - **Owner:** `thelonewander3r`
   - **Repository:** `PIIScanner`
   - **Workflow name:** choose a **dedicated** workflow filename if/when added (e.g. `release-testpypi.yml`) — do **not** point TestPyPI at production `release.yml` without a separate job/environment
   - **Environment name:** e.g. `testpypi` (create matching GitHub Environment)
3. Prefer a separate workflow/job that sets:

   ```yaml
   environment: testpypi
   permissions:
     id-token: write
   steps:
     - uses: pypa/gh-action-pypi-publish@release/v1
       with:
         repository-url: https://test.pypi.org/legacy/
   ```

4. Trigger only via `workflow_dispatch` or an explicit non-`v*` dry-run tag agreed with Emanuel — **never** as a side effect of the production `v*` tag job.

### Dry-run upload policy

- **Default:** document only; **no upload**.
- **Upload:** only with Emanuel’s explicit go for that dry-run.
- After a TestPyPI upload (if any), verify install from TestPyPI:

  ```bash
  pip install -i https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ piilint==0.1.0
  piilint --version
  ```

  (`--extra-index-url` may be needed for dependencies that exist only on prod PyPI.)

- TestPyPI success does **not** authorize a production `v*` tag; prod still needs a separate Emanuel go.

---

## 2. Wait for Emanuel go

Product Owner / Lead Dev: **stop here** until Emanuel explicitly says to cut the **next** tag.

**`v0.1.0`:** go received; tagged and published 2026-08-12.

Checklist before asking for a **future** release:

- [x] Trusted publisher configured *(done for `v0.1.0`; confirm still valid)*.
- [x] GitHub `pypi` environment exists.
- [ ] CHANGELOG date set for the new version (or set in the same commit as the tag).
- [ ] No secrets or unexpected files in a fresh `uv build` inspect.
- [ ] `package-smoke` green on ubuntu + windows for the release commit.

---

## 3. Cut the tag (only after go)

From an up-to-date `main` (or the agreed release commit):

```bash
# Optional: set CHANGELOG date to today, commit, merge — then:
git tag v0.1.0
git push origin v0.1.0
```

Do **not** use a lightweight mistaken tag name; the workflow matches `v*`.

---

## 4. Watch release.yml

1. Open Actions → **Release** workflow for the `v0.1.0` tag.
2. Confirm **Build distributions** succeeds.
3. Confirm **Publish to PyPI (OIDC)** runs in the `pypi` environment (approve if protection rules require it).
4. On failure: read job logs; common first-publish issues are wrong workflow filename, wrong environment name, or missing trusted publisher — fix UI config and re-tag only if needed (never force-push tags without explicit agreement).

PyPI project URL (after success): https://pypi.org/p/piilint

---

## 5. Verify install

```bash
uvx piilint --version
# expect: 0.1.0 (or equivalent)

pipx install piilint
piilint --version

pip install piilint
python -c "import piilint; print(piilint.__version__)"
```

Optional NER path (not required for base release verification):

```bash
pip install "piilint[ner]"
piilint setup-ner
```

After each successful publish, confirm README primary install still points at PyPI and CHANGELOG dates match the tag day.

---

## 6. Action / pre-commit manual check (if CI skipped)

CI `action-smoke` covers this on PRs. Manual fallback:

```bash
# YAML still parse
python -c "import yaml; yaml.safe_load(open('action.yml')); yaml.safe_load(open('.pre-commit-hooks.yaml'))"

# Composite action: use a throwaway workflow or act; or from a PR that runs action-smoke.
# Pre-commit hook snippet (consumer repo):
#   - repo: https://github.com/thelonewander3r/PIIScanner
#     rev: v0.1.0   # after tag
#     hooks:
#       - id: piilint
```

Local staged-hook smoke (optional, from a clone with a staged text file):

```bash
pre-commit try-repo . piilint --verbose --all-files
```

---

## Out of scope / do not do

- No TestPyPI upload unless Emanuel asks (see §1b).
- No long-lived PyPI tokens in GitHub secrets.
- No `v*` tag from prep branches without Emanuel go.
- First prod upload (`v0.1.0`) completed 2026-08-12; no further prod upload without a new Emanuel go.
