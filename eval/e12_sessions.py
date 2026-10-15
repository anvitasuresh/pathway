"""E12: what does remembering a refusal across sessions cost?

Today a refusal is forgotten when the session ends (CONTEXT.md §4.3). Carrying it into
the next session catches someone who comes back tomorrow with a pretext, but it can also
treat an ordinary new request as a second try at the old one. E12 measures that trade on
corpus/refusal_sessions.jsonl: 15 harmless two-session items. Session 1 holds a refusal
(or not); session 2 is either a re-request of the refused item (positive) or a new,
legitimate request that shares its topic words or a frame phrase (hard negative).

A tracker flags an item when it links a session-2 user turn back to a session-1 refusal
as an attempt (pretext or reask). Arms:

    reset         rule tracker, state dropped at each session boundary (deployed
                  default). Cannot flag anything by construction; in the table so the
                  comparison is explicit
    carry_any     baseline: any session-1 refusal flags session 2, which is what an
                  always-injected refusal reminder (E8) amounts to
    rules_carry   rule tracker, refusals carried, adjacency never crosses a boundary
    rules_concat  rule tracker on the histories simply appended
    model_carry   model tracker (prompt v3) on the full two-session transcript with a
                  session marker. Needs --model; one call per item (15). The model
                  tracker under reset would need no calls: with session 1 removed there
                  is nothing to link to

Headline: false-positive rate on hard negatives, per arm. No pooled accuracy.

Usage:
    python -m eval.e12_sessions                                   # offline arms
    python -m eval.e12_sessions --model --dry-run                 # show the 15 calls
    python -m eval.e12_sessions --model --out eval/results/e12_run.jsonl
    python -m eval.e12_sessions --preds eval/results/e12_run.jsonl   # re-score, no calls
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from analyzer.analyzer import load_items, load_prompt, render_transcript
from analyzer.refusal_state import REFUSAL_PROMPT, RefusalState, detect_refusal, session_of, track_model, track_rules
from eval.metrics import STRATA, _fmt, check_no_pooled, rate

DEFAULT_ITEMS = Path(__file__).resolve().parent.parent / "corpus" / "refusal_sessions.jsonl"
ARMS = ("reset", "carry_any", "rules_carry", "rules_concat", "model_carry")


def gold(item: dict) -> dict:
    xs = item["cross_session"]
    return {"attempt": xs["attempt"], "reframe_turn": xs.get("reframe_turn") if xs["attempt"] else None}


def cross_attempts(item: dict, state: RefusalState) -> list:
    """Attempts in a later session that the tracker tied to an earlier session's refusal."""
    sess = {int(t["i"]): session_of(t) for t in item["turns"]}
    return [r for r in state.attempts if sess.get(r.turn, 0) > sess.get(r.refusal_turn, 0)]


def _row(item: dict, arm: str, status: str, state: RefusalState | None, **extra) -> dict:
    row = {"item_id": item["id"], "arm": arm, "status": status}
    if state is not None:
        xs = cross_attempts(item, state)
        row.update(flag=bool(xs), turn=xs[0].turn if xs else None,
                   kinds=sorted({r.kind for r in xs}), state=state.to_dict())
    row.update(extra)
    return row


def predict_offline(item: dict) -> list[dict]:
    sess1_refusal = any(t["role"] == "assistant" and session_of(t) == session_of(item["turns"][0])
                        and detect_refusal(t["text"]) for t in item["turns"])
    later = [int(t["i"]) for t in item["turns"] if t["role"] == "user"
             and session_of(t) > session_of(item["turns"][0])]
    rows = [{"item_id": item["id"], "arm": "carry_any", "status": "ok", "flag": sess1_refusal,
             "turn": later[0] if sess1_refusal and later else None, "kinds": []}]
    for arm, mode in (("reset", "reset"), ("rules_carry", "carry"), ("rules_concat", "concat")):
        rows.append(_row(item, arm, "ok", track_rules(item, sessions=mode)))
    return rows


def predict_model(item: dict, backend, prompt=None) -> dict:
    res = track_model(item, backend, prompt)
    return _row(item, "model_carry", res.status, res.state, model=res.model,
                prompt_version=res.prompt_version, errors=res.errors)


# ---------------------------------------------------------------------- scoring

def _cell(items: list[dict], preds: dict[str, dict]) -> dict:
    scored = [(it, preds[it["id"]]) for it in items
              if it["id"] in preds and preds[it["id"]].get("status") == "ok"]
    pos = [(it, p) for it, p in scored if gold(it)["attempt"]]
    neg = [(it, p) for it, p in scored if not gold(it)["attempt"]]
    hits = [(it, p) for it, p in pos if p["flag"]]
    return {
        "n_items": len(items),
        "n_scored": len(scored),
        "fpr": rate(sum(p["flag"] for _, p in neg), len(neg)),
        "recall": rate(len(hits), len(pos)),
        "turn_correct": rate(sum(p["turn"] == gold(it)["reframe_turn"] for it, p in hits), len(hits)),
        "false_positive_ids": sorted(it["id"] for it, p in neg if p["flag"]),
        "missed_ids": sorted(it["id"] for it, p in pos if not p["flag"]),
    }


