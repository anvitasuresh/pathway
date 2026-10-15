# Case Table

Source-quality column is mandatory. The site and write-up render only rows marked
**site-ready** (CONTEXT.md §2.3). Last verified: 2026-10-08.

Rules for this file:

- Cases are cited in prose with sources. Nothing here is corpus data.
- No operational detail. Where a source describes what was asked or answered, this file
  records the *category* of request (e.g. "weapon comparison"), never the content of an
  answer.
- Anyone not convicted is "accused" and every claim about them is an allegation.
- Minors and uncharged people are not named.

## Source-quality scale

| Grade | Meaning |
|---|---|
| **A** | Court judgment, published sentencing remarks, or an official prosecutor / court statement that states the AI-related fact itself |
| **B** | Statement made in open court or by an official (prosecutor, police, DA), reported by an established outlet; or an official document that establishes the case facts but not the AI-related fact |
| **C** | Investigative reporting by an established outlet, company statements, or civil pleadings (unproven allegations) |
| **D** | Single secondary source, aggregator, social media, or Wikipedia only |

Grades are given per claim, because the case facts and the AI-related facts are often
sourced very differently.

## Summary

| # | Case | Date | Outcome | Case facts | AI-related claim | Site-ready? |
|---|---|---|---|---|---|---|
| 1 | R v. Tristan Roberts (Prestatyn, Wales) | offence 24 Oct 2025; sentenced 25 Mar 2026 | Convicted (guilty plea), life | **A** | **B** (prosecution in open court; not in the judgment or CPS statement) | Yes, with the wording in §1 |
| 2 | FSU shooting (Tallahassee, FL) | 17 Apr 2025 | Accused awaiting trial | **B** | **B/C** (State Attorney records, reported) | Yes, as allegations |
| 3 | Tumbler Ridge school shooting (British Columbia) | 10 Feb 2026 | Shooter died; civil suits pending | **B** | **C** (WSJ reporting, OpenAI statements, civil pleadings) | Yes, as reported and alleged |
| 4 | Acton, MA double homicide | Aug 2026 | Minor accused, indicted, pending | **B** | **B** (DA press conference) | Only with §4 caveats |
| 5 | Pirkkala school stabbing (Finland) | 20 May 2025 | Convicted of 3 attempted murders; not criminally responsible | **A/B** | **B** (prosecutor in court, Yle) | Yes |
| 6 | Gangbuk motel killings (Seoul) | Jan–Feb 2026 | Convicted, life; under appeal | **A/B** | **A/B** (indictment and ruling, reported) | Yes |
| 7 | Adams / Soelberg (Greenwich, CT) | Aug 2025 | Murder-suicide; civil suit pending | **B** | **C** (civil complaint, unproven) | Yes, as alleged |
| 8 | Hamilton County, TN (Darron Lee) | 5 Feb 2026 | Accused awaiting trial (Sept 2027) | **B** | **B** (detective testimony at preliminary hearing, reported) | Yes, as allegations; post-incident use |

## Corrections to CONTEXT.md §2.1–2.2

Research turned up several places where the working notes outrun or misstate the sources.
These should be fixed in CONTEXT.md and anywhere they have been copied.

1. **Roberts: "a court said so" overclaims.** Neither the published sentencing remarks
   nor the CPS statement mentions DeepSeek, AI, the refusal, or the book framing. The
   refuse → reframe → answer sequence comes from prosecutor Andrew Thomas KC in open
   court, as reported by the press. Roberts pleaded guilty, so it was not contested at
   trial, but the judge made no finding on it. Write "the prosecution told the court",
   not "a court found".
2. **Roberts minimum term** is 22 years 6 months *less 148 days on remand*, i.e.
   22 years 34 days still to serve (sentencing remarks).
3. **Roberts "Tonight's the night"**: BBC reports it as his status on the night;
   Radio News Hub reports a Discord username set up the week before. Cite whichever
   source is used, don't merge them.
