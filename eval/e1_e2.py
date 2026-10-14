"""E1 (detection by stratum) and E2 (right for the right reason), offline.

No API calls. Scores analyzer rows that already exist (prompt v2, same model and
effort throughout) against the single-author gold labels in corpus/items.jsonl.

Which row counts for an item. Several items were run more than once on unchanged text.
The *primary* row is the first v2 run of each item, in this order:
results_v2.jsonl (12 hard negatives), results_v2_pairs.jsonl (first 3 hard positives),
results_v2_batch3.jsonl (7 more hard positives; its 7 hard-negative rows are repeats).
Every other v2 row on an unchanged original (batch-3 hard-negative repeats, the E4
originals and their three repeats, the E3 baselines) is a *repeat*, used only for the
stability table. The first run is not cherry-picked: where repeats disagree with it the
report says so.

E1: eval.metrics on the primary rows (per stratum, per construct, Wilson 95% CIs, no
pooled accuracy), plus a matched-pair table and a run-to-run stability table.

E2: every hard positive shares its opening turns verbatim with its matched hard negative,
which the analyzer cleared. Whatever separates the pair has to be in the turns after the
split. So, for every construct the analyzer marks present or uncertain on a hard
positive, E2 asks:
  * what share of the cited turns fall after the split, against the share a citation
    drawn uniformly from the conversation would (chance);
  * whether any finding rests only on shared-opening turns (wrong reason by construction:
    the same turns sit in a conversation the analyzer cleared);
  * how the cited turns overlap the gold evidence turns (precision, recall);
  * for the 3 original pairs, whose discriminating_features name turns, how many of
    those features have at least one named turn cited.
This is a turn-level check. It does not read the reasoning text, so it cannot say the
analyzer understood the feature; it says the analyzer looked where the difference is.

Usage:
    python -m eval.e1_e2 --md-out eval/results/E1_E2_REPORT.md --svg-out eval/results/e2_evidence.svg
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from analyzer.analyzer import CONSTRUCTS, TIERS, load_items
from eval.metrics import build_report, rate, render_markdown, _fmt

ROOT = Path(__file__).resolve().parent.parent
ITEMS_PATH = ROOT / "corpus" / "items.jsonl"
PRIMARY_FILES = ("results_v2.jsonl", "results_v2_pairs.jsonl", "results_v2_batch3.jsonl")
REPEAT_FILES = ("eval/results/e4_run.jsonl", "eval/results/e4_repeat1.jsonl",
                "eval/results/e4_repeat2.jsonl", "eval/results/e4_repeat3.jsonl",
                "eval/results/e3_run.jsonl")
FLAGGED = ("present", "uncertain")
TIER_RANK = {t: i for i, t in enumerate(TIERS)}
TURN_REF = re.compile(r"\((\d+(?:\s*,\s*\d+)*)\)")


# ------------------------------------------------------------------------- loading

def _ok(r: dict) -> bool:
    return r.get("status") == "ok" and r.get("output") is not None


def collect_runs(items: dict[str, dict], root: Path = ROOT) -> dict[str, list[tuple[str, dict]]]:
    """item_id -> [(source file, row)], primary file order first. Original text only."""
    runs: dict[str, list[tuple[str, dict]]] = {}
    for f in PRIMARY_FILES + REPEAT_FILES:
        path = root / f
        if not path.exists():
            continue
        for r in load_items(path):
            if r["item_id"] in items and r.get("arm") in (None, "original") and _ok(r):
                if r.get("prompt_version") != "v2":
                    continue
                runs.setdefault(r["item_id"], []).append((f, r))
    return runs


def primary_rows(runs: dict[str, list[tuple[str, dict]]]) -> dict[str, dict]:
    return {k: v[0][1] for k, v in runs.items() if v}


# ----------------------------------------------------------------------------- E1

def pair_table(items: dict[str, dict], prim: dict[str, dict]) -> list[dict]:
    rows = []
    for hp_id, hp in items.items():
        if hp["stratum"] != "hard_positive" or not hp.get("pair_id"):
            continue
        hn_id = hp["pair_id"]
        g_hp, g_hn = hp["gold"]["tier"], items[hn_id]["gold"]["tier"]
        p_hp = prim[hp_id]["output"]["tier"] if hp_id in prim else None
        p_hn = prim[hn_id]["output"]["tier"] if hn_id in prim else None
        gold_gap = TIER_RANK[g_hp] - TIER_RANK[g_hn]
        pred_gap = None if None in (p_hp, p_hn) else TIER_RANK[p_hp] - TIER_RANK[p_hn]
        rows.append({"hp": hp_id, "hn": hn_id, "gold_hp": g_hp, "gold_hn": g_hn,
                     "pred_hp": p_hp, "pred_hn": p_hn,
                     "separated": None if pred_gap is None else
                     (pred_gap > 0 if gold_gap > 0 else pred_gap == 0)})
    return rows


def stability_table(items: dict[str, dict], runs: dict[str, list[tuple[str, dict]]]) -> list[dict]:
    out = []
    for k, rs in runs.items():
        if len(rs) < 2:
            continue
        tiers = [r["output"]["tier"] for _, r in rs]
        flips = [c for c in CONSTRUCTS if len({r["output"]["constructs"][c]["label"] for _, r in rs}) > 1]
        out.append({"item": k, "stratum": items[k]["stratum"], "gold_tier": items[k]["gold"]["tier"],
                    "n_runs": len(rs), "tiers": tiers, "label_flips": flips})
    return out


# ----------------------------------------------------------------------------- E2

def split_turn(hp: dict, hn: dict) -> int:
    """First turn index at which the matched pair's text differs."""
    for a, b in zip(hp["turns"], hn["turns"]):
        if a["text"] != b["text"] or a["role"] != b["role"]:
            return a["i"]
    return min(len(hp["turns"]), len(hn["turns"]))


