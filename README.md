# Pathway

Explainable AI course project (Duke MIDS, Fall 2026). Studies whether treating a model's
own refusal as conversation-level state — rather than a discarded, per-message event —
can catch refuse → reframe → comply patterns that per-message moderation misses.

Full project context, constraints, and task list: see [`CLAUDE.md`](./CLAUDE.md).

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

Scoping complete, implementation starting. See `CLAUDE.md` §10 for immediate tasks.