4. **BC is the Tumbler Ridge shooting.** "Per Canadian court filings" is too strong.
   The internal-debate account comes from Wall Street Journal reporting (Feb 2026) and
   OpenAI's own statements; court filings (BC Supreme Court, March 2026; California
   suits including the Province's, Sept 2026) repeat it as allegations. "Staff
   recommended alerting police; leadership declined" should read "some employees
   reportedly wanted to contact police; the company decided the activity did not meet
   its imminent-threat threshold".
5. **Finland is Pirkkala, May 2025, not 2024.** The "hundreds of searches" figure is
   Yle's report of AI-assisted searches; the prosecutor confirmed AI use in court
   without a count.
6. **Seoul is much better sourced than §2.2 says, and is not an overdose case.** It is
   a deliberate drugging case with two men killed; the indictment and the trial court's
   ruling both cite the ChatGPT queries. Upgrade from "weak".

---

## 1. R v. Tristan Roberts — Mold Crown Court

**Facts (A).** Roberts, 18, murdered his mother Angela Shellis, 45, a teacher with
limited mobility. The attack began at their home in Prestatyn on the evening of
23 Oct 2025; she was killed in the early hours of 24 Oct 2025 at Coed y Morfa nature
reserve. Guilty plea 5 Feb 2026. Sentenced 25 Mar 2026 by HHJ Rowlands: custody for
life, minimum term 22 years 6 months less 148 days on remand. The judge found
significant planning over several weeks, including internet research and purchases,
and that Roberts posted on Discord that he intended to kill his mother and later
boasted of it. Psychiatric evidence found no abnormality of mental functioning at the
time.

**Planning research (A, without the AI attribution).** The CPS states that digital
evidence from his laptop showed planning and research on removing blood and DNA
traces. The CPS does not say which tool he used.

**AI-related claim (B).** Per prosecutor Andrew Thomas KC in court, as reported on
25 Mar 2026: Roberts asked DeepSeek which of two weapons was better; it refused; he
asked again after saying he was writing a book about serial killers and received
answers. He also asked it about cleaning up blood. *Pathway records only the sequence
(request → refusal → fiction reframe → answer), never the content of the answer.*

**Cross-platform warning behaviour (A/B).** Judge: Discord posts stating intent and
motive. BBC: removed from Discord several times for code-of-conduct violations and
returned under 16 aliases in total.

**How he was identified (B, BBC).** A neighbour's Ring doorbell footage showing him
leading his mother from the house at 03:19; a blood trail over 100 m at the reserve; a
dictaphone recording he made of the attack (also referenced by the judge). Arrested at
home around 13:25. The AI queries are laptop-forensics evidence, not how he was found.

Sources:
- Sentencing remarks, R v Tristan Roberts, Mold Crown Court, 25 Mar 2026 —
  https://www.judiciary.uk/wp-content/uploads/2026/03/2026-March-Mold-ROBERTS-Murder-Sent.pdf
- CPS Cymru Wales, "Man sentenced for murdering his mother", 25 Mar 2026 —
  https://www.cps.gov.uk/cymruwales/news/man-sentenced-murdering-his-mother
- Radio News Hub, "Teenager who recorded fatal hammer attack on mother jailed for
  murder", 25 Mar 2026 (prosecutor's DeepSeek account) —
  https://www.radionewshub.com/articles/news-updates/Teenager-who-recorded-fatal-hammer-attack-on-mother-jailed-for-murder
- BBC Wales (Telor Iwan, Sarah Easedale), syndicated via AOL (Discord, doorbell, arrest) —
  https://www.aol.com/articles/serial-killer-obsessed-teen-posted-124418385.html
- LBC (CCTV time, prosecutor) — https://www.lbc.co.uk/crime/teen-jailed-life-murdering-mother/

TODO: find the BBC original URL (only the AOL syndication was reachable) and a second
outlet carrying the prosecutor's DeepSeek account verbatim.

## 2. Florida State University shooting — Tallahassee, FL

**Facts (B).** 17 Apr 2025, at the FSU student union. Two killed, several wounded. The
accused, a student, is charged with murder and awaiting trial (trial dates have moved
several times through 2026). **Not convicted; everything below is allegation.**

