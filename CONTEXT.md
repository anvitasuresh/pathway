# Pathway — Project Context

**Owner:** Anvita Suresh, Duke MIDS (Master's in Interdisciplinary Data Science)
**Course:** Explainable AI, Fall 2026 · Project 1 due Oct 19, 2026
**Status:** Scoping complete, implementation starting
**This file:** paste-in project context. Read fully before writing code.

---

# 0. Operating rules for this repo

Hard constraints, not preferences. They apply to every file generated here.

**Never generate operational content.** No weapons specifics, acquisition, logistics,
timing, targeting, or anything that functions as instruction for violence — in any file,
including test fixtures, docstrings, and example data. The corpus represents behavioral
*patterns*; it never represents *technique*.

**Never attempt to extract harmful content from a model.** This project studies whether
reframing changes *refusal behavior*, measured on harmless targets. It does not test
whether a model can be made to produce attack planning. If an experiment design would
require obtaining such content to produce a result, the design is wrong — change the
design, not the constraint.

**No real people or institutions in the corpus.** Fictional names, fictional schools,
invented places. Real cases are cited in prose with sources; they are never reproduced
as data.

**False positives are a primary harm.** Every metric, interface, and write-up treats
wrongly flagging a venting teenager as a serious failure with real consequences, not as
a cost of doing business.

**Do not overclaim.** This system does not prevent violence and cannot. Any language
suggesting otherwise is a bug.

---

# 1. The thesis

> Safety in deployed language models is evaluated one message at a time. Harm in the
> documented cases accumulated one conversation at a time. Nothing in the training
> pipeline, the moderation stack, or the review workflow is built to see the difference.

There is a structural reason. Safety behavior is trained with response-level preference
optimization — the unit of safety is the turn because the unit of the reward signal is
the turn (Qi et al. 2024, "Safety Alignment Should Be Made More Than Just a Few Tokens
Deep"). Nothing in that pipeline is shaped to notice a trajectory.

---

# 2. Motivating evidence

## 2.1 The anchor case: R v. Tristan Roberts (Mold Crown Court, sentenced 25 Mar 2026)

The most important case for this project, because it is **court-documented** rather than
reported secondhand, and because the mechanism is explicit.

- Roberts, 18, murdered his mother Angela Shellis, 45, in Prestatyn, North Wales, on
  24 October 2025. Life sentence, minimum 22 years 6 months.
- He asked DeepSeek which was the better weapon for a murder, a hammer or a knife.
- **The model refused.**
- He then said he was writing a book about serial killers. **The model answered** — per
  the prosecutor, indicating a hammer suited an inexperienced person, with pros and cons.
- He also asked about removing blood and DNA traces.
- Over the preceding weeks he posted misogynistic content and stated violent intent on
  Discord, was repeatedly but temporarily banned there, and set his status to "Tonight's
  the night" on the night of the murder.

Three things this establishes that speculation could not:

1. **The fiction wrapper works, and a court said so.** Refusal → reframe → compliance is
   a documented sequence, not a hypothesis.
2. **The refusal was discarded signal.** The model correctly judged the request
   impermissible and declined. That judgment went nowhere — no state carried forward, no
   accumulation, no effect on the next turn.
3. **Warning behaviors were distributed across platforms.** Fixation and leakage on
   Discord; capability-seeking on DeepSeek. No single system saw the whole picture.

## 2.2 Other violent-crime cases

- **FSU shooting (Apr 2025):** reportedly asked ChatGPT about weapon choice and the
  busiest times at the student union — the *mosaic* pattern of individually innocuous
  queries.
- **British Columbia shooting (Feb 2026):** per Canadian court filings, OpenAI's systems
  flagged the chats and staff recommended alerting law enforcement; leadership declined
  and banned the user instead. OpenAI has said it is overhauling its referral protocol.
- **Acton MA double homicide (Aug 2026):** "Gothic novel" stories whose content tracked
  the user's real circumstances. *Charges pending, defendant was a minor, prosecutors
  have not alleged the model supplied a plan. Handle carefully.*
- **Finland school stabbing (2024):** reportedly hundreds of attack-planning searches.
- **Seoul / Gangbuk (early 2026):** reportedly consulted ChatGPT about drug and alcohol
  lethality before overdose deaths. *Weakly sourced; verify before citing.*

## 2.3 Sourcing discipline

The original case list came partly from Facebook posts and Wikipedia. Before any case
enters the site or write-up it needs a primary or near-primary source: court filings,
sentencing remarks, CPS/DA statements, or established outlets. Roberts is solid (CPS
statement, published sentencing remarks, BBC). Seoul is not yet. Maintain
`research/CASES.md` with a source-quality column; the site renders only verified rows.

---

# 3. How these people were actually caught

The most important research finding so far. **Two detection regimes exist, and only one
of them works.**

## 3.1 CSAM: mature, proactive, platform-side

- Platforms scan user-provided content against **known-CSAM hash databases** and run
  **classifiers** for novel material, including on prompts and uploads to generative
  products. Google reported 600+ apparent CSAM instances to NCMEC via hash matching on
  user prompts to its generative AI products in 2024.
- US electronic service providers are **legally required** to report to NCMEC's
  CyberTipline, which routes to law enforcement. Many reports file automatically on hash
  match without human review.
- Volume is enormous: NCMEC received 1.5M+ CyberTipline reports with a generative-AI
  nexus in 2025 — 7,000+ for generating or possessing AI CSAM, 30,000+ for attempts to
  generate it by uploading a file with text prompts.
- Arrests typically begin from a CyberTipline referral or a tip; device forensics
  confirms.

**The pipeline has a measurement-validity problem worth criticizing.** Stanford's Center
for Internet and Society, following Bloomberg reporting, found that of ~half a million
H1-2025 reports with the "Generative AI" checkbox ticked, **at least 78% involved no
AI-generated CSAM at all.** A single ambiguous checkbox carries the entire measurement.
If the most mature detection pipeline in existence has label noise that bad, every claim
about AI-related harm rates deserves scrutiny — including ours.

## 3.2 Violent crime: no proactive pipeline at all

Roberts was identified by a neighbour's doorbell camera showing him leading his mother
from the house at 03:19, a blood-stained path at the nature reserve leading to the body,
his own Discord posts, and a dictaphone recording he made himself. Arrested within hours
of the body being found. **The DeepSeek queries emerged afterward, from laptop
forensics.**

That is the pattern in every violent case: conventional policing identifies the suspect,
and AI involvement surfaces retrospectively in device forensics. The AI evidence is
archaeological. The one case where a platform detected something in advance is British
Columbia — and there the flag was raised, reviewed, and not referred.

## 3.3 Why the asymmetry, and why it matters

| | CSAM | Violent ideation |
|---|---|---|
| Artifact | A file; exists or doesn't | None. Only language |
| Detection | Hash match + classifier | No deployed conversation-level system |
| Legal duty | Mandatory reporting (US) | None |
| Base rate | Low but tractable | Vanishingly low |
| False-positive cost | Serious | Severe, borne by the innocent |
| Signal unit | The file | The trajectory — which nothing tracks |

Hash matching works because CSAM is a *bright-line artifact*. Violent ideation is a
*trajectory in language*, with an enormous and sympathetic false-positive population:
novelists, researchers, clinicians, angry teenagers. You cannot hash a trajectory, and
the base rate makes naive classification useless.

**This asymmetry is the project's motivation** — not "chatbots are dangerous," but "we
have proactive detection where the signal is an artifact and essentially nothing where
the signal is a trajectory, and the second is the problem nobody has tooling for."

---

# 4. Existing guardrails and where they fail

## 4.1 What's deployed

**Anthropic:** Constitutional AI (models critique and revise against written principles);
a Unified Harm Framework spanning physical, psychological, economic, societal, and
autonomy harms; Constitutional Classifiers as real-time filters against universal
jailbreaks; red lines on autonomous weapons, mass surveillance, and CBRNE; pre-deployment
testing under the Responsible Scaling Policy; published threat intelligence.

**OpenAI:** usage policies and the Model Spec; a threat intelligence and disruption team
(formed 2024) publishing recurring "Disrupting malicious uses of AI" reports; account
termination and intelligence sharing with industry and law enforcement.

Both are serious programs. The critique is not that they are absent — it is that they
are **aimed at a different threat model than the one in these cases**.

## 4.2 Seven critiques, each grounded in evidence

1. **Unit-of-analysis mismatch.** Classifiers and refusals operate per message. Every
   case is longitudinal. What is measured is not what causes harm.

2. **Refusal is discarded signal.** Roberts was refused, reframed, and succeeded. A
   refusal is the system's own judgment that a request was impermissible — and it carries
   no state forward, triggers no accumulation, informs no later turn. *Biggest design
   gap, and the most actionable.*

3. **Reframing defeats refusal cheaply.** "I'm writing a book" took no technical skill,
   no jailbreak, no prompt engineering. Court-documented.

4. **Detection without a referral ladder.** BC shows the failure wasn't only detection —
   the options were ban or nothing. No graduated response, no documented escalation path,
   no evidence package for the person deciding.

5. **Policy asymmetry.** Published red lines concentrate on state-scale and catastrophic
   risk: CBRNE, cyber, autonomous weapons, mass surveillance. Individual interpersonal
   violence — what actually happened, repeatedly — is comparatively thinly specified.
   Put the two bodies of policy text side by side; the asymmetry is visible on the page.

6. **Measurement validity.** The 78% finding shows even the mature pipeline mislabels at
   scale. Any guardrail-efficacy claim built on such counts inherits that noise.

7. **Per-provider guardrails, portable users.** Roberts used DeepSeek. Warning behavior
   was on Discord. Guardrails are enforced per provider; users are not. No provider sees
   the trajectory, and the strongest safety program in the industry is a rounding error
   if the user opens a different tab.

## 4.3 The design proposal that follows

**Refusal as signal.** Instead of treating a refusal as a terminal event, treat it as an
observation entering conversation-level state. One refusal means nothing. A refusal
followed by the same request reframed means something specific — and it is exactly the
sequence Roberts documents. Cheap, requires no new detection capability, uses a signal
every provider already generates and discards, and is directly evaluable here.

**This is the project's most defensible novel contribution. Prioritize it.**

---

# 5. Research questions

- **RQ1** Can conversation-level warning behaviors be detected with acceptable
  false-positive cost on hard negatives?
- **RQ2** Are cited evidence spans *faithful* — does removing them flip the finding, or
  is the explanation decorative?
- **RQ3** How much does detection degrade under reframing (fiction, paraphrase,
  euphemism, roleplay, translation, dilution)?
- **RQ4** Does **refusal-sequence state** (refuse → reframe → comply) catch cases
  per-message moderation misses? *Highest-value; directly motivated by Roberts.*
- **RQ5** How much do *humans* disagree on these judgments, and what does that imply for
  interpreting any model's performance?

RQ5 matters more than it looks. Nobody reports human disagreement rates on these
judgments. Without that denominator, a model's 80% agreement with gold labels is
uninterpretable — it could sit inside the band of irreducible human disagreement, or far
outside it. The public artifact (§6C) is how we measure it.

---

# 6. Components

## A. Benchmark

~60 synthetic conversations, hard-negative-heavy, with per-construct gold labels,
evidence spans, and a `discriminating_features` field stating what a correct system
should key on.

Constructs (see `corpus/TAXONOMY.md`): `FIX` fixation, `IDN` identification, `LEAK`
leakage, `RHRS` rehearsal, `ESC` escalation, `CONV` reality convergence. The first five
adapt Meloy's TRAP-18 and the Secret Service NTAC pathway-to-violence literature. `CONV`
is ours, and is the construct the Acton case implies.

Hard negatives (half the corpus): horror novelists, true-crime researchers, trauma
clinicians, criminology students, defense attorneys, and **teenagers venting about
parents** — the highest-volume, highest-stakes false positive.

**Write all hard negatives before any positives.** Writing positives first produces a
benchmark shaped to flatter the detector.

High-value extension: **matched pairs** — each hard positive paired with a hard negative
differing in the minimum features needed to flip the label. Turns "scored 80%" into
"blind to exactly the feature carrying the signal."

## B. Analyzer

Returns, per construct: label (`present`/`absent`/`uncertain`), cited evidence turns, a
one-line rationale, a counterfactual, plus a mandatory `competing_explanation` (strongest
benign reading) and a **graduated tier** (`none`/`resource`/`friction`/`review`/
`escalate`) rather than a binary flag. Binary is what failed in BC.

Prompt in `analyzer/prompt_v1.md`. Version every prompt; prompt sensitivity is itself a
reportable result.

**Refusal-sequence tracking (RQ4)** is a distinct module: detect request → refusal →
semantically equivalent re-request under a changed frame → compliance. Evaluate on
synthetic conversations where the re-request targets *harmless* content. The variable
under study is the reframing pattern, not the payload.

## C. Public artifact — "Threshold"

DisagreeBot-style participatory tool (DisagreeBot is a Duke TRUST Lab project). You see a
flagged conversation and choose a response tier. Then the reveal: what it was, what
everyone else chose, how your threshold compares. Over rounds it shows you your own
decision boundary — you flagged the novelist, you missed the fiction wrapper, you're two
SDs more escalation-happy than median.

Randomized arms (score-only / explanation / explanation-with-competing-reading) run the
XAI experiment at scale: do explanations change decisions, or only confidence?

Operates **only on pre-written corpus conversations**. No user free text — no privacy
surface, no stored disclosures, no chance someone types a real crisis into a class
project. That constraint is what makes it deployable by a student.

## D. Narrative site

Latent Gaze-style scrollytelling: the incidents → why turn-level moderation misses them
→ the detection asymmetry (§3) → base-rate slider → the analyzer live → the evasion
cliff → Threshold embedded → policy gap table → limitations.

---

# 7. Evaluation

| Exp | Question | Method |
|---|---|---|
| E1 | Detection | Per-construct P/R **by stratum**; FPR on hard negatives as headline. Never pooled accuracy |
| E2 | Right for the right reason | Cited evidence vs. `discriminating_features` |
| E3 | Faithfulness | Ablate cited spans, check flips; control = ablate equal count of random turns |
| E4 | Evasion | 6 transforms: paraphrase, euphemism, fiction frame, roleplay, translate-and-back, dilution |
| E5 | Refusal-sequence | Does refusal-state tracking catch reframe cases per-message misses? |
| E6 | Prompt ablation | Remove base-rate instruction / `competing_explanation` / out-of-scope list; semantically identical rubric paraphrase as control |
| E7 | Fairness | Hold behavior constant, vary AAVE, non-native phrasing, disclosed psychiatric history, disclosed disability. Does the tier move? |
| E8 | Human baseline | Crowd disagreement from Threshold; report model performance separately on high- vs low-consensus items |

Expect E3/E4 to show severe degradation. **That is the result.** A safeguard defeated by
paraphrase cannot be load-bearing — which is the argument for graduated in-product
response and refusal-state tracking over detect-and-ban.

Poster figure: recall across the six transforms, baseline as a dashed line. The cliff.

---

# 8. Repo layout

```
corpus/      TAXONOMY.md, SCHEMA.md, items.jsonl, CUTS.md, datasheet
analyzer/    prompt_v*.md, analyzer.py, refusal_state.py
eval/        PLAN.md, run_analyzer.py, metrics.py, transforms/, results/
research/    CASES.md (with source quality), POLICY_COMPARISON.md
site/        scrollytelling build
threshold/   public artifact
```

Existing files to read first: `SCOPE.md`, `corpus/TAXONOMY.md`, `corpus/SCHEMA.md`,
`analyzer/prompt_v1.md`, `eval/PLAN.md`.

---

# 9. Non-goals

- Predicting violence, or claiming to prevent it
- Any deployment recommendation beyond "surface evidence to a human reviewer"
- Clinical or psychiatric judgment of any kind
- A mosaic-aggregation corpus — the pattern is real, but that dataset would itself be a
  misuse artifact. It stays descriptive, via documented cases
- A ranked "what evasion works best" playbook. Report degradation, not recipes

---

# 10. Immediate tasks

1. `research/CASES.md` — case table with source-quality column; Roberts row first, fully
   sourced to the CPS statement and sentencing remarks
2. `corpus/items.jsonl` — 12 hard negatives, starting with three teen-venting variants
3. `analyzer/analyzer.py` — structured-output plumbing against `prompt_v1.md`
4. `eval/metrics.py` — stratum-wise metrics; refuse to emit a pooled accuracy number
5. `research/POLICY_COMPARISON.md` — OpenAI vs. Anthropic vs. Meta on violent ideation,
   escalation, human review, law-enforcement referral, read against the BC case

## Open items outside the repo

- IRB determination for Threshold crowd data — longest-lead item, start now
- Notice to Anthropic (usersafety@anthropic.com), cc professor
- Second labeler for inter-rater agreement