def build_report(items: list[dict], rows: list[dict]) -> dict:
    by_arm: dict[str, dict[str, dict]] = {}
    for r in rows:
        by_arm.setdefault(r["arm"], {})[r["item_id"]] = r
    strata = [s for s in STRATA if any(it["stratum"] == s for it in items)]
    report: dict = {"n_items": len(items), "arms": {}}
    for arm in [a for a in ARMS if a in by_arm]:
        preds = by_arm[arm]
        statuses: dict[str, int] = {}
        for it in items:
            st = preds.get(it["id"], {}).get("status", "missing")
            statuses[st] = statuses.get(st, 0) + 1
        report["arms"][arm] = {
            "by_stratum": {s: _cell([it for it in items if it["stratum"] == s], preds) for s in strata},
            "status_counts": statuses,
        }
    report["headline"] = {
        a: {"hard_negative_fpr": rep["by_stratum"].get("hard_negative", {}).get("fpr"),
            "clear_negative_fpr": rep["by_stratum"].get("clear_negative", {}).get("fpr"),
            "positive_recall": rate(
                sum(rep["by_stratum"][s]["recall"]["k"] for s in ("clear_positive", "hard_positive")
                    if s in rep["by_stratum"]),
                sum(rep["by_stratum"][s]["recall"]["n"] for s in ("clear_positive", "hard_positive")
                    if s in rep["by_stratum"]))}
        for a, rep in report["arms"].items()
    }
    check_no_pooled(report)
    return report


def render_markdown(report: dict) -> str:
    out = ["# E12 refusal state across sessions (per stratum; no pooled accuracy)", "",
           f"{report['n_items']} two-session items. A flag = the tracker ties a session-2 "
           "request back to a session-1 refusal as a second attempt.", "",
           "## Headline", "",
           "| Arm | Hard-negative FPR | Clear-negative FPR | Recall on positives (clear + hard) |",
           "|---|---|---|---|"]
    for a, h in report["headline"].items():
        out.append(f"| {a} | {_fmt(h['hard_negative_fpr'])} | {_fmt(h['clear_negative_fpr'])} | "
                   f"{_fmt(h['positive_recall'])} |")
    for a, rep in report["arms"].items():
        out += ["", f"## {a}", "", f"Statuses: {rep['status_counts']}", "",
                "| Stratum | FPR | Recall | Session-2 turn right |", "|---|---|---|---|"]
        for s, c in rep["by_stratum"].items():
            out.append(f"| {s} | {_fmt(c['fpr'])} | {_fmt(c['recall'])} | {_fmt(c['turn_correct'])} |")
        fps = sorted({i for c in rep["by_stratum"].values() for i in c["false_positive_ids"]})
        miss = sorted({i for c in rep["by_stratum"].values() for i in c["missed_ids"]})
        out += ["", f"False positives: {fps or 'none'}", f"Missed: {miss or 'none'}"]
    out += ["", "Items were written by the project author before any tracker ran on them and "
            "nothing was tuned afterwards, but they are 15 items from one author: the intervals "
            "are wide and the strata are small."]
    return "\n".join(out) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--items", default=str(DEFAULT_ITEMS))
    ap.add_argument("--model", action="store_true", help="also run model_carry (one API call per item)")
    ap.add_argument("--model-id", default=None)
    ap.add_argument("--dry-run", action="store_true", help="with --model: print the calls, send nothing")
    ap.add_argument("--preds", help="re-score saved rows from this JSONL instead of running")
    ap.add_argument("--out", help="write prediction rows here")
    ap.add_argument("--json-out", help="write the report as JSON here")
    args = ap.parse_args(argv)

    items = load_items(args.items)
    if args.preds:
        rows = load_items(args.preds)
    else:
        prompt = load_prompt(REFUSAL_PROMPT)
        if args.model and args.dry_run:
            print(f"# E12 model_carry dry run: prompt {prompt.version}, {len(items)} API calls\n")
            for it in items:
                print(f"## {it['id']}\n{render_transcript(it)}\n")
            return 0
        rows = [r for it in items for r in predict_offline(it)]
        if args.model:
            from analyzer.analyzer import AnthropicBackend

            backend = AnthropicBackend(model=args.model_id)
            for n, it in enumerate(items, 1):
                rows.append(predict_model(it, backend, prompt))
                print(f"model {n}/{len(items)}: {it['id']} {rows[-1]['status']}", file=sys.stderr)
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        with open(args.out, "w", encoding="utf-8") as fh:
            for r in rows:
                fh.write(json.dumps(r, ensure_ascii=False) + "\n")

    report = build_report(items, rows)
    if args.json_out:
        with open(args.json_out, "w", encoding="utf-8") as fh:
            json.dump(report, fh, indent=2)
    sys.stdout.write(render_markdown(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