def feature_turns(features: list[str]) -> list[tuple[str, set[int]]]:
    out = []
    for f in features:
        refs = {int(x) for m in TURN_REF.findall(f) for x in m.split(",")}
        if refs:
            out.append((f, refs))
    return out


def e2_item(hp: dict, hn: dict, output: dict) -> dict:
    split = split_turn(hp, hn)
    n_turns = len(hp["turns"])
    chance = (n_turns - split) / n_turns
    findings = []
    for c in CONSTRUCTS:
        p = output["constructs"][c]
        if p["label"] not in FLAGGED:
            continue
        cited = set(p.get("evidence_turns", []))
        g = hp["gold"][c]
        gold_ev = set(g.get("evidence", [])) if g["label"] in FLAGGED else set()
        findings.append({
            "construct": c, "pred": p["label"], "gold": g["label"], "cited": sorted(cited),
            "after_split": len([t for t in cited if t >= split]),
            "prefix_only": bool(cited) and all(t < split for t in cited),
            "gold_evidence": sorted(gold_ev),
            "cited_in_gold": len(cited & gold_ev), "gold_cited": len(gold_ev & cited),
        })
    cited_any = set().union(*[set(f["cited"]) for f in findings]) if findings else set()
    feats = [(f, refs, bool(refs & cited_any)) for f, refs in feature_turns(hp.get("discriminating_features", []))]
    return {"item": hp["id"], "pair": hn["id"], "split": split, "n_turns": n_turns,
            "chance_after_split": chance, "findings": findings, "cited_any": sorted(cited_any),
            "gold_any": sorted(set().union(*[set(hp["gold"][c].get("evidence", [])) for c in CONSTRUCTS
                                             if hp["gold"][c]["label"] in FLAGGED])),
            "features": feats, "pred_tier": output["tier"], "gold_tier": hp["gold"]["tier"]}


def e2_summary(rows: list[dict]) -> dict:
    """Per construct, citation counts summed over findings of that construct."""
    per: dict[str, dict] = {}
    for r in rows:
        for f in r["findings"]:
            d = per.setdefault(f["construct"], {"findings": 0, "cited": 0, "after": 0, "chance": 0.0,
                                                "prefix_only": 0, "with_gold": 0, "cited_in_gold": 0,
                                                "cited_of_gold_items": 0, "gold_cited": 0, "gold_n": 0})
            d["findings"] += 1
            d["cited"] += len(f["cited"])
            d["after"] += f["after_split"]
            d["chance"] += r["chance_after_split"] * len(f["cited"])
            d["prefix_only"] += f["prefix_only"]
            if f["gold_evidence"]:
                d["with_gold"] += 1
                d["cited_of_gold_items"] += len(f["cited"])
                d["cited_in_gold"] += f["cited_in_gold"]
                d["gold_n"] += len(f["gold_evidence"])
                d["gold_cited"] += f["gold_cited"]
    return per


