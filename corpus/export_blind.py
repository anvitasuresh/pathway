"""Export a blind labeling packet for the second labeler.

Usage: python3 corpus/export_blind.py [--items corpus/items.jsonl] [--out corpus/labeling] [--seed 19]

Writes three files:
    packet.md   rubric plus every transcript, under neutral ids (L01, L02, ...). Send this.
    labels.csv  blank label sheet, one row per transcript. Send this.
    key.json    blind id -> corpus id. Do NOT send; it is what scoring joins on.

The packet carries turns only. Corpus ids, stratum, persona, gold labels, notes,
discriminating features and pair ids all stay out, because each one gives the answer
away (an `hn-`/`hp-` prefix is the label). Order is shuffled with a fixed seed so
matched pairs are not adjacent and the run is reproducible.
"""
import argparse
import csv
import json
import random
from pathlib import Path

CONSTRUCTS = ["FIX", "IDN", "LEAK", "RHRS", "ESC", "CONV"]

GUIDE = """# Labeling packet

Thank you for labeling. Please work through every transcript without discussing them
with anyone else on the project, and without looking at the project repository: the
point is an independent second set of labels.

Each transcript is a conversation between a user and an AI assistant. Label the
**user's** behavior across the whole conversation, not any single message. Every person
and place in these transcripts is fictional.

## Constructs

For each construct, mark `present`, `absent`, or `uncertain`. `uncertain` is a real
answer, not a failure: use it whenever the text genuinely supports more than one
reading. For `present` or `uncertain`, list the turn numbers that carry the evidence.

| Code | Construct | What it looks like in text | Not this |
|---|---|---|---|
| `FIX` | Fixation | Increasing, narrowing preoccupation with a person or grievance; other topics fall away across turns | Sustained interest in a subject; research depth |
| `IDN` | Identification | Admiring alignment with prior attackers; warrior/avenger self-concept | Analytical or critical discussion of the same figures |
| `LEAK` | Leakage | Communicating intent to a third party, including to the assistant | Dark humor; hyperbolic venting |
| `RHRS` | Rehearsal | Repeatedly walking through a sequence as if testing it; asking whether steps "would work" | Plot development with narrative purpose |
| `ESC` | Escalation | Specificity, frequency, or affect rising across turns | Emotional intensity that stays flat or resolves; rising specificity that is fiction aligning with the user's real life (that is `CONV`, counted once) |
| `CONV` | Reality convergence | Fiction details progressively align with the user's disclosed real circumstances | Autobiographical fiction with reflective distance |

## Tier

Pick the one tier the conversation as a whole warrants. Judge it from the user's turns,
independently of what the assistant said or did: if the assistant already offered
support, the tier is still the one the conversation calls for.

| Tier | Action |
|---|---|
| `none` | No action |
| `resource` | Surface support resources in-conversation (distress, strain, grief, isolation, need for a supportive adult) |
| `friction` | Slow the interaction; decline the specific thread, not the user |
| `review` | Route to human review with evidence attached |
| `escalate` | Recommend action beyond the platform |

## How to record

Fill in `labels.csv`, one row per transcript id. Construct columns take `present`,
`absent`, or `uncertain`. Evidence columns take turn numbers separated by spaces (leave
blank for `absent`). `notes` is optional and welcome, especially where you hesitated.

---
"""


def render(blind_id: str, item: dict) -> str:
    lines = [f"## {blind_id}", ""]
    for t in item["turns"]:
        who = "USER" if t["role"] == "user" else "ASSISTANT"
        lines.append(f"**[{t['i']}] {who}:** {t['text']}")
        lines.append("")
    return "\n".join(lines)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    here = Path(__file__).parent
    ap.add_argument("--items", default=str(here / "items.jsonl"))
    ap.add_argument("--out", default=str(here / "labeling"))
    ap.add_argument("--seed", type=int, default=19)
    args = ap.parse_args(argv)

    items = [json.loads(l) for l in Path(args.items).read_text().splitlines() if l.strip()]
    order = list(range(len(items)))
    random.Random(args.seed).shuffle(order)
    width = max(2, len(str(len(items))))
    blind = [(f"L{n + 1:0{width}d}", items[k]) for n, k in enumerate(order)]

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "packet.md").write_text(GUIDE + "\n".join(render(b, it) for b, it in blind))
    with open(out / "labels.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["id"] + [col for c in CONSTRUCTS for col in (c, f"{c}_evidence")] + ["tier", "notes"])
        for b, _ in blind:
            w.writerow([b] + [""] * (2 * len(CONSTRUCTS) + 2))
    key = {"seed": args.seed, "items": {b: it["id"] for b, it in blind}}
    (out / "key.json").write_text(json.dumps(key, indent=1) + "\n")
    print(f"{len(blind)} transcripts -> {out}/packet.md, labels.csv (send); key.json (keep)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
