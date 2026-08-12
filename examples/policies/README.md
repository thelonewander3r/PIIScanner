 Example org policy packs

Copy any file below to your repo root as `piilint.toml`, or point tools at it when your workflow supports a config path. These are **starting points**, not mandates.

## Packs

| File | Intent |
|---|---|
| [`strict-ci.toml`](./strict-ci.toml) | CI gate: fail on medium+, IP off, higher `min_confidence` |
| [`data-eng.toml`](./data-eng.toml) | Tabular-heavy trees: common excludes; pair with `piilint baseline` |
| [`open-source-lib.toml`](./open-source-lib.toml) | Noisy codebases: IP off, higher confidence, sample allowlisted domains |

```bash
# from your project root
cp examples/policies/strict-ci.toml ./piilint.toml
piilint scan . --fail-on medium
```

## Using with redact

`piilint redact PATH -o OUT_DIR` loads the same config/policy as `scan` (entity toggles, allowlists, inline `# piilint: ignore`, `min_confidence`, excludes). Allowed or suppressed matches are **not** rewritten.

## Disclaimer

These examples are detection-aid templates only. They do **not** make anyone GDPR, HIPAA, PCI, or otherwise compliant. piilint cannot guarantee that all sensitive data is found. Tune policies to your risk tolerance and review findings with humans.
