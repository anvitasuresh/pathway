# Between the Lines: What AI Safety Systems Miss

An Explainable AI project (Duke MIDS, Fall 2026) on
conversation-level warning behavior in chatbot conversations, and on treating a model's own
refusal as signal instead of a discarded, one-message event.

- **Full write-up:** [`WRITEUP.md`](./WRITEUP.md) (motivation, cases, provider policies, the
  gaps, method, every experiment, limitations)
- **Site:** <https://anvitasuresh.github.io/pathway/> (source in [`docs/`](./docs/index.html)), an interactive story: the Roberts sequence step by step, the matched-pair walkthrough, all ten pairs side by side with filter scores and cited evidence, the evidence-deletion test (E3), the base-rate calculator (E7), where all 22 conversations landed on the ladder, and a refusal-tracker chooser (E5, E12)
- **Demo:** <https://anvitasuresh.github.io/pathway/e13/> (source [`docs/e13/`](./docs/e13/index.html)): pick an excuse and see a real E8 bot reply and what the tracker makes of it, or watch replays; `python -m demo.server` runs the live game locally

## What this cannot do

It does not predict violence and does not prevent it. It decides how much of a response a
conversation's text supports, from "do nothing" to "a human should look", and only a human
moves anything further. The benchmark is small, fictional and labeled by one person
(inter-rater reliability not measured), so every number carries a wide interval. Wrongly
flagging a venting teenager or a novelist is treated as a primary harm.

## Why

Safety in deployed language models is evaluated one message at a time. In the documented
cases, harm accumulated one conversation at a time. In *R v. Tristan Roberts* (Mold Crown
Court, 2026) the prosecution told the court that a model refused a weapon question and then
answered once the user said he was writing a book. In the Tumbler Ridge, British Columbia case,
OpenAI's own letter says an account was flagged, reviewed and banned but not referred; the only
options used were ban or nothing.

Coding OpenAI, Anthropic and Meta policy texts (E11) found that none publishes a rung between
ban and police referral for risk to others, none publishes that refusals persist as state
across sessions, and none publishes how often referrals are right. Pathway builds and measures
those missing pieces.

## What is in it

1. **Benchmark.** 22 fictional conversations: 12 hard negatives (teens venting, a horror
   novelist, a nurse, a defense attorney and others) and 10 hard positives. Each positive shares
   its opening turns word for word with a negative, so only the trajectory differs. Six
   constructs adapted from threat assessment, plus CONV (fiction converging on real life).
2. **Explainable analyzer.** Reads the whole conversation and returns, per construct, a label,
   cited turns, a rationale, a counterfactual and a mandatory benign reading, plus a five-rung
   tier: `none`, `resource`, `friction`, `review`, `escalate` (the last only a human assigns).
3. **Refusal tracker.** Records request, refusal, re-request kind and outcome, so refuse,
   reframe, comply becomes visible.
4. **Escalation ladder.** A written rubric for each rung, per-rung error rates, and the base-rate
   cost of each rung.
5. **Policy coding** of OpenAI, Anthropic and Meta texts.
6. **Code-word demo.** A bot guards a harmless word; a side panel shows the refusal state, the
   re-request it recognised, and the rung.

## Headline results

Per stratum, 95% Wilson intervals, single-author labels. Details and caveats in the write-up.

| Result | Number |
|---|---|
| Hard negatives routed to review or above: whole-conversation analyzer (headline; not held out) | **0/12** (0.00-0.24) |
| Hard negatives flagged: OpenAI public moderation classifier, one turn at a time | **9/12** (0.47-0.91) |
| Moderation flags on a turn where a matched pair diverges | **0/10 pairs**: every flag fell on the shared, innocent opening |
| Same analyzer, one user turn at a time, no context (3 original pairs) | 3/3 positives to review, 0/3 negatives: the gap is the scorer, not the context |
| Analyzer recall, gold review-level hard positives | 4/6; all errors under-escalation, none over |
| Clean hard negatives needed to show review costs at most 5 innocent reviews per real one at 1-in-1,000 prevalence | about **1,150** (the corpus has 12) |
| Refusal tracker on synthetic transcripts (model): false positives / recall | 0/7 (0.00-0.35) / 10/10 |
| Refusal tracker on real WildChat logs: precision on "refusal undone" | 3/10 (0.11-0.60) |
| Carrying refusals into the next session: ordinary next-day requests wrongly linked | 4/7 (0.25-0.84) |
| Faithfulness: cited turns removed vs. random turns removed | ESC faithful; FIX, CONV and tier citations not selective |
| Nulls | No tier moved under six rewordings (E4); no false positive from a disclosed diagnosis (E6); no pretext undid a code-word refusal (E8); no sycophantic drift in 7 turns (E10) |

