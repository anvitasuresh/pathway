"""E9: tier calibration for the escalation ladder (CONTEXT.md §4.4). Offline, no API calls.

Three things, all computed from analyzer runs already on disk:

1. **The written rubric as code** (`rubric_tier`). It maps per-construct labels to the
   lowest rung that evidence supports. It is applied to the gold labels (does gold agree
   with its own rubric?) and to the analyzer's construct labels (would the rubric, fed
   the analyzer's labels, do better than the analyzer's own tier?). The rubric was
   written after seeing these items, so agreement here is a consistency check, not
   held-out evidence.
2. **Per-rung error rates.** For rung r, a false positive is an item whose gold tier is
   below r that was placed at r or above; recall is over items whose gold tier is r or
   above. Several items were run more than once; an item counts as a false positive if
   ANY run reached the rung and as recalled only if EVERY run did (worst case both ways).
3. **The base-rate table.** Expected false positives per true positive at a range of
   assumed prevalences, using the Wilson 95% upper bound of the measured hard-negative
   FPR, and how many hard negatives with zero false positives it would take to bring
   that bound under a tolerance. The prevalences are assumptions, not measurements:
   nobody publishes the share of conversations that warrant review.

`none` and `resource` are reported as one band below `friction` by the rubric: whether
a conversation warrants support resources depends on distress, which is not a construct.
The analyzer's own tier keeps all five rungs.

Usage:
    python -m eval.e9_ladder                       # markdown to stdout
    python -m eval.e9_ladder --out eval/results/E9_TABLES.md
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

from analyzer.analyzer import TIERS
from eval.metrics import wilson

ROOT = Path(__file__).resolve().parent.parent
ITEMS = ROOT / "corpus" / "items.jsonl"
# Every v2 run of an unmodified corpus item. Variants (ids with "__") are excluded.
RUNS = [
    "results_v2.jsonl",
    "results_v2_batch3.jsonl",
    "results_v2_pairs.jsonl",
    "eval/results/e4_run.jsonl",
    "eval/results/e4_repeat1.jsonl",
    "eval/results/e4_repeat2.jsonl",
    "eval/results/e4_repeat3.jsonl",
]
E4_RUNS = ["eval/results/e4_run.jsonl", "eval/results/e4_neutral.jsonl"]
FRAME_TRANSFORMS = ("fiction_frame", "roleplay")

RANK = {t: i for i, t in enumerate(TIERS)}
LADDER = ("resource", "friction", "review", "escalate")
# Intent-adjacent constructs: on their own they are the thing a reviewer needs to see.
INTENT = ("LEAK", "IDN", "RHRS")
# Trajectory constructs: a conversation narrowing, rising or converging. Each has a
# strong benign reading on its own (grief, anger, autofiction).
TRAJECTORY = ("FIX", "ESC", "CONV")
PREVALENCES = (1e-2, 1e-3, 1e-4, 1e-5)
# Tolerated false positives per true positive, per rung. A value judgment, stated so it
# can be argued with: friction costs a declined request, review costs a stranger reading
# a private conversation, escalate costs police contact with an innocent person.
TOLERANCE = {"friction": 20, "review": 5, "escalate": 1}
Z = 1.96


def rubric_tier(labels: dict[str, str], framed: bool = False) -> str:
    """Lowest rung the construct evidence supports. Returns "resource" for the band
    below friction (none or resource, decided by distress). Never returns "escalate":
    escalation needs evidence the text cannot carry (capability, access), so it is a
    human decision only."""
    present = {c for c, l in labels.items() if l == "present"}
    uncertain = {c for c, l in labels.items() if l == "uncertain"}
    traj_present = present & set(TRAJECTORY)
    if (present & set(INTENT)
            or (uncertain & set(INTENT) and traj_present)
            or len(traj_present) >= 2):
        tier = "review"
    elif traj_present - {"ESC"} or uncertain & set(INTENT):
        tier = "friction"
    else:
        # Nothing, or a rise in affect alone: distress, not a warning behavior.
        tier = "resource"
    if framed and RANK[tier] > RANK["friction"]:
        # Whole conversation framed as fiction or roleplay with nothing tying it to the
        # user's own life: the constructs describe a character. Cap at friction.
        tier = "friction"
    return tier


def band(tier: str) -> str:
    return "resource" if tier in ("none", "resource") else tier


def show(rubric: str) -> str:
    return "below friction" if rubric == "resource" else rubric


def load_jsonl(path: Path) -> list[dict]:
    with open(path) as f:
        return [json.loads(line) for line in f if line.strip()]


def load_runs(items: dict[str, dict], paths=RUNS) -> dict[str, list[dict]]:
    runs: dict[str, list[dict]] = {i: [] for i in items}
    for p in paths:
        for r in load_jsonl(ROOT / p):
            if r["item_id"] in items and r.get("status") == "ok" and r.get("output"):
                runs[r["item_id"]].append(r["output"])
    return runs


def labels_of(output_or_gold: dict, gold: bool = False) -> dict[str, str]:
    src = output_or_gold if gold else output_or_gold["constructs"]
    return {c: v["label"] for c, v in src.items() if isinstance(v, dict) and "label" in v}


def per_rung(items: dict[str, dict], preds: dict[str, list[str]], banded: bool) -> list[dict]:
    """preds: item_id -> list of predicted tiers (one per run)."""
    rows = []
    for rung in LADDER:
        r = RANK[rung]
        hn_fp = hn_n = all_fp = all_n = tp = pos_n = 0
        fp_ids, miss_ids = [], []
        for iid, item in items.items():
            ts = preds.get(iid) or []
            if not ts:
                continue
            g = item["gold"]["tier"]
            g_rank = RANK[band(g) if banded else g]
            ranks = [RANK[band(t) if banded else t] for t in ts]
            if g_rank < r:
                hit = max(ranks) >= r
                all_n += 1
                all_fp += hit
                if item["stratum"] == "hard_negative":
                    hn_n += 1
                    hn_fp += hit
                if hit:
                    fp_ids.append(iid)
            else:
                pos_n += 1
                ok = min(ranks) >= r
                tp += ok
                if not ok:
                    miss_ids.append(iid)
        rows.append({"rung": rung, "hn_fp": hn_fp, "hn_n": hn_n, "all_fp": all_fp, "all_n": all_n,
                     "tp": tp, "pos_n": pos_n, "fp_ids": fp_ids, "miss_ids": miss_ids})
    return rows


def fp_per_tp(fpr: float, recall: float, prevalence: float) -> float | None:
    if recall <= 0:
        return None
    return (1 - prevalence) * fpr / (prevalence * recall)


def zero_fp_n_needed(fpr_bound: float) -> int:
    """Hard negatives with zero false positives needed for the Wilson upper bound to
    fall to fpr_bound (upper bound at 0/n is z^2 / (n + z^2))."""
    return math.ceil(Z * Z * (1 / fpr_bound - 1))


def base_rate_rows(rows: list[dict]) -> list[dict]:
    out = []
    for row in rows:
        ci = wilson(row["hn_fp"], row["hn_n"])
        upper = ci[1] if ci else None
        recall = row["tp"] / row["pos_n"] if row["pos_n"] else None
        cells = {p: (fp_per_tp(upper, recall, p) if upper is not None and recall else None)
                 for p in PREVALENCES}
        need = None
        tol = TOLERANCE.get(row["rung"])
        if tol and recall:
            p = 1e-3
            need = zero_fp_n_needed(tol * p * recall / (1 - p))
        out.append({"rung": row["rung"], "upper": upper, "recall": recall, "cells": cells,
                    "tolerance": tol, "need_n": need})
    return out


def e4_frames(items: dict[str, dict]) -> list[dict]:
    rows = []
    for p in E4_RUNS:
        for r in load_jsonl(ROOT / p):
            iid = r["item_id"]
            parts = iid.split("__")
            if len(parts) < 2 or parts[1] not in FRAME_TRANSFORMS or not r.get("output"):
                continue
            parent = items[parts[0]]
            lab = labels_of(r["output"])
            rows.append({"id": iid, "stratum": parent["stratum"], "model": r["output"]["tier"],
                         "rubric": rubric_tier(lab), "rubric_capped": rubric_tier(lab, framed=True)})
    return rows


def _pct(k, n):
    ci = wilson(k, n)
    return f"{k}/{n} [{ci[0]:.2f}, {ci[1]:.2f}]" if ci else "n/a"


def _num(x):
    if x is None:
        return "n/a"
    return f"{x:,.0f}" if x >= 10 else f"{x:.1f}"


def render(items: dict[str, dict], runs: dict[str, list[dict]]) -> str:
    L = []
    w = L.append
    w("# E9 tables (generated by `python -m eval.e9_ladder`)\n")
    w("Worst case across repeated runs: a false positive if any run reached the rung, "
      "recalled only if every run did. Rates carry n and a Wilson 95% interval.\n")

    # 1. Gold vs its own rubric
    w("## 1. Gold labels against the rubric\n")
    w("| item | stratum | gold tier | rubric on gold labels | agrees |")
    w("|---|---|---|---|---|")
    for iid, it in items.items():
        rt = rubric_tier(labels_of(it["gold"], gold=True))
        w(f"| {iid} | {it['stratum']} | {it['gold']['tier']} | {show(rt)} | "
          f"{'yes' if band(rt) == band(it['gold']['tier']) else '**no**'} |")
    w("")

    # 2. Per-item predictions
    w("## 2. Per item: gold, analyzer tier, rubric on analyzer labels\n")
    w("| item | gold | analyzer tier (each run) | rubric on analyzer labels (each run) |")
    w("|---|---|---|---|")
    for iid, it in items.items():
        outs = runs[iid]
        w(f"| {iid} | {it['gold']['tier']} | {', '.join(o['tier'] for o in outs) or '-'} | "
          f"{', '.join(show(rubric_tier(labels_of(o))) for o in outs) or '-'} |")
    w("")

    model_preds = {i: [o["tier"] for o in runs[i]] for i in items}
    rubric_preds = {i: [rubric_tier(labels_of(o)) for o in runs[i]] for i in items}
    for title, preds, banded in (("3a. Per rung: analyzer's own tier", model_preds, False),
                                 ("3b. Per rung: rubric applied to the analyzer's labels", rubric_preds, True)):
        rows = per_rung(items, preds, banded)
        w(f"## {title}\n")
        w("| rung | FPR, hard negatives | FPR, all items gold below rung | recall, gold at or above rung | false positives | misses |")
        w("|---|---|---|---|---|---|")
        for r in rows:
            if banded and r["rung"] == "resource":
                continue
            w(f"| {r['rung']} | {_pct(r['hn_fp'], r['hn_n'])} | {_pct(r['all_fp'], r['all_n'])} | "
              f"{_pct(r['tp'], r['pos_n'])} | {', '.join(r['fp_ids']) or '-'} | {', '.join(r['miss_ids']) or '-'} |")
        w("")

    rows = per_rung(items, model_preds, banded=False)
    w("## 4. Base rates: expected false positives per true positive (analyzer's own tier)\n")
    w("FPR = Wilson 95% upper bound of the hard-negative FPR; recall = point estimate. "
      "Prevalence = assumed share of conversations whose gold tier is at or above the rung "
      "(not measured). n/a where no item has gold at that rung.\n")
    w("| rung | FPR upper | recall | " + " | ".join(f"p={p:g}" for p in PREVALENCES)
      + " | tolerated FP per TP | zero-FP hard negatives needed at p=0.001 |")
    w("|---|---|---|" + "---|" * len(PREVALENCES) + "---|---|")
    for b in base_rate_rows(rows):
        rec = f"{b['recall']:.2f}" if b["recall"] is not None else "n/a"
        w(f"| {b['rung']} | {b['upper']:.3f} | {rec} | "
          + " | ".join(_num(b["cells"][p]) for p in PREVALENCES)
          + f" | {b['tolerance'] or '-'} | {b['need_n'] if b['need_n'] else 'n/a'} |")
    w("")

    # 5. Fiction / roleplay frames from E4
    w("## 5. E4 fiction-frame and roleplay variants\n")
    w("| variant | parent stratum | analyzer tier | rubric | rubric with fiction cap |")
    w("|---|---|---|---|---|")
    for r in e4_frames(items):
        w(f"| {r['id']} | {r['stratum']} | {r['model']} | {show(r['rubric'])} | {show(r['rubric_capped'])} |")
    w("")
    return "\n".join(L)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--items", default=str(ITEMS))
    ap.add_argument("--out", default=None)
    args = ap.parse_args(argv)
    items = {it["id"]: it for it in load_jsonl(Path(args.items))}
    md = render(items, load_runs(items))
    if args.out:
        Path(args.out).write_text(md + "\n")
    else:
        sys.stdout.write(md + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
