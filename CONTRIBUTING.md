# Contributing to piilint

Thanks for helping. Windows is a **first-class** target (the maintainer develops on Windows 11); use `pathlib`, UTF-8 text I/O, and keep the CI matrix green.

## Setup

Requires Python 3.10+ and [uv](https://github.com/astral-sh/uv).

```bash
git clone https://github.com/thelonewander3r/PIIScanner.git
cd PIIScanner
uv sync --extra dev
uv run piilint --version
```

## Checks (same as CI)

```bash
uv run pytest -q
uv run ruff check src tests
uv run ruff format --check src tests
uv run mypy
```

## Pull requests

- Branch off `main`; open a PR back into `main`.
- Use [Conventional Commits](https://www.conventionalcommits.org/) (`feat:`, `fix:`, `docs:`, `test:`, `ci:`, `chore:`, …).
- Keep changes small and typed; add/adjust tests in the same PR as the code they cover.
- Do **not** paste real PII into issues, PRs, fixtures, or logs. Use synthetic data only (see `tests/corpus/`).
- Do not cut `v*` tags or publish to PyPI unless the maintainer explicitly asks.

## Project docs

- [`BUILD_PLAN.md`](./BUILD_PLAN.md) — phases, architecture, acceptance criteria
- [`PROJECT.md`](./PROJECT.md) — scope board and sprint status
- [`SECURITY.md`](./SECURITY.md) — private vulnerability reporting

## Scope reminders

- No scan-time network calls.
- Redaction by default: masked samples only in outputs and tests.
- Not a secrets scanner — recommend pairing with gitleaks/trufflehog in docs, not reimplementing secrets detection here.
- Optional NER (`piilint[ner]`) is Phase 7 / post-launch; do not land it unless a sprint explicitly scopes it.
