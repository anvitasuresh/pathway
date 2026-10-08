# Cuts

Log of corpus items removed or rejected, and why (e.g. too operational, insufficiently
distinct hard negative, source quality too weak). Keeps the exclusion rationale visible
instead of silently dropping items.

Each review pass asks one question of every item: **does this teach anything?** If yes,
the item or passage is cut and logged here.

## Batch 1: hard negatives `hn-*` (2026-10-08)

**Second pass ("does this teach anything?") on all 12 items: no items cut.** No item
contains a method, means, acquisition, timing, location, or sequence that works as
instruction. Every violent-sounding passage is an idiom, a wish with no agency, or a
secondhand reference with no mechanics.

Content kept out while drafting. These are not cuts of existing text, but they are logged
because they are the same judgment made earlier:

| Item | Excluded | Why |
|---|---|---|
| `hn-nurse-01` | Clinical detail of the patient's injuries | Adds nothing to any construct; the anger and gallows humor carry the item |
| `hn-truecrime-01` | Any reconstruction of how the fictional disappearance happened | The trap is research depth and focus on a named person, not crime facts |
| `hn-defense-01` | Mechanics of the assault in the client's case | "A fight that went badly" is enough; the trap is the idiom toward the prosecutor |
| `hn-grief-01` | Any approach behavior toward the offender (e.g. driving past his house) | That would move the item toward a positive and stop it being a clean negative |
| `hn-teen-03` | An explicit walk-back of turn 0 ("not literally") | Makes the negative too easy; the signal should be the trajectory, not a disclaimer |
| `hn-teen-03` | Disclosure of physical abuse by the stepparent | Would change the correct response (safety of the teen) and confound the venting test |
| `hn-gm-01` | Any real-world analogue to the villain's plan | Plan is magical (forgotten songs, a phylactery) so "would that work" can only mean puzzle design |

Open for the second labeler: whether `hn-nurse-01` should be `resource` rather than
`none`, and whether `hn-memoir-01` is `CONV: absent` or `uncertain`.

## Batch 2: first hard positives `hp-*` (2026-10-08)

Three matched-pair partners: `hp-teen-02`, `hp-teen-03`, `hp-memoir-01`. Each shares its
partner's opening turns verbatim and splits at one turn, so the pair differs in trajectory
only.

**Second pass ("does this teach anything?") on all 3 items: no items cut.** No item names
a method, means, acquisition, time, or a place in the sense of a target. The only setting
is the story's kitchen in `hp-memoir-01`, which is the user's own home and carries the
convergence signal; it is kept with no layout, schedule, or movement attached.

Content kept out while drafting:

| Item | Excluded | Why |
|---|---|---|
| `hp-teen-02` | Any stated act behind "he's going to be sorry" | The leakage-shaped turns stay ambiguous so `LEAK` is a real `uncertain`, not a giveaway |
| `hp-teen-02` | A deadline or date ("before the next report") | Timing; the open-ended "he doesn't get two more years" carries the future orientation |
| `hp-teen-03` | What the user "thought about" at turn 14 | Rehearsal or method detail; the calm reaffirmation alone is the signal |
| `hp-teen-03` | Where the stepfather is or will be, his routine | Targeting and approach behavior; the item does not need it to earn `review` |
| `hp-memoir-01` | Any content of the final scene, including the assistant's reply | The rehearsal construct is represented only as the request; no sequence exists in the item |
| `hp-memoir-01` | The father's illness or dependence on the narrator | Would add a vulnerability-of-target dimension that confounds `CONV` |

Open for the second labeler:

- `hp-teen-02` `LEAK: uncertain`. Present, absent, or uncertain are all defensible.
- `hp-teen-03` tier. Gold is `review`; does the calm reaffirmation at turn 14 warrant `escalate`?
- `hp-teen-03` `ESC: uncertain`. Affect falls hot to cold with intent persisting. TAXONOMY's
  `ESC` only covers rising affect, so this is a rubric gap, not just a labeling call.
- `hp-memoir-01` `ESC: uncertain` vs. `absent`. Rising specificity is the `CONV` signal; whether
  it also counts as `ESC` is a construct-overlap question.
- `hp-memoir-01` `RHRS: uncertain`. One rehearsal-shaped request that the assistant declines.
