# Corpus Item Schema

TODO: define the per-item JSON schema for `items.jsonl`. Minimum fields per CONTEXT.md §6A:

- `id`
- `conversation` (list of turns)
- `is_hard_negative` (bool)
- `gold_labels` (per construct: present / absent / uncertain)
- `evidence_spans`
- `discriminating_features`
