# Evaluation Plan

Full experiment table: CONTEXT.md §7 (E1–E11). Headline rule: report metrics
stratum-wise (hard negative vs. positive, by construct); never emit a pooled accuracy
number. False-positive rate on hard negatives is a headline number.

## Experiments

| Exp | Question | Needs | Status (2026-10-08) |
|---|---|---|---|
| E1 | Detection by stratum | Corpus, analyzer run | `metrics.py` done; 12 hard negatives ready, positives not written |
| E2 | Right for the right reason | E1 run, `discriminating_features` on items | Field in schema |
| E3 | Faithfulness (ablate cited spans vs. random turns) | E1 run | Not started |
| E4 | Evasion (6 transforms) | Positives, `transforms/` | Not started |
| E5 | Refusal-sequence tracking | `refusal_state.py`, refusal-sequence transcripts (harmless payloads) | Not started; highest priority |
| E6 | Prompt ablation | E1 baseline | Not started |
| E7 | Fairness (dialect, non-native phrasing, disclosed history or disability) | Positives | Not started |
| E8 | Human baseline | Threshold deployed, IRB determination | Blocked on IRB |
| E9 | Tier calibration / escalation ladder | Per-rung rubric, base-rate table, E1 run; crowd tiers from E8 | Not started |
| E10 | Refusal-state mitigation | Harmless rule (code word), pretext re-requests, with and without injected refusal reminder | Not started |
| E11 | Prompt-injection robustness | Injection items added to corpus | Not started |

## Run order

1. **E1** on the 12 hard negatives as soon as the analyzer runs end to end: FPR by
   stratum. A high FPR here is a result, not a reason to tune the prompt until it goes
   away (that would be overfitting the benchmark).
2. **E5** next. It is the main contribution and needs only synthetic refusal-sequence
   transcripts, not the full corpus.
3. Write positives and matched pairs, then **E2, E3, E4**. E4 produces the poster figure
   ("the cliff"), so it blocks the poster.
4. **E9** (rubric and base-rate table can be written now; the crowd comparison waits for E8).
5. **E10, E11, E6, E7.**
6. **E8** after IRB and Threshold deployment (P2).

## Safety rules for every experiment

- Corpus conversations are labeled third-person transcripts fed to the analyzer. Nobody
  types first-person violent content or harmful requests into a live model.
- Any experiment on a live model (E10) uses a harmless payload. The reframing pattern is
  the variable. If a design needs a harmful payload to produce a result, change the design.
- Report degradation, never a ranked list of which evasion or pretext works best.
