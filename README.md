# Pathway

Explainable AI course project (Duke MIDS, Fall 2026). Studies whether treating a model's
own refusal as conversation-level state — rather than a discarded, per-message event —
can catch refuse → reframe → comply patterns that per-message moderation misses.

Full project context, constraints, and task list: see [`CONTEXT.md`](./CONTEXT.md).

## Layout

```
corpus/      TAXONOMY.md, SCHEMA.md, items.jsonl, CUTS.md, datasheet
analyzer/    prompt_v*.md, analyzer.py, refusal_state.py
eval/        PLAN.md, run_analyzer.py, metrics.py, transforms/, results/
research/    CASES.md (with source quality), POLICY_COMPARISON.md
site/        scrollytelling build
threshold/   public artifact
```

## Status

Implementation underway. Done: analyzer plumbing, stratum-wise metrics, sourced case table,
policy comparison, first 12 hard negatives. See `CONTEXT.md` §10 for next tasks and §11 for
changes since the original proposal; `eval/PLAN.md` for experiment status.

## Running

```
pip install -r requirements.txt
python -m pytest -q                                              # no network, bland fixtures
python -m analyzer.analyzer --items corpus/items.jsonl --dry-run # render requests, call nothing
python -m analyzer.analyzer --items corpus/items.jsonl --out eval/results/run.jsonl
python -m eval.metrics --items corpus/items.jsonl --preds eval/results/run.jsonl
python -m eval.e3_faithfulness --out eval/results/e3_run.jsonl   # E3, see docstring
python -m eval.transforms.build                                  # rebuild E4 variants
python -m eval.e4_evasion --out eval/results/e4_run.jsonl --figure eval/results/e4_cliff.svg
python -m eval.e4_evasion --assistant neutral --out eval/results/e4_neutral.jsonl
```

Model defaults to `DEFAULT_MODEL` in `analyzer/analyzer.py`; override with `--model` or `PATHWAY_MODEL`
(effort: `--effort` / `PATHWAY_EFFORT`).
