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
   secrecy idiom added after E10 ("is locked").
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
