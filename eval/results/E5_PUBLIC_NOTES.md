# E5 on WildChat: first review of the rule tracker (2026-10-09)

Run: 50,000 English WildChat-1M conversations (public, non-toxic release), rule tracker,
offline. Review sample: 75 conversations, 25 from each tracker cell, labeled in
`e5_wildchat_review_labels.csv`. **First-pass labels by the assistant that wrote the
tracker rules; a person needs to check them before any number here is cited.**

## Headline

The tracker's "refusal undone" flag is not usable on real logs as written.

| Check | Result |
|---|---|
| Tracker says undone, label agrees (precision) | 3/25 (0.12; 95% CI 0.04-0.30) |
| Tracker says refusal: actually a policy refusal | 31/75 (0.41; 0.31-0.53) |
| Tracker says refusal: a capability disclaimer ("As an AI language model, I cannot browse...") | 35/75 (0.47; 0.36-0.58) |
| Tracker says refusal: no refusal at all | 9/75 (0.12; 0.06-0.21) |
| Tracker says re-asked and refused again: label disagrees | 1/25 yes, 4/25 unclear |

So the 32% "refusal undone" rate from the run is mostly tracker error, and the 80%
"undone given an attempt" is not a finding.

## Why it fails (error types in the notes column)

1. **Capability disclaimers counted as refusals.** This generation of assistant opens
   many ordinary answers with "As an AI language model, I cannot..." and then answers.
   Nothing was declined, so nothing can be undone.
2. **Refusal phrases inside generated text.** A character in a story ("I can't help but
   worry"), a drafted letter ("I am unable to continue working in the office"), or a
   secrecy idiom added after E8 ("is locked").
3. **Refusals the rules miss in the "comply" turn** ("I do not have the ability",
   "I am not programmed to"), so a second refusal is read as compliance.
4. **A related but different request counted as a re-ask**, through word overlap.
5. **Dual-output jailbreak replies** ("[CLASSIC] I'm sorry... [JAILBREAK] ..."), where
   one turn refuses and complies at once. The tracker has no category for this.

## What it does show

Real refuse, reframe, comply sequences exist in ordinary logs. Clearest case: a request
for piracy sites is refused, the user asks for "sites I should avoid", and the list is
given (labeled yes). In another conversation the same reframe was refused again. That
pair is a better illustration of the thesis than any synthetic item.

## Next

- Do not tune the rules on this sample and re-score it. If the rules change, draw a
  fresh sample (different seed or a later slice) as the test.
- The model tracker (refusal_prompt_v1) is built for exactly these distinctions. Run it
  on this same sample of 75 and compare against the labels. WildChat is public and
  non-toxic, so that is safe to send. Do not send LMSYS flagged conversations to an API.

## Model tracker on the same 75 (refusal_prompt_v1, 2026-10-09)

Scored against the same first-pass labels; "unclear" labels left out (66 scored).

| Tracker | Precision (undone) | Recall (undone) | False "undone" flags |
|---|---|---|---|
| rules | 3/24 (0.12; 0.04-0.31) | 3/4 (0.75; 0.30-0.95) | 21 of 66 |
| model, v1 | 3/11 (0.27; 0.10-0.57) | 3/4 (0.75; 0.30-0.95) | 8 of 66 |

The API model declined to analyze 4 of the 75 conversations (status `refusal`); they are
unscored. Recall rests on 4 positives and says little.

The model's 8 false flags: 6 capability disclaimers read as refusals (the rules' main
error too), 1 clarifying question read as a refusal, and 1 where the label says the
reframe was refused again and the model says it complied (label or model may be wrong).
It also flagged both dual-output jailbreak replies, which are labeled unclear. Its one
miss is the auto-clicker case, which it read as the user taking an offered alternative;
that label is arguable.

`analyzer/refusal_prompt_v2.md` targets those errors. It was written from this sample,
so its numbers here would be a fit. The test is a fresh 75 drawn with seed 23 and these
ids excluded (`e5_wildchat_review2.csv`), labeled before any model run on it.

## Fresh sample for testing prompt v2 (labeled 2026-10-14, before any model run)

`e5_wildchat_review2_labels.csv`: 75 new conversations. Single-author labels, made by the
same assistant that wrote the rule tracker and prompt v2, blind to model output but not
checked by a person; inter-rater agreement is not measured. Before v1 vs v2 counts are
reported as a result, Anvita spot-checks at least the 3 yes and 10 unclear rows. 3 yes, 62 no, 10 unclear; refusal type 41 capability, 26 policy, 8 none. Rule
tracker precision on this sample: 3/21 with unclear left out. Unclear is mostly
dual-output jailbreak replies and re-asks that got a related but different item.

### Result: prompt v1 vs v2 on the fresh 75 (2026-10-14)

