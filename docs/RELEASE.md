# Release runbook (v0.1.0)

Maintainer steps for the **first** PyPI publish of `piilint`.  
**Hard stop:** do **not** cut a `v*` tag or publish until **Emanuel** gives an explicit go.

See also: [issue #14](https://github.com/thelonewander3r/PIIScanner/issues/14), [`PROJECT.md`](../PROJECT.md) Sprint 7, README trusted-publisher checklist.

---

## 0. Preconditions (prep PR)

- [ ] Prep PR merged to `main` (metadata, CHANGELOG fold, README install wording, this runbook).
- [ ] CI green on `main`.
- [ ] Local `uv build` previously succeeded; wheel entry point `piilint` present.
- [ ] Version is `0.1.0` in `pyproject.toml` and `src/piilint/__init__.py`.

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

## 2. Wait for Emanuel go

Product Owner / Lead Dev: **stop here** until Emanuel explicitly says to cut the tag.

Checklist before asking:

- [ ] Trusted publisher configured (or Emanuel acknowledges he will configure it before/at tag time).
- [ ] GitHub `pypi` environment exists.
- [ ] CHANGELOG `[0.1.0]` date set (or set in the same commit as the tag).
- [ ] No secrets or unexpected files in a fresh `uv build` inspect.

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

Update README if any “until published” git-fallback wording should be softened after a successful publish (separate small docs PR is fine).

---

## Out of scope / do not do

- No TestPyPI upload unless Emanuel asks.
- No long-lived PyPI tokens in GitHub secrets.
- No `v*` tag from prep branches without Emanuel go.