**AI-related claim (B/C).** Thousands of records released by the Leon County State
Attorney's Office, including the accused's ChatGPT history, were reviewed by local
press in April 2026. Reported content includes questions about how much media
attention a campus shooting would draw, crowd timing at the student union, and
weapon-related questions shortly before the shooting. On 21 Apr 2026 Florida's
Attorney General announced a criminal investigation into whether OpenAI is liable.

This is the closest documented example of the **mosaic** pattern (individually
innocuous questions), but that label is our interpretation, not the prosecution's.
Per CONTEXT.md §9 Pathway does not build a mosaic corpus.

Sources:
- WTXL, "ChatGPT records give insight into mind of alleged gunman…", 8 Apr 2026 —
  https://www.wtxl.com/college-town/fsu-shooting/chatgpt-records-give-insight-into-mind-of-alleged-gunman-leading-up-to-florida-state-shooting
- Florida Phoenix, "Uthmeier investigating whether ChatGPT is criminally liable…",
  21 Apr 2026 — https://floridaphoenix.com/2026/04/21/uthmeier-investigating-whether-chatgpt-is-criminally-liable-for-fsu-shooting/
- CNN, 21 Apr 2026 —
  https://www.cnn.com/2026/04/21/tech/florida-criminal-investigation-chatgpt-openai-fsu-shooting
- WTXL, jury selection scheduling —
  https://www.wtxl.com/downtown-tallahassee/fsu-shooting-trial-jury-selection-set-for-october-as-case-moves-forward

TODO: link the State Attorney's records release directly; recheck trial status before
publishing.

## 3. Tumbler Ridge school shooting — British Columbia

**Facts (B).** 10 Feb 2026, Tumbler Ridge Secondary School. Five students and a
teacher were killed at the school, plus the shooter's mother and half-brother; the
shooter, a teenager, died by suicide. No criminal case against the shooter.

**AI-related claim (C).**
- OpenAI flagged and banned one of the shooter's accounts in June 2025 after an
  automated review surfaced violent scenarios over multiple days. About a dozen
  employees reportedly knew; some reportedly wanted to contact police. The company
  decided it did not meet its imminent-threat threshold for referral (WSJ, Feb 2026,
  as relayed by Fox/AOL; OpenAI statement).
- OpenAI later disclosed a second account that was not detected.
- 26 Feb 2026: OpenAI's VP of global policy wrote to Canada's AI minister that "under
  our enhanced law enforcement referral protocol, we would refer the account banned in
  June 2025 to law enforcement if it were discovered today" (AFP).
- 23 Apr 2026: Sam Altman's letter to Tumbler Ridge: "I am deeply sorry that we did not
  alert law enforcement to the account that was banned in June."
- Civil suits: a claim in BC Supreme Court (Mar 2026); family suits in California
  (30 more reported Sept 2026); the Province of British Columbia sued in California
  (Sept 2026). All are unproven pleadings.

What this case establishes for Pathway: detection happened; the only options exercised
were ban or nothing. OpenAI's own statements are the strongest sources for that.

Sources:
- AFP via Malay Mail, 27 Feb 2026 —
  https://malaymail.com/news/world/2026/02/27/openai-says-it-would-now-alert-police-over-potential-threats-after-canada-mass-shooting/210587
- Fox News via AOL, relaying WSJ, 21 Feb 2026 —
  https://www.aol.com/articles/openai-didnt-contact-police-despite-140233410.html
- The Next Web, Altman apology —
  https://thenextweb.com/news/sam-altman-openai-apology-tumbler-ridge-shooting
- Insurance Journal (Reuters), BC sues OpenAI, 22 Sept 2026 —
  https://www.insurancejournal.com/news/international/2026/09/22/886361.htm
- TechCrunch, 30 more lawsuits, 2 Sept 2026 —
  https://techcrunch.com/2026/09/02/openai-faces-30-more-lawsuits-tied-to-tumbler-ridge-shooting/
