"""E3: does the analyzer's cited evidence actually carry its finding?

For every finding the analyzer flags (a construct labeled present or uncertain, with
cited turns), remove the cited turns and run the analyzer again. As a control, remove
the same number of turns chosen at random from the whole conversation. If the
explanation is faithful, removing the cited turns should flip the finding much more
often than removing random ones (CONTEXT.md §7, E3).

Two scopes:

    construct   remove one construct's cited turns; did that construct's label flip?
                (present -> absent or uncertain; uncertain -> absent)
    item        remove the union of every flagged construct's cited turns; did the
                tier drop, and did every construct stop being present?

Removal unit: a cited user turn is removed together with the assistant reply that
follows it, since the reply would otherwise restate what was removed. A cited assistant
turn is removed alone. Random controls match the cited turns' count and user/assistant
mix and are removed the same way. They may include cited turns (see `random_anchors`);
the report gives, per finding, the share of the conversation the cited ablation removed
and how much the random draws overlapped the cited turns. A finding that cites most of
the conversation is not much of an explanation, whatever its flip rate. Surviving turns are renumbered from 0 so the
transcript has no visible gaps; `index_map` in each row maps new indices back.

How to read a non-flip: either the explanation is unfaithful (the finding rests on
something it did not cite) or the signal is redundant (it also lives in turns it did not
cite). The report lists, for every non-flip, what the analyzer cited after ablation, so
the two can be told apart by reading. That reading is the analysis; the flip rate alone
is not.

Every rate is per stratum and per construct with n and a Wilson 95% CI. No pooled
accuracy. Random-control draws are counted as separate trials, which slightly overstates
the precision of the control rate.

Usage:
    python -m eval.e3_faithfulness --dry-run --baseline results_v2.jsonl results_v2_pairs.jsonl
    python -m eval.e3_faithfulness --out eval/results/e3_run.jsonl
    python -m eval.e3_faithfulness --preds eval/results/e3_run.jsonl
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

from analyzer.analyzer import (CONSTRUCTS, DEFAULT_PROMPT, AnthropicBackend, analyze, load_items,
                               load_prompt, render_transcript)
from eval.metrics import STRATA, TIER_RANK, _fmt, check_no_pooled, rate

ROOT = Path(__file__).resolve().parent.parent
ITEMS_PATH = ROOT / "corpus" / "items.jsonl"
FLAGGED = ("present", "uncertain")


# ---------------------------------------------------------------------- ablation

def removal_unit(item: dict, i: int) -> set[int]:
    turns = item["turns"]
    unit = {i}
    if turns[i]["role"] == "user" and i + 1 < len(turns) and turns[i + 1]["role"] == "assistant":
        unit.add(i + 1)
    return unit


def removal_set(item: dict, anchors: set[int]) -> set[int]:
    out: set[int] = set()
    for i in anchors:
        out |= removal_unit(item, i)
    return out


def ablate(item: dict, remove: set[int], new_id: str) -> dict:
    kept = [t for t in item["turns"] if int(t["i"]) not in remove]
    return {
        "id": new_id,
        "stratum": item["stratum"],
        "turns": [{"i": n, "role": t["role"], "text": t["text"]} for n, t in enumerate(kept)],
        "index_map": {str(n): int(t["i"]) for n, t in enumerate(kept)},
    }


def random_anchors(item: dict, cited: set[int], rng: random.Random) -> set[int] | None:
    """As many random turns as were cited, with the same mix of user and assistant
    turns, drawn from the whole conversation (cited turns included). None if the
    conversation has too few turns of a role.

    The draw includes cited turns on purpose. The analyzer often cites most of a
    conversation, and a control restricted to uncited turns would then be impossible
    for exactly the broadest findings. Drawing from everything keeps the control
    defined for every finding; the price is that a random draw overlaps the cited turns
    more when the citation is less selective, which `selectivity` in the report shows.
    """
    roles = {int(t["i"]): t["role"] for t in item["turns"]}
    chosen: set[int] = set()
    taken: set[int] = set()
    for role in ("user", "assistant"):
        need = sum(roles[i] == role for i in cited)
        pool = [i for i, r in roles.items() if r == role]
        rng.shuffle(pool)
        got = 0
        for i in pool:
            if got == need:
                break
            unit = removal_unit(item, i) if role == "user" else {i}
            if unit & taken:
                continue
            chosen.add(i)
            taken |= unit
            got += 1
        if got < need:
            return None
    return chosen


def plan(item: dict, baseline: dict, draws: int = 2, seed: int = 0) -> list[dict]:
    """Every ablation to run for one item, given its baseline analyzer row."""
    out = baseline["output"]
    targets: list[tuple[str, set[int]]] = []
    for c in CONSTRUCTS:
        f = out["constructs"][c]
        if f["label"] in FLAGGED and f["evidence_turns"]:
            targets.append((c, set(f["evidence_turns"])))
    if targets:
        targets.append(("ITEM", set().union(*(t for _, t in targets))))

    jobs = []
    for scope_c, cited in targets:
        remove = removal_set(item, cited)
        base = dict(parent_id=item["id"], target=scope_c, cited=sorted(cited))
        if len(remove) >= len(item["turns"]) or not any(
                item["turns"][i]["role"] == "user" for i in range(len(item["turns"])) if i not in remove):
            jobs.append(dict(base, condition="cited", status="skipped_empty"))
            continue
        jobs.append(dict(base, condition="cited", removed=sorted(remove),
                         removed_share=round(len(remove) / len(item["turns"]), 4),
                         item=ablate(item, remove, f"{item['id']}__e3_{scope_c}_cited")))
        rng = random.Random(f"{seed}:{item['id']}:{scope_c}")
        for d in range(draws):
            anchors = random_anchors(item, cited, rng)
            if anchors is None:
                jobs.append(dict(base, condition="random", draw=d, status="skipped_no_control"))
                continue
            r_remove = removal_set(item, anchors)
            jobs.append(dict(base, condition="random", draw=d, anchors=sorted(anchors), removed=sorted(r_remove),
                             overlap_with_cited=round(len(anchors & cited) / len(cited), 4),
                             item=ablate(item, r_remove, f"{item['id']}__e3_{scope_c}_random{d}")))
    return jobs


# ------------------------------------------------------------------------ scoring

def flipped(target: str, before: dict, after: dict) -> bool:
    if target == "ITEM":
        return TIER_RANK[after["tier"]] < TIER_RANK[before["tier"]]
    b = before["constructs"][target]["label"]
    a = after["constructs"][target]["label"]
    return (b == "present" and a != "present") or (b == "uncertain" and a == "absent")


def _ok(row: dict | None) -> bool:
    return bool(row) and row.get("status") == "ok" and row.get("output") is not None


def _mean(xs: list[float]) -> float | None:
    return round(sum(xs) / len(xs), 4) if xs else None


def build_report(items: list[dict], rows: list[dict]) -> dict:
    by_id = {it["id"]: it for it in items}
    base = {r["item_id"]: r for r in rows if r.get("e3_role") == "baseline"}
    abl = [r for r in rows if r.get("e3_role") == "ablation"]

    cells: dict = {}
    details = []
    for r in abl:
        pid, target, cond = r["parent_id"], r["target"], r["condition"]
        stratum = by_id[pid]["stratum"] if pid in by_id else "unknown"
        cell = cells.setdefault(stratum, {}).setdefault(target, {
            "cited": {"k": 0, "n": 0, "unscored": 0}, "random": {"k": 0, "n": 0, "unscored": 0},
            "any_present_cleared_cited": {"k": 0, "n": 0}, "removed_share": [], "overlap": []})
        slot = cell[cond]
        if "removed_share" in r:
            cell["removed_share"].append(r["removed_share"])
        if "overlap_with_cited" in r:
            cell["overlap"].append(r["overlap_with_cited"])
        b = base.get(pid)
        if r.get("status", "").startswith("skipped") or not (_ok(r) and _ok(b)):
            slot["unscored"] += 1
            continue
        f = flipped(target, b["output"], r["output"])
        slot["n"] += 1
        slot["k"] += f
        if target == "ITEM" and cond == "cited":
            cleared = not any(r["output"]["constructs"][c]["label"] == "present" for c in CONSTRUCTS)
            cell["any_present_cleared_cited"]["n"] += 1
            cell["any_present_cleared_cited"]["k"] += cleared
        if cond == "cited":
            imap = {int(k): v for k, v in r["index_map"].items()}
            if target == "ITEM":
                after = {"tier": r["output"]["tier"]}
                before = {"tier": b["output"]["tier"]}
            else:
                fa = r["output"]["constructs"][target]
                after = {"label": fa["label"], "cites_original_turns": sorted(imap[i] for i in fa["evidence_turns"] if i in imap)}
                before = {"label": b["output"]["constructs"][target]["label"], "cited": r["cited"]}
            details.append({"item": pid, "target": target, "flipped": f, "before": before, "after": after})

    strata = {}
    order = [s for s in STRATA if s in cells] + sorted(set(cells) - set(STRATA))
    for s in order:
        strata[s] = {}
        for target in [c for c in CONSTRUCTS + ("ITEM",) if c in cells[s]]:
            cell = cells[s][target]
            cited = rate(cell["cited"]["k"], cell["cited"]["n"])
            rnd = rate(cell["random"]["k"], cell["random"]["n"])
            strata[s][target] = {
                "flip_cited": cited,
                "flip_random": rnd,
                "gap": round(cited["rate"] - rnd["rate"], 4) if cited["rate"] is not None and rnd["rate"] is not None else None,
                "unscored_cited": cell["cited"]["unscored"],
                "unscored_random": cell["random"]["unscored"],
                "mean_share_of_conversation_removed_cited": _mean(cell["removed_share"]),
                "mean_random_overlap_with_cited": _mean(cell["overlap"]),
            }
            if target == "ITEM":
                acc = cell["any_present_cleared_cited"]
                strata[s][target]["all_constructs_cleared_cited"] = rate(acc["k"], acc["n"])

    meta_rows = list(base.values()) + abl
    report = {
        "meta": {
            "prompt_versions": sorted({r.get("prompt_version") for r in meta_rows} - {None}),
            "models": sorted({r.get("model") for r in meta_rows} - {None}),
            "n_baseline": len(base),
            "n_baseline_ok": sum(_ok(r) for r in base.values()),
            "n_ablations": len(abl),
        },
        "strata": strata,
        "cited_ablations": details,
    }
    check_no_pooled(report)
    return report


def render_markdown(report: dict) -> str:
    m = report["meta"]
    out = ["# E3 faithfulness (per stratum and construct; no pooled accuracy)", "",
           f"Prompt: {', '.join(m['prompt_versions']) or '?'} · Model: {', '.join(m['models']) or '?'}",
           f"Baseline rows {m['n_baseline']} ({m['n_baseline_ok']} ok); ablation rows {m['n_ablations']}.", "",
           "Flip = the finding changes after removal (construct: present to absent/uncertain, or "
           "uncertain to absent; ITEM: tier drops). A faithful explanation flips much more often "
           "when its cited turns are removed than when random turns are."]
    if not report["strata"]:
        out += ["", "No flagged findings in the baseline, so there is nothing to ablate. On hard "
                "negatives that is the expected outcome, not a gap in the run."]
    for s, targets in report["strata"].items():
        out += ["", f"## Stratum: {s}", "",
                "| Finding | Flip: cited removed | Flip: random removed | Gap | Share of conversation "
                "removed (cited) | Random overlap with cited | Unscored (cited / random) |",
                "|---|---|---|---|---|---|---|"]
        for t, c in targets.items():
            gap = "n/a" if c["gap"] is None else f"{c['gap']:+.2f}"
            share = c["mean_share_of_conversation_removed_cited"]
            ov = c["mean_random_overlap_with_cited"]
            out.append(f"| {t} | {_fmt(c['flip_cited'])} | {_fmt(c['flip_random'])} | {gap} | "
                       f"{'n/a' if share is None else f'{share:.2f}'} | {'n/a' if ov is None else f'{ov:.2f}'} | "
                       f"{c['unscored_cited']} / {c['unscored_random']} |")
        if "ITEM" in targets and "all_constructs_cleared_cited" in targets["ITEM"]:
            out.append(f"\nITEM, cited removed: no construct left present in "
                       f"{_fmt(targets['ITEM']['all_constructs_cleared_cited'])}")
    if report["cited_ablations"]:
        out += ["", "## Every cited ablation", "",
                "Read the non-flips: if the analyzer now cites other turns for the same label, the "
                "signal may be redundant rather than the explanation unfaithful.", "",
                "| Item | Finding | Before | After | Flipped |", "|---|---|---|---|---|"]
        for d in report["cited_ablations"]:
            out.append(f"| {d['item']} | {d['target']} | {json.dumps(d['before'])} | "
                       f"{json.dumps(d['after'])} | {'yes' if d['flipped'] else 'no'} |")
    return "\n".join(out) + "\n"


# --------------------------------------------------------------------------- main

def _write(fh, row: dict) -> None:
    fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    fh.flush()


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--items", default=str(ITEMS_PATH))
    ap.add_argument("--ids", nargs="*", help="only these item ids")
    ap.add_argument("--baseline", nargs="*", help="reuse saved analyzer rows as the baseline instead of re-running it")
    ap.add_argument("--prompt", default=str(DEFAULT_PROMPT))
    ap.add_argument("--model", default=None)
    ap.add_argument("--effort", default=None)
    ap.add_argument("--draws", type=int, default=2, help="random-control draws per finding")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--dry-run", action="store_true", help="print the ablation plan; call nothing")
    ap.add_argument("--preds", help="score saved rows from this JSONL instead of running")
    ap.add_argument("--out", help="write baseline and ablation rows here")
    ap.add_argument("--json-out", help="write the report as JSON here")
    args = ap.parse_args(argv)

    items = load_items(args.items)
    if args.ids:
        items = [it for it in items if it["id"] in set(args.ids)]

    if args.preds:
        report = build_report(items, load_items(args.preds))
        return _finish(report, args)

    prompt = load_prompt(args.prompt)
    saved = {}
    for path in args.baseline or []:
        saved.update({r["item_id"]: r for r in load_items(path)})

    if args.dry_run:
        print(f"# E3 dry run: prompt {prompt.version}, {len(items)} items, {args.draws} random draws per finding\n")
        n_calls = 0
        for it in items:
            b = saved.get(it["id"])
            if b is None:
                print(f"## {it['id']}: baseline would be run live (1 call); ablations depend on its citations")
                n_calls += 1
                continue
            if not _ok(b):
                print(f"## {it['id']}: saved baseline status {b.get('status')}; nothing to ablate")
                continue
            jobs = plan(it, b, args.draws, args.seed)
            runnable = [j for j in jobs if "item" in j]
            n_calls += len(runnable)
            print(f"## {it['id']} ({it['stratum']}): {len(runnable)} ablations")
            for j in jobs:
                desc = j.get("status") or f"remove turns {j['removed']}"
                print(f"   {j['target']:<5} {j['condition']:<6} cited {j['cited']}: {desc}")
        print(f"\nTotal analyzer calls: {n_calls}")
        if saved and items:
            first = next((j for it in items for j in plan(it, saved[it["id"]], args.draws, args.seed)
                          if it["id"] in saved and _ok(saved[it["id"]]) and "item" in j), None)
            if first:
                print(f"\n# Example ablated transcript: {first['item']['id']}\n{render_transcript(first['item'])}")
        return 0

    if not args.out:
        ap.error("live runs need --out so the rows are kept")
    backend = AnthropicBackend(model=args.model, effort=args.effort)
    rows: list[dict] = []
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as fh:
        for it in items:
            b = saved.get(it["id"])
            if b is None:
                b = json.loads(analyze(it, prompt, backend).to_json())
                print(f"{it['id']} baseline: {b['status']}", file=sys.stderr)
            b = dict(b, e3_role="baseline")
            rows.append(b)
            _write(fh, b)
            if not _ok(b):
                continue
            for job in plan(it, b, args.draws, args.seed):
                meta = {k: v for k, v in job.items() if k != "item"}
                if "item" not in job:
                    row = dict(meta, item_id=f"{it['id']}__e3_{job['target']}_{job['condition']}", e3_role="ablation")
                else:
                    res = json.loads(analyze(job["item"], prompt, backend).to_json())
                    row = dict(res, **meta, index_map=job["item"]["index_map"], e3_role="ablation")
                    print(f"{job['item']['id']}: {res['status']}", file=sys.stderr)
                rows.append(row)
                _write(fh, row)
    return _finish(build_report(items, rows), args)


def _finish(report: dict, args) -> int:
    if args.json_out:
        with open(args.json_out, "w", encoding="utf-8") as fh:
            json.dump(report, fh, indent=2)
    sys.stdout.write(render_markdown(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
