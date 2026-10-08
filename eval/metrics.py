"""Stratum-wise metrics for analyzer runs (CLAUDE.md §7, E1).

Rules this module enforces:

* Every number is reported per stratum, and per construct where it applies. There is
  no pooled accuracy, anywhere. `pooled_accuracy()` exists only to raise, and every
  report is checked for an accuracy key before it is returned.
* False-positive rate on hard negatives is the headline, reported first, at both the
  construct level and the item level ("would this person have been flagged at all?").
* Tier errors are split into over- and under-escalation, because they cost different
  people different things.
* Items the analyzer failed on (refusal, invalid output, missing) are counted, never
  silently dropped and never counted as correct.
* Every rate carries its n and a Wilson 95% interval. With ~6-12 items per stratum
  the intervals are wide, and the report should make that impossible to miss.

Usage:
    python -m eval.metrics --items corpus/items.jsonl --preds eval/results/run.jsonl
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from collections import Counter
from typing import Any, Iterable

from analyzer.analyzer import CONSTRUCTS, LABELS, TIERS, load_items

# Hard negatives first: that is the order a reader should meet them in.
STRATA = ("hard_negative", "hard_positive", "clear_positive", "clear_negative")
TIER_RANK = {t: i for i, t in enumerate(TIERS)}
# Tiers at which a human, or someone outside the platform, is brought in.
REVIEW_OR_ABOVE = {"review", "escalate"}


class PooledAccuracyError(RuntimeError):
    pass


def pooled_accuracy(*_args: Any, **_kwargs: Any) -> float:
    """Deliberately not implemented. See module docstring and CLAUDE.md §7."""
    raise PooledAccuracyError(
        "Pathway does not report pooled accuracy. On a corpus that is half clear cases "
        "it hides the only errors that matter. Use the per-stratum, per-construct "
        "report, and lead with false-positive rate on hard negatives."
    )


def check_no_pooled(report: Any, path: str = "report") -> None:
    """Raise if any key in a report looks like an accuracy number."""
    if isinstance(report, dict):
        for key, value in report.items():
            if "accuracy" in str(key).lower():
                raise PooledAccuracyError(f"{path}.{key}: accuracy keys are not allowed")
            check_no_pooled(value, f"{path}.{key}")
    elif isinstance(report, list):
        for i, value in enumerate(report):
            check_no_pooled(value, f"{path}[{i}]")


# --------------------------------------------------------------------------- rates

def wilson(k: int, n: int, z: float = 1.96) -> list[float] | None:
    if n == 0:
        return None
    p = k / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return [round(max(0.0, centre - half), 4), round(min(1.0, centre + half), 4)]


def rate(k: int, n: int) -> dict:
    return {"k": k, "n": n, "rate": round(k / n, 4) if n else None, "ci95": wilson(k, n)}


# ------------------------------------------------------------------ gold accessors
# Centralized so a change in corpus/SCHEMA.md touches one place.

def stratum_of(item: dict) -> str:
    return item.get("stratum", "unknown")


def gold_label(item: dict, construct: str) -> str:
    return item["gold"][construct]["label"]


def gold_evidence(item: dict, construct: str) -> set[int]:
    return set(item["gold"][construct].get("evidence", []))


def gold_tier(item: dict) -> str:
    return item["gold"]["tier"]


# -------------------------------------------------------------------- predictions

def index_predictions(results: Iterable[dict]) -> dict[str, dict]:
    """Map item_id -> result row (as written by analyzer.analyzer). Last row wins."""
    return {r["item_id"]: r for r in results}


def pred_finding(result: dict, construct: str) -> tuple[str, set[int]]:
    finding = result["output"]["constructs"][construct]
    return finding["label"], set(finding.get("evidence_turns", []))


def is_scored(result: dict | None) -> bool:
    return bool(result) and result.get("status") == "ok" and result.get("output") is not None


# ---------------------------------------------------------------------- per stratum

def _construct_metrics(pairs: list[tuple[dict, dict]], construct: str) -> dict:
    confusion = {g: {p: 0 for p in LABELS} for g in LABELS}
    tp = fp = fn = 0  # strict: only "present" counts as a positive call
    fp_lenient = 0  # present or uncertain on a gold-absent item
    gold_absent = gold_positive = 0
    overlaps: list[float] = []
    right_label_wrong_turns = 0

    for item, result in pairs:
        g = gold_label(item, construct)
        p, cited = pred_finding(result, construct)
        confusion[g][p] += 1
        if g == "absent":
            gold_absent += 1
            fp += p == "present"
            fp_lenient += p in ("present", "uncertain")
        elif g == "present":
            gold_positive += 1
            if p == "present":
                tp += 1
                gold_turns = gold_evidence(item, construct)
                if gold_turns:
                    union = cited | gold_turns
                    overlaps.append(len(cited & gold_turns) / len(union))
                    right_label_wrong_turns += not (cited & gold_turns)
            else:
                fn += 1
        # gold "uncertain" is excluded from P/R and FPR; it stays visible in `confusion`.

    return {
        "confusion_gold_by_pred": confusion,
        "precision": rate(tp, tp + fp),
        "recall": rate(tp, gold_positive),
        "fpr": rate(fp, gold_absent),
        "fpr_lenient": rate(fp_lenient, gold_absent),
        "evidence": {
            "true_positives_with_gold_evidence": len(overlaps),
            "mean_jaccard": round(sum(overlaps) / len(overlaps), 4) if overlaps else None,
            "right_label_no_overlap": right_label_wrong_turns,
        },
    }


def _tier_metrics(pairs: list[tuple[dict, dict]]) -> dict:
    confusion = {g: {p: 0 for p in TIERS} for g in TIERS}
    over = under = review_or_above = 0
    for item, result in pairs:
        g, p = gold_tier(item), result["output"]["tier"]
        confusion[g][p] += 1
        over += TIER_RANK[p] > TIER_RANK[g]
        under += TIER_RANK[p] < TIER_RANK[g]
        review_or_above += p in REVIEW_OR_ABOVE
    n = len(pairs)
    return {
        "confusion_gold_by_pred": confusion,
        "over_escalation": rate(over, n),
        "under_escalation": rate(under, n),
        "predicted_review_or_above": rate(review_or_above, n),
    }


def stratum_report(items: list[dict], preds: dict[str, dict]) -> dict:
    statuses = Counter(
        (preds[it["id"]].get("status", "unknown") if it["id"] in preds else "missing")
        for it in items
    )
    pairs = [(it, preds[it["id"]]) for it in items if is_scored(preds.get(it["id"]))]
    report: dict = {
        "n_items": len(items),
        "n_scored": len(pairs),
        "status_counts": dict(sorted(statuses.items())),
        "constructs": {c: _construct_metrics(pairs, c) for c in CONSTRUCTS},
        "tier": _tier_metrics(pairs),
    }
    any_flag = sum(
        any(pred_finding(r, c)[0] == "present" for c in CONSTRUCTS) for _, r in pairs
    )
    report["items_with_any_present"] = rate(any_flag, len(pairs))
    return report


# --------------------------------------------------------------------------- report

def build_report(items: list[dict], results: Iterable[dict]) -> dict:
    preds = index_predictions(results)
    by_stratum: dict[str, list[dict]] = {}
    for it in items:
        by_stratum.setdefault(stratum_of(it), []).append(it)
    order = [s for s in STRATA if s in by_stratum] + sorted(set(by_stratum) - set(STRATA))
    strata = {s: stratum_report(by_stratum[s], preds) for s in order}

    meta_rows = [preds[it["id"]] for it in items if it["id"] in preds]
    meta = {
        "prompt_versions": sorted({r.get("prompt_version") for r in meta_rows} - {None}),
        "models": sorted({r.get("model") for r in meta_rows} - {None}),
        "efforts": sorted({str(r.get("effort")) for r in meta_rows}),
        "unmatched_prediction_ids": sorted(set(preds) - {it["id"] for it in items}),
    }

    hn = strata.get("hard_negative")
    headline = None
    if hn is not None:
        headline = {
            "hard_negative_item_flag_rate": hn["items_with_any_present"],
            "hard_negative_fpr_by_construct": {
                c: hn["constructs"][c]["fpr"] for c in CONSTRUCTS
            },
            "hard_negative_over_escalation": hn["tier"]["over_escalation"],
            "hard_negative_review_or_above": hn["tier"]["predicted_review_or_above"],
            "hard_negative_unscored": hn["n_items"] - hn["n_scored"],
        }

    report = {"meta": meta, "headline": headline, "strata": strata}
    check_no_pooled(report)
    return report


def _fmt(r: dict) -> str:
    if r["rate"] is None:
        return f"n/a (0/{r['n']})"
    lo, hi = r["ci95"]
    return f"{r['rate']:.2f} ({r['k']}/{r['n']}; 95% CI {lo:.2f}-{hi:.2f})"


def render_markdown(report: dict) -> str:
    out = ["# Analyzer metrics (stratum-wise; no pooled accuracy)", ""]
    m = report["meta"]
    out.append(f"Prompt: {', '.join(m['prompt_versions']) or '?'} · Model: "
               f"{', '.join(m['models']) or '?'} · Effort: {', '.join(m['efforts'])}")
    if m["unmatched_prediction_ids"]:
        out.append(f"\nPredictions with no corpus item: {m['unmatched_prediction_ids']}")

    h = report["headline"]
    out += ["", "## Headline: false positives on hard negatives", ""]
    if h is None:
        out.append("No hard-negative items in this corpus, so there is no headline number. "
                   "That is a corpus problem, not a pass.")
    else:
        out.append(f"- Hard negatives with any construct flagged present: "
                   f"{_fmt(h['hard_negative_item_flag_rate'])}")
        out.append(f"- Hard negatives routed to review or above: "
                   f"{_fmt(h['hard_negative_review_or_above'])}")
        out.append(f"- Hard negatives over-escalated vs. gold tier: "
                   f"{_fmt(h['hard_negative_over_escalation'])}")
        out.append(f"- Hard negatives not scored (refusal/invalid/missing): "
                   f"{h['hard_negative_unscored']}")
        out += ["", "| Construct | FPR on hard negatives |", "|---|---|"]
        for c, r in h["hard_negative_fpr_by_construct"].items():
            out.append(f"| {c} | {_fmt(r)} |")

    for s, sr in report["strata"].items():
        out += ["", f"## Stratum: {s}", "",
                f"Items {sr['n_items']}, scored {sr['n_scored']}, statuses {sr['status_counts']}",
                "", "| Construct | Precision | Recall | FPR | FPR incl. uncertain |",
                "|---|---|---|---|---|"]
        for c, cr in sr["constructs"].items():
            out.append(f"| {c} | {_fmt(cr['precision'])} | {_fmt(cr['recall'])} | "
                       f"{_fmt(cr['fpr'])} | {_fmt(cr['fpr_lenient'])} |")
        t = sr["tier"]
        out += ["", f"Over-escalation {_fmt(t['over_escalation'])}; "
                    f"under-escalation {_fmt(t['under_escalation'])}", "",
                "Tier confusion (rows gold, columns predicted):", "",
                "| gold \\ pred | " + " | ".join(TIERS) + " |",
                "|---" * (len(TIERS) + 1) + "|"]
        for g in TIERS:
            row = t["confusion_gold_by_pred"][g]
            out.append(f"| {g} | " + " | ".join(str(row[p]) for p in TIERS) + " |")
    return "\n".join(out) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--items", required=True, help="corpus JSONL with gold labels")
    ap.add_argument("--preds", required=True, help="analyzer results JSONL")
    ap.add_argument("--json-out", help="write the full report as JSON here")
    args = ap.parse_args(argv)

    report = build_report(load_items(args.items), load_items(args.preds))
    if args.json_out:
        with open(args.json_out, "w", encoding="utf-8") as fh:
            json.dump(report, fh, indent=2)
    sys.stdout.write(render_markdown(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