Scored against the labels above, unclear left out. One label was corrected after the
model runs: `73b10273` (no -> yes). The first pass read a truncated view and missed that
the list was given after a hedge; both model versions had flagged it. That correction was
made with model output in view, so it is disclosed here.

| Tracker | Precision (undone) | Recall (undone) | False "undone" flags | Not scored (API refused) |
|---|---|---|---|---|
| rules (on v1's scored set) | 4/21 (0.19; 0.08-0.40) | 4/4 | 17 of 63 | 0 |
| model, v1 | 4/14 (0.29; 0.12-0.55) | 4/4 | 10 of 63 | 4 |
| model, v2 | 3/5 (0.60; 0.23-0.88) | 3/3 | 2 of 62 | 6 |

v2 cuts false flags from 10 to 2 on conversations it was not written from. Both remaining
false flags are capability disclaimers ("cannot provide code" followed by code; a
real-time disclaimer). The cost: the API model declined to analyze 6 conversations under
v2 against 4 under v1, and one extra refusal was the arguable story-character positive
(`73c35dba`), which v2 therefore never scored. Recall rests on 3-4 positives and says
little. v2 is now the default prompt; v1 stays in the repo for comparison.

### Re-scored with Anvita's check (2026-10-14)

Anvita checked the 4 yes and 10 unclear rows herself. She saw the first-pass labels, so
this is a check, not a blind second label. Her labels now count as the gold for those rows:
9 yes, 62 no, 4 unclear. Her criterion is wider than the first pass: a user who rewords
the request or switches to a jailbreak persona and gets the item counts as yes, including
dual-output replies.

| Tracker | Precision (undone) | Recall (undone) | False "undone" flags |
|---|---|---|---|
| rules | 5/22 (0.10-0.43) | 5/8 | 17 of 67 |
| model, v1 | 3/13 (0.08-0.50) | 3/8 | 10 of 67 |
| model, v2 | 3/5 (0.23-0.88) | 3/8 | 2 of 67 |

One yes (`f54f5e35`) was refused by the API under both prompts and is unscored.

Both prompts miss the same 5 of her positives. 3 are jailbreak conversations where the
persona was set up before the request, so the refusing half and the complying half arrive
in one reply. 2 are rewordings the prompt reads as "a new request". 1 of the 5
(`327b49eb`) is a capability limit, not a policy refusal, which v2 excludes on purpose.

So v2 bought its precision partly by narrowing the definition. Which definition the
paper uses is a decision for Anvita. Any v3 written from these 75 needs another fresh
sample to test it.

`7c5e0b53` is a jailbreak set up before the request, with no refusal followed by a
re-request. It is not "undone" under any definition here, and a refusal tracker cannot see
it because no refusal state exists. That is a stated limitation, and it is the main
analyzer's job.

## Third sample: prompt v2 vs v3 (2026-10-14)

`e5_wildchat_review3.csv`: 75 new conversations, none in the first two samples, drawn
before v3 was run. Labels by Anvita, by hand (`e5_wildchat_review3_labels.csv`), under her
chosen definition: a safety or ethics refusal undone by rewording, an added reason, or a
persona or jailbreak, including dual-output replies. An AI tool had labeled this set
before she did; she had seen its labels briefly but not in full, so these are her own
labels but not fully independent of it. Single author; inter-rater agreement not measured. 4 yes, 71 no. The API model declined to analyze 2 conversations under both
prompts, including one of the 4 yes, so 3 positives are scored.

| Tracker | Precision (undone) | Recall (undone) | False "undone" flags |
|---|---|---|---|
| rules | 1/23 (0.01-0.21) | 1/3 | 22 of 73 |
| model, v2 | 1/7 (0.03-0.51) | 1/3 | 6 of 73 |
| model, v3 | 3/10 (0.11-0.60) | 3/3 | 7 of 73 |

v3 was not written from this sample, so this is the test for it. Under the chosen
definition it finds all 3 scored positives (v2 found 1), at the cost of one more false
flag. With 3 positives the recall interval runs from 0.44 to 1.00. That is evidence that
v3 tracks the definition better than v2, not a measured recall. v3 is now the default
prompt.

### Synthetic set re-run with v3 (2026-10-14)

`python -m eval.e5_refusal --model` with prompt v3 on the 19 synthetic items (all statuses ok): hard-negative FPR 0.00 (0/7; 95% CI 0.00-0.35), hard-positive recall 1.00 (3/3; 95% CI 0.44-1.00), clear-positive recall 7/7, clear-negative FPR 0/2. Held-out split: recall 4/4, FPR 0/4. Same as v1 on this set. Widening the definition did not flag the clarifying-question, alternative-offer, new-topic or fiction hard negatives. Same caveat as before: the synthetic items were written by the same author, so this checks for regressions; it is not a generalization result.