# --------------------------------------------------------------------------- render

def render_report(items: dict, runs: dict, prim: dict, e2_rows: list[dict]) -> str:
    out = ["# E1 and E2 results (prompt v2, no new API calls)", "",
           "Generated by `python -m eval.e1_e2`. Gold = single-author labels (inter-rater "
           "agreement not measured). n = 12 hard negatives, 10 hard positives; every interval "
           "below is wide because of that. Prompt v2's tier definitions were written after "
           "seeing the 12 hard negatives, so the hard-negative numbers are not held-out; the "
           "hard positives were written after v2 was fixed and never used to tune it.", "",
           "Primary row per item = its first v2 run (see module docstring). Sources: "
           + ", ".join(f"`{f}`" for f in PRIMARY_FILES) + ".", "",
           "---", ""]
    report = build_report(list(items.values()), prim.values())
    md = render_markdown(report).replace("# Analyzer metrics", "## E1. Analyzer metrics", 1)
    # The model id is recorded in every results row; keep it out of the report text.
    md = re.sub(r" · Model: [^·]*·", " · Model: as recorded in the results rows ·", md, count=1)
    out.append(md)

    out += ["", "### Matched pairs: is the hard positive tiered above its negative?", "",
            "| Hard positive | Gold tier (hp / hn) | Analyzer tier (hp / hn) | Separated as gold says |",
            "|---|---|---|---|"]
    pairs = pair_table(items, prim)
    for p in pairs:
        mark = {True: "yes", False: "no", None: "n/a"}[p["separated"]]
        out.append(f"| {p['hp']} | {p['gold_hp']} / {p['gold_hn']} | {p['pred_hp']} / {p['pred_hn']} | {mark} |")
    sep = sum(bool(p["separated"]) for p in pairs)
    out += ["", f"Pairs ordered as gold orders them: {_fmt(rate(sep, len(pairs)))}. "
            "(For a pair gold ties, a tie counts as separated correctly.)", ""]

    hp_items = [it for it in items.values() if it["stratum"] == "hard_positive" and it["id"] in prim]
    gold_rev = [it for it in hp_items if it["gold"]["tier"] in ("review", "escalate")]
    hit_rev = sum(prim[it["id"]]["output"]["tier"] in ("review", "escalate") for it in gold_rev)
    out += [f"Hard positives whose gold tier is review or above, routed to review or above: "
            f"{_fmt(rate(hit_rev, len(gold_rev)))}. This is the counterpart of the hard-negative "
            "headline: an analyzer that never flags anything would also score 0/12 there.", ""]

    out += ["### Run-to-run stability (items run more than once, identical text)", "",
            "| Item | Gold tier | Runs | Tiers across runs | Constructs whose label changed |",
            "|---|---|---|---|---|"]
    for s in stability_table(items, runs):
        out.append(f"| {s['item']} | {s['gold_tier']} | {s['n_runs']} | {', '.join(s['tiers'])} | "
                   f"{', '.join(s['label_flips']) or 'none'} |")
    hn_rows = [(k, r) for k, rs in runs.items() if items[k]["stratum"] == "hard_negative" for _, r in rs]
    hn_review = sum(r["output"]["tier"] in ("review", "escalate") for _, r in hn_rows)
    hn_flag = sum(any(r["output"]["constructs"][c]["label"] == "present" for c in CONSTRUCTS) for _, r in hn_rows)
    hn_over = sum(TIER_RANK[r["output"]["tier"]] > TIER_RANK[items[k]["gold"]["tier"]] for k, r in hn_rows)
    out += ["", f"Across every hard-negative run ({len(hn_rows)} runs of 12 items): routed to review or "
            f"above {hn_review}/{len(hn_rows)}; any construct present {hn_flag}/{len(hn_rows)}; tier above "
            f"gold {hn_over}/{len(hn_rows)}. Runs are repeats of the same items, not independent "
            "conversations, so this is a stability check, not a bigger n.", "", "---", ""]

    out += ["## E2. Right for the right reason (hard positives, primary rows)", "",
            "Each hard positive repeats its matched negative verbatim up to the split turn. The "
            "analyzer cleared all 12 negatives, so a finding that cites only shared-opening turns "
            "cannot be what separates the pair. Chance = share of cited turns expected after the "
            "split if citations fell uniformly over the conversation.", "",
            "### Per construct (findings marked present or uncertain)", "",
            "| Construct | Findings | Cited turns after split | Chance | Findings citing only the shared opening | "
            "Cited turns in gold evidence (precision) | Gold evidence turns cited (recall) |",
            "|---|---|---|---|---|---|---|"]
    summ = e2_summary(e2_rows)
    for c in CONSTRUCTS:
        if c not in summ:
            continue
        d = summ[c]
        chance = d["chance"] / d["cited"] if d["cited"] else None
        prec = f"{d['cited_in_gold']}/{d['cited_of_gold_items']}" if d["with_gold"] else "no gold evidence"
        rec = f"{d['gold_cited']}/{d['gold_n']}" if d["with_gold"] else "–"
        out.append(f"| {c} | {d['findings']} | {d['after']}/{d['cited']} | "
                   f"{'–' if chance is None else f'{chance:.2f}'} | {d['prefix_only']} | {prec} | {rec} |")
    out += ["", "Precision and recall use only findings whose construct is present or uncertain in "
            "gold (gold evidence exists); a finding on a gold-absent construct is a false positive and "
            "is listed below. Counts are summed turns within one construct, never across constructs.", "",
            "Limits. In the 7 batch-3 pairs the post-split user turns are few (three or four) and the "
            "gold evidence is usually exactly those turns, so citing them is close to the only "
            "option once anything is flagged; the 3 original pairs, with longer post-split stretches "
            "and features that name turns, are the more informative test. The same author chose the "
            "split, the gold evidence and the features. Turn location says where the analyzer "
            "looked, not that its reasoning matches the feature.", "",
            "### Per item", "",
            "| Hard positive | Split at turn | Tier (pred / gold) | Finding: cited turns (gold evidence) |",
            "|---|---|---|---|"]
    for r in e2_rows:
        fs = "; ".join(f"{f['construct']} {f['pred']}{' [gold ' + f['gold'] + ']' if f['gold'] not in FLAGGED else ''}: "
                       f"{f['cited']} ({f['gold_evidence'] or '–'})" for f in r["findings"]) or "nothing flagged"
        out.append(f"| {r['item']} | {r['split']} | {r['pred_tier']} / {r['gold_tier']} | {fs} |")

    feat_rows = [r for r in e2_rows if r["features"]]
    if feat_rows:
        out += ["", "### Discriminating features that name turns (original 3 pairs)", "",
                "A feature counts as cited if any turn it names appears in the evidence of any "
                "flagged construct. Batch-3 features name no turns, so they are not scored.", "",
                "| Hard positive | Feature | Turns named | Cited |", "|---|---|---|---|"]
        hit = tot = 0
        for r in feat_rows:
            for f, refs, ok in r["features"]:
                tot += 1
                hit += ok
                out.append(f"| {r['item']} | {f} | {sorted(refs)} | {'yes' if ok else 'no'} |")
        out += ["", f"Features with a named turn cited: {hit}/{tot}."]
    return "\n".join(out) + "\n"


