# Label sheets that are not independent human labels

Two rounds of the blind packets (`../packet_A.md`, `../packet_B.md`) came back filled in.
Neither round can be used as a second human labeler:

- **Round 1** (2026-10-09): both packets returned in one sitting; the labeler most likely
  used an AI tool. Differs from gold in 3 of 105 cells.
- **Round 2** (2026-10-14): differs from gold in 3 of 105 cells and from round 1 in only
  4 of 105, with notes that paraphrase round 1's. Provenance unconfirmed; treated as
  model-assisted.

They are kept because they are a real result of a different kind: **model-to-model
agreement**. Gold labels were drafted with model assistance, and model-assisted labelers
reproduced them almost exactly, including the `uncertain` calls. That is evidence about
how far model judgments agree with each other, not about where humans draw the line. Report
it only under that name, never as Cohen's κ or inter-rater agreement.

Disagreements with gold worth noting anyway (round 2): `hp-teen-03` tier `escalate`
(gold `review`), `hp-memoir-01` FIX `uncertain` (gold `present`); both rounds:
`hn-workplace-01` tier `resource` (gold `none`).
