# Pathway

**Reading conversations, not messages.** An Explainable AI project (Duke MIDS, Fall 2026) on
conversation-level warning behavior in chatbot conversations, and on treating a model's own
refusal as signal instead of a discarded, one-message event.

- **Full write-up:** [`WRITEUP.md`](./WRITEUP.md) (motivation, cases, provider policies, the
  gaps, method, every experiment, limitations)
- **Site:** [`docs/`](./docs/index.html), a scrolling explainer of the results
- **Demo:** [`docs/e13/`](./docs/e13/index.html) (replay) and `python -m demo.server` (live, local)

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
| E9 | Per-message guardrail baseline | Moderation flags shared openings, never divergent turns |
| E10 | Sycophancy drift | Null: no drift; reminder arm 0/14 validations vs. 2/14 |
| E11 | Policy coding | Asymmetry is in enforcement, not prohibitions |
| E12 | Cost of remembering refusals | Rule tracker carrying state: 4/7 false positives |
| E13 | Code-word demo | Built: replay on the site, live game locally |

Experiments were renumbered on 2026-10-15; older commits use old numbers (mapping in
[`eval/PLAN.md`](./eval/PLAN.md)).

## Running it

```
pip install -r requirements.txt
python -m pytest -q          # 199 pass, 1 expected failure; no network, no API key
```

Every reported number regenerates offline from saved runs, with no API calls:

```
python -m eval.e1_e2 > eval/results/E1_E2_REPORT.md
python -m eval.e3_faithfulness --preds eval/results/e3_run.jsonl
python -m eval.e5_refusal
python -m eval.e7_ladder > eval/results/E7_TABLES.md
python -m eval.e12_sessions > eval/results/E12_REPORT.md
python eval/e11/count.py
```

Live runs need `ANTHROPIC_API_KEY` (E9's moderation arm also needs `OPENAI_API_KEY`) and cost
money. Every script has `--dry-run`, which prints the requests and sends nothing:

```
python -m analyzer.analyzer --items corpus/items.jsonl --dry-run
python -m analyzer.analyzer --items corpus/items.jsonl --out eval/results/run.jsonl
python -m eval.metrics --items corpus/items.jsonl --preds eval/results/run.jsonl
```

The model is `DEFAULT_MODEL` in `analyzer/analyzer.py`; override with `--model` or
`PATHWAY_MODEL` (effort: `--effort` or `PATHWAY_EFFORT`). See each `eval/e*.py` docstring for
its live command and call count.

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
stores nothing. Use harmless pretexts only. `docs/e13/` is the no-cost replay.

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
```

## Content rules

No operational content anywhere, including test fixtures. No attempts to extract harmful
content from any model: refusal experiments use harmless payloads (a code word, song lyrics),
and the reframing pattern is the variable. No real people in corpus data; real cases are cited
in prose with graded sources (`research/CASES.md`). No ranked list of which rewording or pretext
"works". See `CONTEXT.md` §0.
