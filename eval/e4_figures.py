"""E4 explanation-stability figure: the decision held, did the explanation?

The first two E4 runs moved no tier under any transform, but construct labels did move.
This draws, for each hard positive, its tier and every construct that is not absent in
gold or any analyzer output, across all seven arms, for the run
with the assistant's turns kept and the run with them neutral. Each cell is one
analyzer label on one conversation (no rates, no pooling), so n=3 is visible as n=3.

It also prints, per arm, how many of the hard positives' construct labels (6 per
conversation) match the analyzer's label on the original, and how many tiers do.

Usage:
    python -m eval.e4_figures --kept eval/results/e4_run.jsonl \
        --neutral eval/results/e4_neutral.jsonl --out eval/results/e4_explanation.svg
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from analyzer.analyzer import CONSTRUCTS, load_items
from eval.e4_evasion import ARMS, ITEMS_PATH
from eval.transforms.build import PARENTS, neutral_id

ARM_LABEL = {"original": "original", "paraphrase": "paraphrase", "euphemism": "euphemism",
             "fiction_frame": "fiction frame", "roleplay": "roleplay",
             "translate_back": "translate &amp; back", "dilution": "dilution"}
POSITIVES = tuple(p for p in PARENTS if p.startswith("hp-"))


def row_id(pid: str, arm: str, assistant: str) -> str:
    vid = pid if arm == "original" else f"{pid}__{arm}"
    return neutral_id(vid) if assistant == "neutral" else vid


def grid(rows: list[dict], assistant: str) -> dict:
    """{(pid, arm): output or None} for the hard positives."""
    by_id = {r["item_id"]: r for r in rows}
    out = {}
    for pid in POSITIVES:
        for arm in ARMS:
            r = by_id.get(row_id(pid, arm, assistant))
            out[(pid, arm)] = r["output"] if r and r.get("status") == "ok" and r.get("output") else None
    return out


def shown_constructs(pid: str, gold: dict, kept: dict, neutral: dict) -> list[str]:
    shown = []
    for c in CONSTRUCTS:
        labels = {gold[pid][c]["label"]}
        for g in (kept, neutral):
            for arm in ARMS:
                o = g[(pid, arm)]
                if o:
                    labels.add(o["constructs"][c]["label"])
        if labels != {"absent"}:
            shown.append(c)
    return shown


def stability(g: dict) -> dict[str, dict]:
    out = {}
    for arm in ARMS:
        same = n = tier_same = tier_n = 0
        for pid in POSITIVES:
            base, o = g[(pid, "original")], g[(pid, arm)]
            if not (base and o):
                continue
            tier_n += 1
            tier_same += o["tier"] == base["tier"]
            for c in CONSTRUCTS:
                n += 1
                same += o["constructs"][c]["label"] == base["constructs"][c]["label"]
        out[arm] = {"labels_same": same, "labels_n": n, "tiers_same": tier_same, "tiers_n": tier_n}
    return out


def render_svg(gold: dict, kept: dict, neutral: dict) -> str:
    blue, ink, ink2, rule, surface = "#2a78d6", "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"
    rows: list[tuple[str, str]] = []  # (pid, "TIER" | construct)
    for pid in POSITIVES:
        rows.append((pid, "TIER"))
        rows += [(pid, c) for c in shown_constructs(pid, gold, kept, neutral)]

    left, top, cw, rh, gap = 170, 150, 46, 24, 36
    panel_w = cw * len(ARMS)
    W = left + 2 * panel_w + gap + 24
    n_groups = len(POSITIVES)
    H = top + rh * len(rows) + 10 * n_groups + 70

    p = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" '
         f'font-family="Helvetica, Arial, sans-serif" role="img" aria-labelledby="t d">',
         '<title id="t">The decision held; the explanation moved</title>',
         '<desc id="d">For each of three hard positives, the analyzer tier and construct labels on the '
         'original conversation and six rewordings, with the assistant turns as written and replaced '
         'by neutral acknowledgments. The tier is review in every cell; several construct labels move '
         'between present and uncertain.</desc>',
         f'<rect width="{W}" height="{H}" fill="{surface}"/>',
         f'<text x="16" y="28" font-size="17" font-weight="600" fill="{ink}">The decision held; the explanation moved</text>',
         f'<text x="16" y="48" font-size="12" fill="{ink2}">Analyzer output on 3 hard positives, original and six '
         'rewordings. One cell = one label on one conversation.</text>']

    for k, (g, title) in enumerate(((kept, "Assistant turns as written"), (neutral, "Assistant turns neutral"))):
        x0 = left + k * (panel_w + gap)
        p.append(f'<text x="{x0}" y="{top - 78}" font-size="12" font-weight="600" fill="{ink}">{title}</text>')
        for j, arm in enumerate(ARMS):
            cx = x0 + cw * j + cw / 2
            p.append(f'<text transform="translate({cx + 3:.1f},{top - 8}) rotate(-40)" font-size="10" '
                     f'fill="{ink2}">{ARM_LABEL[arm]}</text>')
        y = top
        prev = None
        for pid, what in rows:
            if pid != prev and prev is not None:
                y += 10
            prev = pid
            cy = y + rh / 2
            if k == 0:
                label = f"{pid}  tier" if what == "TIER" else what
                weight = "600" if what == "TIER" else "400"
                p.append(f'<text x="{left - 10}" y="{cy + 4:.1f}" font-size="11" font-weight="{weight}" '
                         f'text-anchor="end" fill="{ink}">{label}</text>')
            for j, arm in enumerate(ARMS):
                cx = x0 + cw * j + cw / 2
                o = g[(pid, arm)]
                if o is None:
                    p.append(f'<text x="{cx:.1f}" y="{cy + 4:.1f}" font-size="11" text-anchor="middle" fill="{ink2}">–</text>')
                    continue
                if what == "TIER":
                    p.append(f'<text x="{cx:.1f}" y="{cy + 4:.1f}" font-size="10" text-anchor="middle" '
                             f'fill="{ink}"><title>{ARM_LABEL[arm]}: tier {o["tier"]}</title>{o["tier"]}</text>')
                    continue
                lab = o["constructs"][what]["label"]
                tip = f'<title>{pid} {what}, {ARM_LABEL[arm]}: {lab}</title>'
                if lab == "present":
                    p.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="7" fill="{blue}">{tip}</circle>')
                elif lab == "uncertain":
                    p.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="6" fill="{surface}" stroke="{blue}" '
                             f'stroke-width="2" stroke-dasharray="3 2">{tip}</circle>')
                else:
                    p.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="2.5" fill="{ink2}">{tip}</circle>')
            y += rh
        p.append(f'<line x1="{x0}" x2="{x0 + panel_w}" y1="{y + 4}" y2="{y + 4}" stroke="{rule}"/>')

    ly = H - 22
    p += [f'<circle cx="22" cy="{ly - 4}" r="7" fill="{blue}"/>',
          f'<text x="36" y="{ly}" font-size="12" fill="{ink}">present</text>',
          f'<circle cx="112" cy="{ly - 4}" r="6" fill="{surface}" stroke="{blue}" stroke-width="2" stroke-dasharray="3 2"/>',
          f'<text x="126" y="{ly}" font-size="12" fill="{ink}">uncertain</text>',
          f'<circle cx="212" cy="{ly - 4}" r="2.5" fill="{ink2}"/>',
          f'<text x="222" y="{ly}" font-size="12" fill="{ink}">absent</text>',
          f'<text x="300" y="{ly}" font-size="11" fill="{ink2}">Rows: constructs not absent in gold or in any output.'
          ' Transforms in design order, not ranked.</text>',
          "</svg>"]
    return "\n".join(p) + "\n"


def render_table(kept: dict, neutral: dict) -> str:
    out = ["| Arm | Tier same as original (kept) | Construct labels same (kept) | "
           "Tier same (neutral) | Construct labels same (neutral) |", "|---|---|---|---|---|"]
    sk, sn = stability(kept), stability(neutral)
    for arm in ARMS:
        a, b = sk[arm], sn[arm]
        out.append(f"| {arm} | {a['tiers_same']}/{a['tiers_n']} | {a['labels_same']}/{a['labels_n']} | "
                   f"{b['tiers_same']}/{b['tiers_n']} | {b['labels_same']}/{b['labels_n']} |")
    return "\n".join(out) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--items", default=str(ITEMS_PATH))
    ap.add_argument("--kept", required=True, help="E4 rows with assistant turns as written")
    ap.add_argument("--neutral", required=True, help="E4 rows with --assistant neutral")
    ap.add_argument("--out", help="write the SVG here")
    args = ap.parse_args(argv)

    gold = {it["id"]: it["gold"] for it in load_items(args.items)}
    kept = grid(load_items(args.kept), "kept")
    neutral = grid(load_items(args.neutral), "neutral")
    if args.out:
        Path(args.out).write_text(render_svg(gold, kept, neutral), encoding="utf-8")
    sys.stdout.write("Hard positives: agreement with the analyzer's own output on the original "
                     "(not with gold).\n\n" + render_table(kept, neutral))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
