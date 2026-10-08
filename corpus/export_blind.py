"""Export a blind labeling packet for the second labeler.

Usage: python3 corpus/export_blind.py [--items corpus/items.jsonl] [--out corpus/labeling] [--seed 5]

Writes five files:
    packet_A.md, labels_A.csv   first sitting. Send these.
    packet_B.md, labels_B.csv   second sitting, a few days later. Send these after A is back.
    key.json                    blind id -> corpus id. Do NOT send; it is what scoring joins on.

Matched pairs share their opening turns, so a labeler who reads both halves in one
sitting labels them as a contrast. Each pair is therefore split across the two packets
(which half goes where is random), and unpaired items alternate between them.

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
with anyone else on the project, without looking at the project repository, and
without using AI tools: the point is an independent human set of labels.

Some transcripts contain angry, distressing, or violent-sounding language. You can stop
at any point.

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

Fill in the labels CSV that came with this packet, one row per transcript id. Construct columns take `present`,
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
    ap.add_argument("--seed", type=int, default=5)
    args = ap.parse_args(argv)

    items = [json.loads(l) for l in Path(args.items).read_text().splitlines() if l.strip()]
    rng = random.Random(args.seed)
    ids = {it["id"] for it in items}
    packets = {"A": [], "B": []}
    seen, unpaired = set(), []
    for it in items:
        if it["id"] in seen:
            continue
        partner = it.get("pair_id")
        if partner in ids:
            pair = [it, next(x for x in items if x["id"] == partner)]
            rng.shuffle(pair)
            packets["A"].append(pair[0])
            packets["B"].append(pair[1])
            seen.update(x["id"] for x in pair)
        else:
            unpaired.append(it)
            seen.add(it["id"])
    rng.shuffle(unpaired)
    for n, it in enumerate(unpaired):
        packets["AB"[n % 2]].append(it)

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    width = max(2, len(str(len(items))))
    key, n = {}, 0
    for name, group in packets.items():
        rng.shuffle(group)
        blind = []
        for it in group:
            n += 1
            blind.append((f"L{n:0{width}d}", it))
            key[blind[-1][0]] = {"id": it["id"], "packet": name}
        header = GUIDE.replace("# Labeling packet", f"# Labeling packet {name}")
        (out / f"packet_{name}.md").write_text(header + "\n".join(render(b, it) for b, it in blind))
        with open(out / f"labels_{name}.csv", "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["id"] + [col for c in CONSTRUCTS for col in (c, f"{c}_evidence")] + ["tier", "notes"])
            for b, _ in blind:
                w.writerow([b] + [""] * (2 * len(CONSTRUCTS) + 2))
    (out / "key.json").write_text(json.dumps({"seed": args.seed, "items": key}, indent=1) + "\n")
    for stale in ("packet.md", "labels.csv"):
        (out / stale).unlink(missing_ok=True)
    print(f"A={len(packets['A'])} B={len(packets['B'])} transcripts -> {out} (send packets/labels; keep key.json)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