- Mother Jones investigation, Sept 2026 (not yet reviewed) —
  https://www.motherjones.com/media/2026/09/chatgpt-tumbler-ridge-mass-shooter-openai/

TODO: get the WSJ original and the BC Supreme Court notice of civil claim; quote
OpenAI's letter from the primary if published.

## 4. Acton, MA double homicide — HANDLE CAREFULLY

**Facts (B).** Mid-Aug 2026. A 17-year-old is charged with murdering his mother and
14-year-old brother at their home; indicted by a Middlesex County grand jury (reported
3 Oct 2026). **Minor, presumed innocent, case pending. Do not name him.**

**AI-related claim (B).** Middlesex DA Marian Ryan said at a press conference that he
used the internet and ChatGPT for "theoretical ideas or fantasy stories regarding the
killing of his family", describing them as "gothic novel kind of stories". **The DA has
not alleged that the model supplied a plan, method, or instructions**, and cause of
death was pending the medical examiner at the time.

Use only for the `CONV` (reality convergence) construct, and only as "the DA described…".
Do not present it as a fiction-wrapper success.

Sources:
- WBUR, 12 Aug 2026 — https://www.wbur.org/news/2026/08/12/teen-found-acton-deaths-home
- CBS Boston — https://www.cbsnews.com/boston/news/acton-death-investigation-martha-lane/
- Hoodline (relaying WCVB), indictment, 3 Oct 2026 —
  https://hoodline.com/2026/10/acton-teen-indicted-in-mother-and-brother-s-deaths-after-chatgpt-fantasy-searches/

TODO: replace Hoodline with WCVB or a DA press release.

## 5. Pirkkala school stabbing — Finland

**Facts (A/B).** 20 May 2025, Vähäjärvi School, Pirkkala. A 16-year-old injured three
15-year-old girls. Pirkanmaa District Court convicted him of three attempted murders
(Dec 2025); a psychiatric evaluation found him not criminally responsible, so he
received no criminal sentence and was ordered into involuntary psychiatric care. Minor:
not named.

**AI-related claim (B).** The prosecutor told the court he began planning the previous
November and used AI to look up information, including on school killings (MTV Uutiset,
19 Dec 2025). Yle reports "Poika teki ennen tekoaan tekoälyn avulla satoja hakuja"
("before the act, the boy made hundreds of searches with the help of AI"). No source
names the AI tool. An earlier claim that ChatGPT helped write his manifesto (GNET) is
unconfirmed. He also published a manifesto announcing the attack — `LEAK`.

Sources:
- Yle, verdict, 31 Dec 2025 — https://yle.fi/a/74-20201746
- MTV Uutiset, trial opening, 19 Dec 2025 —
  https://www.mtvuutiset.fi/artikkeli/16-vuotiasta-poikaa-syytetaan-kolmesta-murhan-yrityksesta-pirkkalan-koulupuukotuksessa-karajakasittely-alkoi/9272414
- Yle, psychiatric evaluation order, 12 Aug 2025 — https://yle.fi/a/74-20177101
- GNET, 12 Jun 2025 (analysis; AI role "plausible, though not confirmed") —
  https://gnet-research.org/2025/06/12/prompted-to-harm-analysing-the-pirkkala-school-stabbing-and-its-digital-manifesto/

TODO: get the judgment from Pirkanmaan käräjäoikeus if it is public (juvenile cases may
be restricted).

## 6. Gangbuk motel killings — Seoul

**Facts (A/B).** Jan–Feb 2026. A woman in her early 20s gave men drinks laced with
prescription sedatives; two men died at motels in Gangbuk-gu and others were injured.
Indicted 10 Mar 2026 by the Seoul Northern District Prosecutors' Office on murder,
aggravated injury and narcotics charges. Seoul Northern District Court sentenced her to
life on 27 Aug 2026, rejecting a self-defence claim; both sides have appealed.

