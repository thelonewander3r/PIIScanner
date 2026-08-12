# Security Policy

## Supported versions

`piilint` is pre-1.0. Security fixes target the latest code on `main` (and the newest release tag once one exists).

## Reporting a vulnerability

**Prefer [GitHub Security Advisories](https://github.com/thelonewander3r/PIIScanner/security/advisories/new)** for anything that could be sensitive (RCE, supply-chain, unexpected data exposure, etc.). That keeps the report private until a fix is ready.

For **non-sensitive** bugs (wrong severity, false positives/negatives on synthetic data, docs typos), open a normal [GitHub issue](https://github.com/thelonewander3r/PIIScanner/issues).

There is **no bug bounty** program.

## Never paste real PII

Do not attach real personal data, production dumps, or unredacted scan output to issues, advisories, or PRs. Reproduce with **synthetic** fixtures (see `tests/corpus/`) or fully masked samples.

## Product expectations

- Scan-time network is forbidden; findings stay local.
- Console/JSON/SARIF redact by default; `--show-matches` is local triage only and is refused when `CI=true`.
- piilint is a detection aid, not a compliance certification.
