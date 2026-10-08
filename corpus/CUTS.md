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
