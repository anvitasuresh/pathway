# Writing the remaining hard positives

Seven to write, so the corpus reaches the 10 TAXONOMY.md plans for. Each one is the
matched partner of an existing hard negative, like `hp-teen-02` is for `hn-teen-02`.

## Rules first (these override everything below)

1. **Behavior, never technique.** Anger, grievance, narrowing, refusal of support, a
   statement that comes back calmly. No weapons, methods, acquisition, logistics, times,
   dates, schedules, or where a person can be found. If a sentence would teach someone
   anything, cut it and log it in `CUTS.md`.
2. **Everything fictional.** Invented names, places, employers. No real people.
3. **Write them yourself, in a text editor.** Don't paste them into a chat model to write
   or polish (account-safety rule, and it would bring back the self-agreement problem).
4. **Not every positive should look scary.** The point is that no single message is
   more alarming than the negative it's paired with. The signal is the direction the
   conversation takes.

## The 7 pairs

Pick 7 of these 9 unpaired negatives. Each line says which construct the positive should
test, so the set covers constructs the first three didn't.

| Partner of | Construct to test | Note |
|---|---|---|
| `hn-teen-01` | `ESC` alone | Escalation without fixation. Correct tier can be `resource`: tests whether the analyzer over-escalates a positive |
| `hn-crimstudent-01` | `IDN` | Stance moves from critical to admiring of the textbook's composite subject. IDN has zero positives right now |
| `hn-truecrime-01` | `LEAK` buried | One leakage-shaped line in a long, otherwise ordinary conversation, then back to normal topics |
| `hn-grief-01` | `FIX` | Attention narrows onto the offender where the negative turns toward the sister |
| `hn-workplace-01` | `FIX` + `IDN` uncertain | Keeps returning to the manager instead of moving on to severance and resume |
| `hn-defense-01` | `FIX`, tier `friction` | Professional grievance turns personal; ends with a request the assistant declines |
| `hn-novelist-01` | `RHRS` | Only the *request* to go over something again; no sequence ever appears |
| `hn-nurse-01` | your call | |
| `hn-gm-01` | your call | Hardest to make safely; skip unless you have a clear idea |

## How to write one

1. Open the negative in `corpus/items.jsonl` and copy its opening turns word for word.
2. Pick **one turn** where your version splits off. Everything before it stays identical.
3. From that turn on, change the *direction*: where the negative broadens, yours narrows;
   where it accepts help, yours declines; where affect resolves, yours doesn't.
4. Keep the assistant's replies reasonable. It should notice, ask, and offer support.
5. End without resolving. Don't add a confession or a disclaimer that makes the label obvious.
6. Reread it once asking "does this teach anything?" Cut anything that does.

## How to fill in the fields

Copy the structure of `hp-teen-02` in `items.jsonl`:

- `id`: `hp-<persona>-01` (e.g. `hp-grief-01`); `stratum`: `hard_positive`
- `gold`: each construct `present` / `absent` / `uncertain`, with the turn numbers as
  evidence (`absent` has none). Use `uncertain` whenever you'd honestly argue both ways.
- `tier`: what the conversation warrants. Most will be `review`; aim for at least one
  `resource` or `friction`.
- `discriminating_features`: 3–6 short lines. The first says which turn the pair splits at.
- `trap_for`: one line on what kind of system this fools.
- `notes`: one sentence per labeled construct, citing turns.
- `pair_id`: the negative's id. Also add `"pair_id": "hp-..."` to the negative.

## Check and commit

```
python3 corpus/validate.py      # must print OK
python -m pytest -q
git add corpus && git commit -m "corpus: add hard positives for ..." && git push
```

Add a short "Batch 3" section to `CUTS.md` listing anything you left out and why.

Then run the analyzer on the new pairs (negatives too, so each pair comes from one run):

```
python -m analyzer.analyzer --items corpus/items.jsonl --ids <the new hp and hn ids> --out results_v2_batch3.jsonl
python -m eval.metrics --items corpus/items.jsonl --preds results_v2_batch3.jsonl
```

Commit the results file. Because you wrote these labels without a model, this run is the
first analyzer-vs-gold comparison in the project that isn't partly a model agreeing with
itself. Say so in the write-up.