**AI-related claim (A/B).** Police (Feb 2026), the indictment (Mar 2026) and the
ruling all cite her ChatGPT questions about whether the drug combination could be
fatal. The court reportedly treated those questions, with the repeated offences, as
evidence she recognised the possibility of death. That makes this the only case in the
table where a court relied on the AI queries for a finding (intent).

Not an "overdose" case and not a self-harm case; the victims were drugged.

Sources:
- Korea Herald (police), 19 Feb 2026 — https://www.koreaherald.com/article/10678557
- Kyunghyang Shinmun (indictment), 18 Mar 2026 — https://www.khan.co.kr/en/article/202603181700007
- Korea JoongAng Daily (verdict) —
  https://www.koreajoongangdaily.com/korea/motel-killer-gets-life-sentence-as-court-rejects-claim-of-selfdefense-against-sexual-assault/12847811
- Seoul Economic Daily (ruling details), 9 Sept 2026 —
  https://en.sedaily.com/society/2026/09/09/court-ruling-details-motel-drug-killings-that-drew-life
- SBS (prosecution appeal) — https://news.sbs.co.kr/english/article.do?news_id=N1008734254

TODO: recheck appeal outcome before publishing.

## 7. Adams / Soelberg murder-suicide — Greenwich, CT

**Facts (B).** Early Aug 2025. Police said Stein-Erik Soelberg, 56, killed his mother,
Suzanne Adams, 83, at their home and then himself.

**AI-related claim (C).** Civil complaint by Adams's estate, filed Dec 2025 in San
Francisco Superior Court against OpenAI, Microsoft, Sam Altman and others. It alleges
ChatGPT (GPT-4o) affirmed his persecutory beliefs (that his mother was surveilling him,
that a printer was a surveillance device, that he was being poisoned through his car's
vents), never suggested professional help, and did not decline delusional content.
**Allegations only.** The public chats (his own YouTube videos) reportedly do not show
conversations about killing his mother; the estate says it lacks the full history.
OpenAI did not address the merits. Wikipedia is not a source for this case.

**Why it matters here.** A different mechanism from Roberts: no refusal and no reframe,
but validation accumulating across a long conversation. Same unit-of-analysis argument;
motivates E10 (sycophancy drift).

Sources:
- WBUR / AP, 11 Dec 2025 — https://www.wbur.org/news/2025/12/11/open-ai-chatgpt-lawsuit-connecticut-murder-suicide/
- Boston Globe, 11 Dec 2025 — https://www.bostonglobe.com/2025/12/11/business/openai-microsoft-chatgpt-wrongful-death-lawsuit/

TODO: get the complaint itself (case number) and replace the press citations.

## 8. Hamilton County, TN (Darron Lee) — post-incident use

**Facts (B).** Gabriella Perpétuo, 29, found unresponsive at her Ooltewah home on
5 Feb 2026 and pronounced dead. Darron Lee, a former NFL player, is charged with her
murder; bound over to the grand jury at a 9 Mar 2026 preliminary hearing; trial set for
27 Sept 2027. **Presumed innocent, case pending.**

**AI-related claim (B).** A Hamilton County Sheriff's detective testified at the
preliminary hearing that Lee messaged ChatGPT ("she isn't waking up or responding, what
do I do?") about a day before officers were called; the DA argued he used it to help
cover up the death. No confession in the messages.

**Fit.** Post-incident use, not warning behaviour before harm. Out of scope for the
analyzer's constructs; cite only as a contrast (the per-message duty to direct someone
to emergency help).

Sources:
- Local 3 News — https://www.local3news.com/local-news/update-ex-nfl-player-charged-with-murder-of-girlfriend-given-trial-date-in-2027/article_515b5c92-0423-493d-aa89-a419a755d3f7.html
- NewsChannel 9 (preliminary hearing) — https://newschannel9.com/news/local/body-camera-footage-shown-at-preliminary-hearing-for-former-nfl-player-charged-with-murder-darron-lee-preliminary-hearing-ooltewah-homicide-update-gabriella-carvalho-perpetuo-case-former-nfl-player-murder-charge-hamilton-county-courtroom
