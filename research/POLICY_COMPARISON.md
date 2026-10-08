# Policy Comparison: violent ideation, escalation, human review, referral

OpenAI vs. Anthropic vs. Meta, read against the Tumbler Ridge, British Columbia case
(CONTEXT.md §2.2, §4.2 items 4, 5 and 7).

**Last verified:** 2026-10-08. Policies change; re-check every quoted line before it goes
on the site or into the write-up, and update the "as of" dates.

**Source-quality legend** (same discipline as `research/CASES.md`):

| Tag | Meaning |
|---|---|
| **P** | Primary: the company's own published policy, letter, or statement; a court record |
| **S** | Secondary: established outlet reporting a primary document or on-record statement |
| **W** | Weak: paraphrase via aggregator, unverified, or text we could not load directly |

Quotes below are verbatim fragments from the linked page as fetched on 2026-10-08.
Anything we could not load verbatim is marked **W** and says so.

---

## 1. What the BC case required of a policy

Facts the comparison depends on, with sourcing. Allegations in the pending lawsuits are
allegations; nothing here has been adjudicated.

| Fact | Source | Quality |
|---|---|---|
| Shooting at Tumbler Ridge, BC, 10 Feb 2026; multiple people killed (reported counts differ between outlets) | [Incident 1375 index](https://incidentdatabase.ai/cite/1375/) aggregating Reuters, AP, Jurist | S (counts unresolved) |
| OpenAI's automated system flagged the account in June 2025 and it went to human review | [OpenAI letter to Minister Solomon, 26 Feb 2026](https://cdn.openai.com/pdf/8e938d69-0b67-4994-b9ff-683733ed587e/openai-letter-minister-solomon.pdf): "OpenAI's automated system detected the account, and it was subsequently sent to human review." | P |
| Reviewers did not refer: OpenAI "did not identify credible and imminent planning that met our threshold to refer the matter to law enforcement." The account was banned. | Same letter; [TechCrunch, 21 Feb 2026](https://techcrunch.com/2026/02/21/openai-debated-calling-police-about-suspected-canadian-shooters-chats/) | P |
| Staff "debated whether to reach out to Canadian law enforcement over the behavior but ultimately did not" | WSJ via [TechCrunch, 21 Feb 2026](https://techcrunch.com/2026/02/21/openai-debated-calling-police-about-suspected-canadian-shooters-chats/) | S |
| The perpetrator later had a second account; OpenAI shared it with police after discovering it | [OpenAI letter, 26 Feb 2026](https://cdn.openai.com/pdf/8e938d69-0b67-4994-b9ff-683733ed587e/openai-letter-minister-solomon.pdf) | P |
| OpenAI says that under its revised protocol the June 2025 account "would" be referred today | Same letter | P |
| CEO apology: "I am deeply sorry that we did not alert law enforcement to the account that was banned in June" | [TechCrunch, 25 Apr 2026](https://techcrunch.com/2026/04/25/openai-ceo-apologizes-to-tumbler-ridge-community/) quoting Altman's letter | S (quoting P) |
| Victims' families sued OpenAI and Altman in US federal court in California, 29 Apr 2026 (negligence) | [Reuters](https://www.reuters.com/world/families-canadian-mass-shooting-victims-sue-openai-ceo-altman-us-court-2026-04-29/), [NPR](https://www.npr.org/2026/04/29/nx-s1-5798896/tumbler-ridge-mass-shooting-chat-gpt-lawsuit) | S |
| BC provincial government sued OpenAI in California, announced 21 Sep 2026, alleging negligence in failing to alert police | [CTV News](https://www.ctvnews.ca/vancouver/article/bc-sues-openai-over-deadly-tumbler-ridge-mass-shooting/), [CBC](https://www.cbc.ca/news/canada/british-columbia/bc-government-announce-update-openai-legal-action-9.7352395) | S |
| BC chief coroner ordered an inquest (Mar 2026) | [Jurist](https://www.jurist.org/news/2026/03/british-columbia-chief-coroner-orders-inquest-into-tumbler-ridge-mass-shooting/) | S |

> **Correction to CONTEXT.md §2.2.** CONTEXT.md says "per Canadian court filings ... staff
> recommended alerting law enforcement; leadership declined." What we could verify is
> narrower: staff *debated* referral and the company did not refer (WSJ via TechCrunch);
> the decision was made against a "credible and imminent planning" threshold (OpenAI's own
> letter). The fuller "staff recommended police, leadership declined" account traces to
> WSJ reporting ([headline: "OpenAI Employees Raised Alarms About Canada Shooting Suspect
> Months Ago"](https://www.wsj.com/us-news/law/openai-employees-raised-alarms-about-canada-shooting-suspect-months-ago-b585df62),
> paywalled, not read directly here) and OpenAI's own statements; the lawsuits only
> repeat it as allegations. Attribute it to WSJ, never to court filings. The lawsuits were
> filed in **California**, not Canada; the Canadian proceeding is the coroner's inquest.

**The decision point.** In June 2025 a human reviewer at OpenAI had a flagged account and
two options in practice: ban, or refer to police. They banned. The person opened another
account. The test this comparison applies to each provider's published policy is:

1. **Ideation:** does the policy say what it does with conversations expressing violent
   intent toward others, as distinct from requests for help with violence?
2. **Escalation:** is there anything between "do nothing" and "ban" (graduated tiers)?
3. **Human review:** does the policy commit to a human looking before action?
4. **Referral:** what threshold triggers contacting law enforcement, and is it published?
5. **Persistence:** does a ban or a flag carry forward to a new account?

---

## 2. Side-by-side

As of 2026-10-08. "Not stated" means we did not find it in the published text linked in
§3, not that the practice does not exist internally.

| | OpenAI | Anthropic | Meta (Meta AI / Llama) |
|---|---|---|---|
| **Violent-ideation rule** | Usage policies prohibit "threats, intimidation, harassment" and "terrorism or violence" (P). No text on users *expressing* intent vs. *requesting help* | AUP: "Facilitate or promote any act of violence or intimidation targeting individuals, groups, animals, or property" (P). Constitution: the model should not "Assist someone who has clearly displayed an intention to harm others" and "could address the expressed intent to cause harm" (P) | Llama AUP: "Violence or terrorism"; "threatening, or bullying"; content "intended to incite or promote violence" (P). Community Standards cover "threats of violence that could lead to death" and "coded statements where the threat of violence is not clearly articulated" (P, via Oversight Board) — whether this standard governs private Meta AI chats is **not stated** |
| **Escalation tiers** | None published. Flags may "require[] escalation for more detailed human review" or be dismissed (P). Outcomes named: ban, refer | None published. AUP: "throttle, suspend, or terminate" access; "block or modify model outputs" (P) | None published for harm to others. Parental alerts exist for teen **self-harm/suicide** only (S, Jul 2026) |
| **Human review** | Yes: "assessed in context by trained personnel" (P); a "small team trained on our usage policies" (P, Aug 2025) | AUP describes "detection and monitoring" only (P). Privacy policy: conversations "flagged for safety review" (P). Human review before referral is reported, not published (S, Oct 2026) | Not stated for Meta AI chats |
| **Referral threshold** | Aug 2025: "imminent threat of serious physical harm to others" (P). Apr 2026: "imminent and credible risk of harm to others"; criteria made "more flexible" so target, means and timing need not be stated (P) | No referral policy for violence. Only child-safety reporting is a stated commitment (P). Privacy policy permits disclosure to "prevent serious harm to any person or to property" (P) — a permission, not a threshold | Law-enforcement guidelines cover *inbound* emergency requests ("risk of death or serious physical injury to any person") (P). No published *proactive* referral threshold for AI chats found |
| **Persistence across accounts** | Bans may extend to "other accounts of the same user" and "detect and stop the opening of new accounts" (P). Post-BC: commitment to strengthen repeat-violator detection (P) | AUP prohibits "Circumvent a ban through the use of a different account" (P) — a user obligation, not a detection commitment | Not stated for Meta AI |
| **Within-conversation memory of refusal** | Not stated | Constitution: the model may "be more wary for the remainder of the interaction" after expressed harmful intent (P) | Not stated |
| **Referral transparency** | Committed to "transparency about reports to police" in Canada (P, letter). No published counts found | Government-requests report counts inbound emergency requests; does **not** count Anthropic's own referrals (S, Oct 2026) | Publishes inbound government-request data; no AI-referral counts found |

---

## 3. Provider detail

### 3.1 OpenAI

- **Usage policies**, effective 29 Oct 2025 — <https://openai.com/policies/usage-policies/>
  (P). Prohibits "threats, intimidation, harassment, or defamation"; "terrorism or
  violence, including hate-based violence"; "weapons development, procurement, or use,
  including conventional weapons or CBRNE". The only named authority-reporting
  commitment is to NCMEC: "We report apparent child sexual abuse material and child
  endangerment". No text on fiction or creative framing.
- **"Helping people when they need it most"**, 26 Aug 2025 —
  <https://openai.com/index/helping-people-when-they-need-it-most/> (P). The policy in
  force at the BC decision point was published *after* it (June 2025 flag; August 2025
  post), so this is the closest published statement, not proof of what reviewers used:
  "When we detect users who are planning to harm others, we route their conversations to
  specialized pipelines ... reviewed by a small team trained on our usage policies ... who
  are authorized to take action, including banning accounts." "If human reviewers
  determine that a case involves an imminent threat of serious physical harm to others,
  we may refer it to law enforcement." Self-harm: "We are currently not referring
  self-harm cases to law enforcement to respect people's privacy".
- **Letter to Minister Solomon**, 26 Feb 2026, Ann M. O'Leary —
  [PDF](https://cdn.openai.com/pdf/8e938d69-0b67-4994-b9ff-683733ed587e/openai-letter-minister-solomon.pdf)
  (P). States the June 2025 threshold ("credible and imminent planning"), the revision
  (criteria "more flexible to account for the fact" that a user may not discuss target,
  means, or timing), mental-health and behavioural experts on hard cases, direct
  contacts with Canadian police, and stronger detection of repeat violators.
- **"Our commitment to community safety"**, 28 Apr 2026 —
  <https://openai.com/index/our-commitment-to-community-safety/> (P). Automated detection
  ("classifiers, reasoning models, hash-matching, blocklists"); "When an account or
  conversation is flagged, it is assessed in context by trained personnel"; "When
  conversations indicate an imminent and credible risk of harm to others, we notify law
  enforcement"; "We have a zero-tolerance policy for using our tools to assist in
  committing violence"; bans may cover "other accounts of the same user". The page does
  not mention Tumbler Ridge.

### 3.2 Anthropic

- **Usage Policy**, effective 15 Sep 2025 — <https://www.anthropic.com/legal/aup> (P).
  Violence items: "Incite, facilitate, or promote violent extremism, terrorism, or hateful
  behavior"; "Facilitate or promote any act of violence or intimidation targeting
  individuals, groups, animals, or property". Enforcement: "Anthropic's Safeguards Team
  will implement detection and monitoring to enforce our Usage Policy"; "we may throttle,
  suspend, or terminate your access". The only authority-reporting commitment is child
  safety: on CSAM or "coercion or enticement of a minor", "we will report to relevant
  authorities." Ban evasion is prohibited as user conduct.
- **Privacy policy**, effective 10 Sep 2026 — <https://www.anthropic.com/legal/privacy>
  (P). May share personal data with law enforcement "in response to an enforceable
  governmental request" or to "prevent serious harm to any person or to property".
  Conversations may be "flagged for safety review". No published criteria for when a
  flag becomes a referral.
- **Anthropic's model constitution**, published Jan 2026 (date not shown on page) —
  <https://www.anthropic.com/constitution> (P). Model-behavior norms, not enforcement:
  "Always refer users to relevant emergency services" where life is at risk; the model should
  not "Assist someone who has clearly displayed an intention to harm others"; after
  expressed intent it may "be more wary for the remainder of the interaction"; creative
  work has value but some use it "as a shield".
- **Practice, reported not published** (S). [Tom's Hardware, 5 Oct
  2026](https://www.tomshardware.com/tech-industry/artificial-intelligence/anthropic-reports-florida-womans-claude-diary-threat-to-shoot-up-sheriffs-office-felony-charge-follows-its-at-least-the-third-such-conversation-to-reach-police-since-august),
  citing a Lee County arrest report via WINK News: Anthropic's monitoring flagged a
  conversation, its human review team reported it, and a felony threat charge followed.
  The same article lists other Anthropic chatbot conversations reaching police since August 2026.
  Anthropic has not commented on the record. Treat as **S**; the arrest report is the
  primary source to pull.

### 3.3 Meta

Meta is the weakest-sourced column because its policy pages are rendered client-side and
did not load as text. Every Meta row should be re-read in a browser before citing.

- **Llama 3 Acceptable Use Policy** (no date or version on page) —
  <https://www.llama.com/llama3/use-policy/> (P). Prohibits "Violence or terrorism";
  "harassment, abuse, threatening, or bullying"; "Any content intended to incite or
  promote violence, abuse, or any infliction of bodily harm to an individual". The only
  mechanism is reporting violations to Meta (`LlamaUseReport@meta.com`). This governs
  developers using open weights; Meta has no visibility into those deployments, which is
  critique 7 in its strongest form.
- **Community Standards: Violence and Incitement** —
  <https://transparency.meta.com/policies/community-standards/violence-incitement/>.
  Could not load verbatim (**W**). Fragments verified via the Oversight Board's
  [Rhetorical Threats Against Authorities decision, 29 Jan
  2026](https://www.oversightboard.com/?p=53276) (P): covers "threats of violence that
  could lead to death" and "serious injury"; "coded statements where the threat of
  violence is not clearly articulated, but the threat is veiled or implicit"; Meta tries to
  "consider the language and context in order to distinguish casual or awareness-raising
  statements". This is a *content-on-platform* standard. We found no Meta text saying it
  applies to one-to-one Meta AI conversations. Older versions of this page said Meta works
  with law enforcement where there is "a genuine risk of physical harm"; we could not
  confirm that wording on the current page (**W**, do not quote until verified).
- **Information for law enforcement** — <https://www.meta.com/safety/communities/law/guidelines/>
  (P). Emergency requests from police "involving imminent harm to a child or risk of death
  or serious physical injury to any person". This is the inbound channel; it is not a
  proactive referral policy.
- **Teen AI safety alerts**, July 2026 (S, [KWTX/Gray](https://www.kwtx.com/2026/07/16/meta-releases-new-protection-that-alerts-parents-teens-showing-signs-distress-conversations-with-ai/)).
  Parents using Instagram supervision are alerted when a teen discusses self-harm or
  suicide with Meta AI. Nothing equivalent for violence toward others. The same article
  reports 19,000+ referrals to first responders for wellness checks in the prior year; it
  is unclear whether any of these relate to AI chats (**W**).

---

## 4. Read against BC

What each published policy, as written today, says a reviewer should do with the June
2025 account. This is a reading of the text, not a claim about what any company's staff
would actually have done.

| Question | OpenAI | Anthropic | Meta |
|---|---|---|---|
| Is there a written referral threshold a reviewer could apply? | Yes, and it moved: "credible and imminent planning" (2025) → "imminent and credible risk", with target/means/timing no longer required (2026) | No. A legal permission to disclose, no criteria | No proactive threshold for AI chats found |
| Is there an option between ban and referral? | No | No | No |
| Would a ban follow the user to a new account? | Stated aim to detect new accounts | User is forbidden to evade; no stated detection | Not stated |
| Does refusal or a flag change later model behavior? | Not stated | Within one conversation only ("more wary for the remainder of the interaction") | Not stated |
| Would anyone outside the provider see the pattern? | Only via referral | Only via referral | Only via referral |

**What this supports.**

- **Critique 4 (no referral ladder) holds for all three.** No provider publishes anything
  between "do nothing" and "ban or refer". OpenAI's post-BC changes moved the referral
  threshold; they did not add a rung. The analyzer's graduated tier
  (`none`/`resource`/`friction`/`review`/`escalate`) has no published counterpart.
- **Critique 5 (policy asymmetry) is visible on the page.** OpenAI names CBRNE and
  conventional weapons development in the same sentence and commits to mandatory NCMEC
  reporting; violence toward a person gets a two-word item. Anthropic's AUP has one
  authority-reporting commitment, for child safety. Meta's only AI-chat escalation is for
  self-harm. Interpersonal violence is the least-specified category at all three.
- **Critique 7 (portable users) holds and has a concrete instance.** The BC perpetrator
  opened a second account after the ban (OpenAI's own letter). Only OpenAI publishes a
  commitment to detect that. None addresses a user moving to a different provider, and
  Llama's open weights put most deployments outside Meta's view entirely.

**Where CONTEXT.md overstates, and the project should say so.**

- **"Nothing tracks trajectories" is too strong as of 2026.** OpenAI's revised criteria
  ("a user may not discuss target, means, or timing") are explicitly a judgment about the
  pattern rather than one message, made at the human-review stage. Anthropic's
  constitution tells the model to stay wary after expressed intent, which is a
  within-conversation carry-forward of exactly the kind §4.3 proposes. The defensible
  claim is narrower: *refusals are not recorded as state that persists across sessions or
  accounts, and no provider publishes whether they are an input to review.* That is still
  the gap RQ4 tests.
- **The fix the public demanded points the wrong way for our FP concern.** Every post-BC
  change at OpenAI widens referral ("more flexible", no named target needed). A looser
  referral bar applied to the population that actually talks to chatbots means more police
  contact for venting teenagers, novelists and clinicians. No provider publishes referral
  volume, precision, or outcomes. This is the strongest argument for the project's
  graduated tiers: the policy debate after BC has only one dial, and turning it is costly
  for the innocent. The write-up should make this point without implying that referral
  in BC would have prevented the shooting; no source establishes that, and the lawsuits'
  claim that it would have is an allegation.

---

## 5. Open verification items

- [ ] Read the families' complaint (US District Court, California, filed 29 Apr 2026) and
      the BC government's complaint (Sep 2026) directly; replace S rows in §1 with P where
      possible. Resolve the "staff recommended / leadership declined" wording.
- [ ] Resolve the casualty count from the coroner or RCMP; coordinate with whoever owns
      `research/CASES.md`.
- [ ] Load Meta's Violence and Incitement page in a browser; quote the rationale and any
      law-enforcement sentence verbatim, with its "last updated" date.
- [ ] Find whether any Meta document states that Community Standards apply to Meta AI
      one-to-one chats.
- [ ] Pull the Lee County arrest report for the Anthropic referral case (currently S via
      WINK News / Tom's Hardware).
- [ ] Check whether Anthropic publishes any statement on violence referrals after Oct 2026.
- [ ] Archive every linked policy page (e.g. Wayback) with the fetch date; these pages are
      revised without notice and the BC timeline depends on which version was live when.