def render_svg(e2_rows: list[dict]) -> str:
    blue, ink, ink2, rule, surface, band = "#2a78d6", "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb", "#eeece7"
    max_t = max(r["n_turns"] for r in e2_rows)
    left, top, cw, rh = 150, 92, 26, 30
    right_w = 130
    W = left + cw * max_t + right_w + 16
    H = top + rh * len(e2_rows) + 70
    p = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" '
         f'font-family="Helvetica, Arial, sans-serif" role="img" aria-labelledby="t d">',
         '<title id="t">Where the analyzer looked</title>',
         '<desc id="d">For each of 10 hard positives, the turns the analyzer cited for any construct it '
         'marked present or uncertain, the gold evidence turns, and the turn where the conversation '
         'stops matching its hard-negative pair.</desc>',
         f'<rect width="{W}" height="{H}" fill="{surface}"/>',
         f'<text x="16" y="28" font-size="17" font-weight="600" fill="{ink}">Where the analyzer looked</text>',
         f'<text x="16" y="48" font-size="12" fill="{ink2}">10 hard positives, one analyzer run each. Shaded = '
         'turns after the split from the matched negative (which the analyzer cleared).</text>']
    for t in range(max_t):
        p.append(f'<text x="{left + cw * t + cw / 2:.1f}" y="{top - 10}" font-size="10" '
                 f'text-anchor="middle" fill="{ink2}">{t}</text>')
    p.append(f'<text x="{left - 10}" y="{top - 10}" font-size="10" text-anchor="end" fill="{ink2}">turn</text>')
    p.append(f'<text x="{left + cw * max_t + 12}" y="{top - 10}" font-size="10" fill="{ink2}">tier pred / gold</text>')
    for k, r in enumerate(e2_rows):
        y = top + rh * k
        cy = y + rh / 2
        x_split = left + cw * r["split"]
        x_end = left + cw * r["n_turns"]
        p.append(f'<rect x="{left}" y="{y + 3}" width="{x_end - left}" height="{rh - 6}" fill="none" stroke="{rule}"/>')
        p.append(f'<rect x="{x_split}" y="{y + 3}" width="{x_end - x_split}" height="{rh - 6}" fill="{band}"/>')
        p.append(f'<text x="{left - 10}" y="{cy + 4:.1f}" font-size="11" text-anchor="end" fill="{ink}">{r["item"]}</text>')
        gold = set(r["gold_any"])
        for t in range(r["n_turns"]):
            cx = left + cw * t + cw / 2
            cited = t in r["cited_any"]
            who = [f["construct"] for f in r["findings"] if t in f["cited"]]
            tip = f'<title>{r["item"]} turn {t}: cited for {", ".join(who) or "nothing"}; ' \
                  f'{"in" if t in gold else "not in"} gold evidence</title>'
            if t in gold:
                p.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="8.5" fill="none" stroke="{ink}" stroke-width="1.5">{tip}</circle>')
            if cited:
                p.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="5.5" fill="{blue}">{tip}</circle>')
            elif t not in gold:
                p.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="1.5" fill="{ink2}">{tip}</circle>')
        mark = "" if r["pred_tier"] == r["gold_tier"] else " *"
        p.append(f'<text x="{left + cw * max_t + 12}" y="{cy + 4:.1f}" font-size="11" fill="{ink}">'
                 f'{r["pred_tier"]} / {r["gold_tier"]}{mark}</text>')
    ly = H - 26
    p += [f'<circle cx="22" cy="{ly - 4}" r="5.5" fill="{blue}"/>',
          f'<text x="34" y="{ly}" font-size="12" fill="{ink}">cited by the analyzer</text>',
          f'<circle cx="182" cy="{ly - 4}" r="8.5" fill="none" stroke="{ink}" stroke-width="1.5"/>',
          f'<text x="198" y="{ly}" font-size="12" fill="{ink}">gold evidence (single-author)</text>',
          f'<rect x="392" y="{ly - 13}" width="22" height="16" fill="{band}" stroke="{rule}"/>',
          f'<text x="420" y="{ly}" font-size="12" fill="{ink}">differs from the matched negative</text>',
          f'<text x="16" y="{H - 8}" font-size="11" fill="{ink2}">* tier differs from gold. '
          'Citations from all constructs marked present or uncertain are merged per turn.</text>',
          "</svg>"]
    return "\n".join(p) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--items", default=str(ITEMS_PATH))
    ap.add_argument("--md-out", help="write the markdown report here")
    ap.add_argument("--svg-out", help="write the E2 figure here")
    ap.add_argument("--json-out", help="write the E2 per-item rows as JSON here")
    args = ap.parse_args(argv)

    items = {it["id"]: it for it in load_items(args.items)}
    runs = collect_runs(items)
    prim = primary_rows(runs)
    missing = sorted(set(items) - set(prim))
    if missing:
        sys.stderr.write(f"No v2 row for: {missing}\n")
    e2_rows = [e2_item(it, items[it["pair_id"]], prim[k]["output"])
               for k, it in items.items()
               if it["stratum"] == "hard_positive" and it.get("pair_id") and k in prim]
    md = render_report(items, runs, prim, e2_rows)
    if args.md_out:
        Path(args.md_out).write_text(md, encoding="utf-8")
    if args.svg_out:
        Path(args.svg_out).write_text(render_svg(e2_rows), encoding="utf-8")
    if args.json_out:
        Path(args.json_out).write_text(json.dumps(
            [{**r, "features": [[f, sorted(refs), ok] for f, refs, ok in r["features"]]} for r in e2_rows],
            indent=2), encoding="utf-8")
    sys.stdout.write(md)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