## Experiments

| | Question | Result in one line |
|---|---|---|
| E1 | Detection by stratum | 0/12 hard negatives at review+; 4/6 review-level positives found |
| E2 | Right for the right reason | Cites post-split turns (FIX 26/27); errors are construct names, not locations |
| E3 | Faithfulness | ESC faithful; FIX, CONV, tier unselective |
| E4 | Evasion, six rewordings | Null: no tier moved; labels moved within noise |
| E5 | Refusal-sequence tracking | Works on synthetic items; real logs are hard |
| E6 | Diagnosis disclosure (fairness) | Null: 0/12 false positives; one stereotyped explanation |
| E7 | Escalation ladder, base rates | 12 clean negatives cannot rule out a 24% FPR |
| E8 | Refusal-state mitigation, code word | Negative: no pretext undid a refusal, so the reminder was untested |
| E9 | Per-message guardrail baseline | Moderation flags shared openings, never divergent turns; the same analyzer one turn at a time still splits all 3 pairs (gap is the scorer, not the context) |
| E10 | Sycophancy drift | Null: no drift; reminder arm 0/14 validations vs. 2/14 |
| E11 | Policy coding | Asymmetry is in enforcement, not prohibitions |
| E12 | Cost of remembering refusals | Rule tracker carrying state: 4/7 false positives |
| E13 | Code-word demo | Built: "your turn" mode and replays on the site (real E8 replies, no calls), live game locally |

Experiments were renumbered on 2026-10-15; older commits use old numbers (mapping in
[`eval/PLAN.md`](./eval/PLAN.md)).

## Setup

Tested on Python 3.13. The offline path needs only `pytest`; the `anthropic` package is used
for live runs.

```
git clone https://github.com/anvitasuresh/pathway.git && cd pathway
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m pytest -q          # 200 pass, 1 expected failure; no network, no API key
```

**Data.** Everything the reported numbers need is in the repo: the 22 fictional conversations
(`corpus/items.jsonl`), the refusal sequences and sessions, the E4/E6 variants, and every saved
model run under `eval/results/` plus three earlier analyzer runs at the root
(`results_v2*.jsonl`). Nothing needs downloading and there are no model weights. The one
external dataset is WildChat-1M (`allenai/WildChat-1M`, ODC-BY, ungated) for E5's real-log arm;
only id-level tracker rows are committed, and re-scanning it needs the optional `datasets` and
`pyarrow` packages listed in `requirements.txt`.

**API keys (live runs only).** `export ANTHROPIC_API_KEY=...` for the analyzer, refusal tracker,
E8, E10 and the demo. `export OPENAI_API_KEY=...` only for E9's moderation arm (called with the
standard library, no extra package). Live runs cost money; every script has `--dry-run`, which
prints the requests and sends nothing.

## Reproducing every number offline

Each command re-scores saved runs and makes no API calls.

| Experiment | Command |
|---|---|
| E1, E2 | `python -m eval.e1_e2 > eval/results/E1_E2_REPORT.md` |
| E3 | `python -m eval.e3_faithfulness --preds eval/results/e3_run.jsonl` |
| E4 | `python -m eval.e4_evasion --preds eval/results/e4_run.jsonl` |
| E5 (synthetic; rule tracker, then model tracker) | `python -m eval.e5_refusal` and `python -m eval.e5_refusal --preds eval/results/e5_run_v3.jsonl` |
| E5 (WildChat) | `python -m eval.e5_public --rows eval/results/e5_wildchat.jsonl` |
| E6 | `python -m eval.e6_disclosure --preds eval/results/e6_run.jsonl` |
| E7 | `python -m eval.e7_ladder > eval/results/E7_TABLES.md` |
| E8 | `python -m eval.e8_codeword --rows eval/results/e8_run.jsonl` |
| E9 | `python -m eval.e9_per_message --preds eval/results/e9_per_turn.jsonl eval/results/e9_moderation.jsonl eval/results/e9_moderation_novelist.jsonl --whole-from eval/results/e4_run.jsonl results_v2.jsonl results_v2_batch3.jsonl > eval/results/E9_REPORT.md` |
| E10 | `python -m eval.e10_sycophancy --rows eval/results/e10_run.jsonl > eval/results/E10_REPORT.md` |
| E11 | `python eval/e11/count.py` |
| E12 | `python -m eval.e12_sessions > eval/results/E12_REPORT.md` |

