# Examples

Synthetic-only pointers for trying `piilint` quickly. **No real PII** lives here or under `tests/corpus/`.

## Notebook output leak

Story: a notebook prints `df.head()` and the **output cell** still contains customer-looking rows when the `.ipynb` is committed.

- Demo notebook: [`../tests/corpus/notebook/leak_demo.ipynb`](../tests/corpus/notebook/leak_demo.ipynb)
- Full labeled corpus: [`../tests/corpus/`](../tests/corpus/)

```bash
# from repo root
piilint tests/corpus/notebook
# or with the local checkout
uv run piilint tests/corpus/notebook
```

You should see credit-card findings from the notebook **output** (masked samples only in the report).

## More formats

The corpus also covers text, CSV, JSON/JSONL, and Parquet under `tests/corpus/`. Prefer those fixtures over inventing sample data with real personal information.

## Policy packs

Example org `piilint.toml` starters live under [`policies/`](./policies/) (strict CI, data-eng, open-source). Detection-aid templates only ? see the policies README disclaimer.
