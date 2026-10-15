# E11: Policy texts coded clause by clause

OpenAI, Anthropic and Meta, coded for how each published text handles conversation-level
risk, refusal memory, graduated responses, referral criteria and referral accuracy.
Desk work, no API calls. Builds on `research/POLICY_COMPARISON.md` (2026-10-08).

**Accessed:** 2026-10-14. Data: `eval/e11/policy_codes.csv` (one row per provider ×
dimension, with the evidence quote, URL, document date and source quality) and
`eval/e11/policy_items.csv` (prohibited-use items in five harm areas). Counts:
`python eval/e11/count.py`.

**What a code means.** Every code describes the *published text*. "Not stated" means we
did not find it in the documents below; it is not a claim about internal practice.
Nothing here says what any company's reviewers actually do.

## Sources and quality

| Provider | Document | Date on page | URL | Quality |
|---|---|---|---|---|
| Anthropic | Usage Policy | effective 12 Nov 2026 (live page, not yet in force on access date) | <https://www.anthropic.com/legal/aup> | P, full text read |
| Anthropic | Usage Policy, previous version | effective 15 Sep 2025 | [archive](https://www.anthropic.com/legal/archive/22742366-2ef0-4c7a-a833-6523f10d3944) | P, full text read |
| Anthropic | Constitution | Jan 2026 | <https://www.anthropic.com/constitution> | P, full text read |
| Anthropic | Privacy Policy | effective 10 Sep 2026 | <https://www.anthropic.com/legal/privacy> | P, full text read |
| Anthropic | Crisis Helpline Support (help centre) | 16 Mar 2026 | [support article](https://support.claude.com/en/articles/13171706-crisis-helpline-support-in-claude) | P, full text read |
| OpenAI | Usage Policies | effective 29 Oct 2025 | <https://openai.com/policies/usage-policies/> | P (extract) |
| OpenAI | "Our commitment to community safety" | 28 Apr 2026 | <https://openai.com/index/our-commitment-to-community-safety/> | P (extract) |
| OpenAI | "Helping people when they need it most" | 26 Aug 2025 | <https://openai.com/index/helping-people-when-they-need-it-most/> | P (extract) |
| Meta | Llama 3 Acceptable Use Policy | undated | <https://dev.meta.ai/llama/llama3/use-policy> (redirect from llama.com) | P (extract) |
| Meta | Meta AI consumer terms | — | not retrieved | gap |

**P (extract)** means a primary page that blocked direct download from our environment;
text was read through a fetch tool that returns quotes of at most ~125 characters.
Quotes marked this way are exact fragments, but re-read the page in a browser before a
quote goes into the write-up. Anthropic pages were downloaded and read in full.

**Meta is still the weakest column.** We could not retrieve the consumer Meta AI terms,
so the Meta column codes the Llama AUP, which governs developers using open weights, not
people chatting with Meta AI. Meta rows from the law-enforcement guidelines and the teen
alert are carried over from POLICY_COMPARISON.md, not re-fetched.

## Codebook and results

| Dimension | OpenAI | Anthropic | Meta (Llama AUP) |
|---|---|---|---|
| D1 Unit of detection named in text | **Across conversations, claimed**: "a broader pattern within a long conversation—or across conversations—can suggest something more concerning" (Apr 2026) | Not stated ("detection and monitoring") | Not stated |
| D2 Refusal or expressed intent changes later model behaviour | Aspiration only, self-harm example: "researching ways to ensure robust behavior across multiple conversations" (Aug 2025) | **Within one conversation**: "more wary for the remainder of the interaction, even if the person claims to be joking" (constitution) | Not stated |
| D3 Refusal or block as an enforcement signal | Not stated. Models are trained to refuse; nothing on what a refusal feeds | **Explicitly not by itself**: "encountering a block does not by itself indicate a violation" (AUP, Nov 2026) | Not stated |
| D4 Named enforcement steps | Revoke access, ban other accounts of the same user, block new accounts; "other penalties" unnamed | **Warn**, throttle, limit, suspend, terminate (Nov 2026). The Sep 2025 version had no "warn" or "limit", and said "If we learn" where the new text says "If we suspect" | None |
| D5 A rung between ban and referral, for harm to others | **Undefined**: "in some sensitive cases, we may contact others who are best positioned to help" (who, when, on what criteria not stated) | No. Warn and throttle are generic AUP steps with no risk-to-others criteria | No |
| D6 Referral criteria, harm to others | **Published threshold**: "imminent and credible risk of harm to others"; criteria "flexible" so target, means and timing need not be stated (blog post, not the usage policy) | **Permission only**: may disclose to "prevent serious harm to any person or to property" (privacy policy) | Inbound police requests only |
| D7 Referral volume or accuracy published | No | No | No |
| D8 Ban follows the person to a new account | **Detection commitment** | User obligation only ("Circumvent a ban ... different account" is prohibited) | Not stated |
| D9 Human review before action | Yes: "assessed in context by trained personnel" | Not stated in policy; privacy policy mentions conversations "flagged for safety review" | Not stated |
| D10 Mandatory reporting, by harm area | Child safety in the usage policy (NCMEC); violence referral only in blog posts | Child safety only | None |
| D11 Resource tier, separate from enforcement | Crisis resources; teen parent alert in "rare cases" | Crisis banner for self-harm; "no consequences for your account"; suppressed for about two hours after shown | Teen self-harm parent alert (S, reported) |

## Prohibited-use items per harm area

`python eval/e11/count.py`:

| Harm area | OpenAI | Anthropic | Meta |
|---|---|---|---|
| violence_to_persons | 1 | 4 | 2 |
| extremism_terrorism | 1 | 2 | 1 |
| weapons | 1 | 6 | 2 |
| child_safety | 8 | 6 | 2 |
| self_harm | 1 | 3 | 1 |

Anthropic's violence row counts the violence-or-intimidation item, two harassment items
and the glorifying-graphic-violence item. Meta's 2.e ("Self-harm or harm to others") is
coded as self-harm but names both. Counts compare within a document only: OpenAI writes
one noun phrase per area where Anthropic writes several verb clauses.

## What this supports, and what it does not

1. **Critique 5 (policy asymmetry) holds for enforcement, not for prohibitions.** By item
   count, violence to persons is not the least specified area: OpenAI gives weapons and
   threats one item each, Meta two each, Anthropic 6 to 4. The asymmetry that survives
   coding is in what the company commits to *do*: child safety has a mandatory-report
   commitment in OpenAI's and Anthropic's policies; violence to others has none in any
   policy text. OpenAI's referral threshold lives in blog posts and a letter, not in its
   usage policy. Restate critique 5 as an enforcement asymmetry, and drop "violence gets
   a two-word item" from POLICY_COMPARISON §4.

2. **"No deployed conversation-level system" overstates.** OpenAI publicly claims its
   review considers patterns "within a long conversation—or across conversations". What
   no provider publishes is how that works, what it is measured against, or how often it
   is wrong. Defensible: *conversation-level review is claimed by one provider and
   described by none.*

3. **Refusal memory: the calibrated claim still stands, sharpened.** Only Anthropic says
   anything about carrying a refusal forward in the model, and only within one
   interaction. Only Anthropic says anything about blocks and enforcement, and what it
   says is that a block is not by itself a violation. No provider states that a refusal
   is stored as state that persists across sessions or accounts or that feeds review.
   Say "no provider publishes that refusals persist", not "refusals are discarded"; the
   second is a claim about practice we cannot see.

4. **Graduated options: narrower than CONTEXT.md said.** Graduated *account* enforcement
   now exists in text: Anthropic's Nov 2026 AUP adds "warn" and "limit". Graduated
   *resource* responses exist for self-harm at all three. What is still missing
   everywhere is a published rung between ban and police referral for risk to others,
   with criteria. OpenAI's "contact others who are best positioned to help" is the
   closest thing, and it is undefined. For the write-up: the analyzer's
   `friction`/`review` tiers are the rung no provider describes.

5. **Referral accuracy: holds for all three.** No provider publishes referral counts,
   precision, or outcomes. OpenAI's post-BC changes loosened the referral criteria
   ("flexible") with no published way to see the false-positive cost. This is the
   strongest single finding for the project's FP-first framing.

## Limits

- Text only. Policies describe intent; practice may be stricter or looser.
- One coder (the author); no agreement measured. Most codes are presence/absence of
  quoted text, which a reader can check against the CSV.
- Anthropic's live AUP is dated after the access date (effective 12 Nov 2026). Both the
  new and previous versions are coded so either can be cited.
- Policy pages change without notice. Archive every URL (e.g. Wayback) before citing.
