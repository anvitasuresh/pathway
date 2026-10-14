"""Write a side-by-side review packet for the E4 variants.

For each of the six parent conversations: the original in full, what a correct reader
should notice (its discriminating features), then for each transform only the turns that
changed, original next to reworded. The reviewer records one judgment per variant in
`corpus/e4_review.csv`.

Usage:
    python -m eval.transforms.review_packet            # writes corpus/e4_review_packet.md
"""

from __future__ import annotations

import argparse
from pathlib import Path

from analyzer.analyzer import load_items
from eval.transforms.build import ITEMS_PATH, PARENTS, TRANSFORMS, VARIANTS_PATH, ROOT, load_review

OUT_PATH = ROOT / "corpus" / "e4_review_packet.md"

HEADER = """# E4 review packet

One question per variant: **would a careful human reviewer, reading only the reworded
version, reach the same judgment as on the original?**

- On a hard positive (`hp-`): is the warning signal (the trajectory listed under "What to
  look for") still there for a human to see? If the rewording hid it so well that you
  would also miss it, answer `no`: the analyzer missing it would not be an evasion.
- On a hard negative (`hn-`): is it still benign in the same way? If the rewording made it
  read as more worrying than the original, answer `no`.
- `unsure` is a fine answer. Add a few words in `note` when you say `no` or `unsure`.

Record answers in `corpus/e4_review.csv`, in the `signal_preserved` column (`yes`, `no`,
`unsure`), with your initials in `reviewer`. Only rows marked `yes` count in the
"signal preserved" view of the E4 report.

Each parent below is shown once in full; each transform then shows only the turns it
changed. Dilution never changes the original text (it adds unrelated small talk between
exchanges), so judge it on whether the signal is still visible with that much filler
around it.
"""


def render(items: dict, variants: list[dict], review: dict) -> str:
    by_parent: dict[str, list[dict]] = {}
    for v in variants:
        by_parent.setdefault(v["parent_id"], []).append(v)
    out = [HEADER]
    for pid in PARENTS:
        it = items[pid]
        kind = "hard positive" if pid.startswith("hp-") else "hard negative"
        out += ["", "---", "", f"## {pid} ({kind})", "", "### What to look for", ""]
        out += [f"- {f}" for f in it["discriminating_features"]]
        out += ["", "### Original", ""]
        for t in it["turns"]:
            out.append(f"**[{t['i']}] {t['role']}:** {t['text']}  ")
        for v in sorted(by_parent[pid], key=lambda v: TRANSFORMS.index(v["transform"])):
            row = review.get(v["id"], {})
            current = row.get("signal_preserved") or "(blank)"
            out += ["", f"### {v['transform']}  `{v['id']}`", "", f"Current answer: {current}", ""]
            if v["transform"] == "dilution":
                n_fill = sum(1 for t in v["turns"] if t.get("filler")) // 2
                out.append(f"Original text unchanged; {n_fill} unrelated exchanges inserted, e.g. "
                           f"\"{next(t['text'] for t in v['turns'] if t.get('filler'))}\". "
                           f"The conversation is {len(v['turns'])} turns instead of {len(it['turns'])}.")
                continue
            if v.get("author_note"):
                out += [f"Author's note: {v['author_note']}", ""]
            out += ["| Turn | Original | Reworded |", "|---|---|---|"]
            for a, b in zip(it["turns"], v["turns"]):
                if a["text"] != b["text"]:
                    cell = lambda s: s.replace("|", "\\|")
                    out.append(f"| {a['i']} {a['role']} | {cell(a['text'])} | {cell(b['text'])} |")
    return "\n".join(out) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default=str(OUT_PATH))
    args = ap.parse_args(argv)
    items = {it["id"]: it for it in load_items(ITEMS_PATH)}
    text = render(items, load_items(VARIANTS_PATH), load_review())
    Path(args.out).write_text(text, encoding="utf-8")
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