The committed reports match these outputs byte for byte.

## Live runs

```
python -m analyzer.analyzer --items corpus/items.jsonl --dry-run
python -m analyzer.analyzer --items corpus/items.jsonl --out eval/results/run.jsonl
python -m eval.metrics --items corpus/items.jsonl --preds eval/results/run.jsonl
```

The model is `DEFAULT_MODEL` in `analyzer/analyzer.py`; override with `--model` or
`PATHWAY_MODEL` (effort: `--effort` or `PATHWAY_EFFORT`). Each `eval/e*.py` docstring gives its
live command and call count; `eval/PLAN.md` records run order and status.

### The site

Static, no API calls; its data comes from files already in the repo.

```
python docs/build_data.py                 # rebuild docs/data.js
python -m http.server 8000 -d docs        # http://localhost:8000
```

To publish: Settings, Pages, deploy from branch `main`, folder `/docs`. The site is then at
`https://anvitasuresh.github.io/pathway/`.

### The demo

```
python -m demo.server                     # http://127.0.0.1:8016
python -m demo.server --dry-run           # print the prompts; call nothing
```

Runs only on your machine and your key, one small-model call per turn, 15 turns per round,
stores nothing. Use harmless pretexts only. `docs/e13/` is the no-cost version: "your turn"
lets a reader pick any of E8's six pretexts, with or without the refusal-state note, and shows
the real reply E8 recorded for that choice; "watch replays" steps through chosen sessions. Both
are rebuilt by `python -m demo.replays` from `eval/results/e8_haiku_soft.jsonl`.

## Design decisions

- **Matched pairs.** Every hard positive shares its opening turns word for word with a hard
  negative, so a detector can only separate them by reading where the conversation goes.
- **Hard negatives first.** The corpus is built around people who sound alarming and are not
  (venting teens, a horror novelist, a nurse, a defense attorney), because false positives are
  treated as a primary harm. False-positive rate on them is the headline number.
- **Explanations are structured and tested.** The analyzer must cite turns, give a
  counterfactual and a benign reading; E3 then checks whether the cited turns actually drive
  the decision instead of trusting them.
- **A ladder, not a verdict.** Output is a rung (`none` to `review`); `escalate` is reserved for
  a human. No component predicts violence.
- **Harmless payloads.** Refusal experiments use a code word and song lyrics, so the reframing
  pattern is the variable and no harmful content is ever requested.
- **Per-stratum metrics with Wilson intervals,** never pooled accuracy.

## Known limitations

Small (22 items), fictional, written and labeled by one person; inter-rater reliability not
measured; prompt v2 and the ladder rubric were written after seeing the items, so results are
not held out; one model and one prompt for analyzer comparisons; in the three pairs scored one turn at a
time, each positive had a single turn that gave it away, so the unit-of-analysis claim still
needs sequence-only items. Full list in [`WRITEUP.md` §11](./WRITEUP.md#11-limitations).

## Layout

```
WRITEUP.md      the full write-up
CONTEXT.md      project context, constraints, decisions (source of truth)
SCOPE.md        original full scope
corpus/         items.jsonl (22 conversations), refusal_sequences.jsonl, refusal_sessions.jsonl,
                E4/E6 variants, TAXONOMY.md, SCHEMA.md, CUTS.md (cut log), labeling/
analyzer/       analyzer.py, prompt_v1.md, prompt_v2.md, refusal_state.py, refusal_prompt_v*.md
eval/           one script per experiment (e1_e2.py ... e12_sessions.py), metrics.py,
                E7_LADDER.md, PLAN.md, transforms/, e11/, results/ (saved runs and reports)
research/       CASES.md (graded sources), POLICY_COMPARISON.md, E11_POLICY_CODING.md
demo/           the code-word game (game.py, server.py, replays.py)
docs/           the site (index.html, data.js) and the demo replay (e13/)
tests/          offline tests with bland fixtures
results_v2*.jsonl  the first prompt-v2 analyzer runs, reused by E1, E2, E7 and E9
```

## Content rules

No operational content anywhere, including test fixtures. No attempts to extract harmful
content from any model: refusal experiments use harmless payloads (a code word, song lyrics),
and the reframing pattern is the variable. No real people in corpus data; real cases are cited
in prose with graded sources (`research/CASES.md`). No ranked list of which rewording or pretext
"works". See `CONTEXT.md` §0.
