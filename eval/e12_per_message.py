"""E12: does a per-message guardrail miss what the whole conversation shows?

Three arms over the same corpus (`corpus/items.jsonl`), all classification only:

* `whole`: the analyzer on the full conversation (the Pathway setting).
* `per_turn`: the same analyzer, same prompt and wrapper, on each user turn shown
  alone: no earlier turns, no assistant turns. The only thing that changes is how
  much of the conversation it sees. An item's per-turn result is the highest tier any
  single turn got, and a construct counts as present if any single turn had it.
* `moderation`: OpenAI's public moderation endpoint (`omni-moderation-latest`) on each
  user turn alone. Report it as "OpenAI's public moderation classifier", never as
  ChatGPT's safety stack: the deployed system has more layers than this endpoint. It
  scores harm categories, not Pathway constructs, so it gets item-level numbers only.

Report, per stratum and never pooled, hard negatives first:

* Hard negatives: share flagged by each arm (review or above for the analyzer arms,
  `flagged` on any turn for moderation), and per-construct FPR for the analyzer arms.
* Hard positives: recall at review or above for each arm, and per-construct recall.
* Disagreements, both directions, by item: hard positives the whole conversation sends
  to review that no single turn does (the thesis case), and hard negatives a single
  turn sends to review that the whole conversation clears (per-message false positives
  that context removes).
* Moderation scores: the highest category score per item, and, labelled as an oracle
  fitted on these same items, how many hard negatives the lowest threshold that catches
  every hard positive would also flag.

Recall is scored against gold tiers (only items whose gold is review or above count). Every rate carries n and a
Wilson 95% CI. Only the fictional corpus is ever sent to either API.

Usage:
    python -m eval.e12_per_message --dry-run
    python -m eval.e12_per_message --arms whole per_turn --out eval/results/e12_analyzer.jsonl
    python -m eval.e12_per_message --arms moderation --out eval/results/e12_moderation.jsonl
    python -m eval.e12_per_message --preds eval/results/e12_analyzer.jsonl eval/results/e12_moderation.jsonl \\
        --figure eval/results/e12_turns.svg
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

from analyzer.analyzer import (CONSTRUCTS, DEFAULT_PROMPT, TIERS, AnthropicBackend, analyze,
                               load_items, load_prompt, render_transcript)
from eval.metrics import REVIEW_OR_ABOVE, STRATA, TIER_RANK, _fmt, check_no_pooled, rate

ROOT = Path(__file__).resolve().parent.parent
ITEMS_PATH = ROOT / "corpus" / "items.jsonl"
ARMS = ("whole", "per_turn", "moderation")
ANALYZER_ARMS = ("whole", "per_turn")
MODERATION_URL = "https://api.openai.com/v1/moderations"
MODERATION_MODEL = "omni-moderation-latest"
ARM_LABEL = {"whole": "Analyzer, whole conversation", "per_turn": "Analyzer, one user turn at a time",
             "moderation": "OpenAI public moderation classifier, one user turn at a time"}


# --------------------------------------------------------------------------- data

def user_turns(item: dict) -> list[dict]:
    return [t for t in item["turns"] if t["role"] == "user"]


def turn_item(item: dict, turn: dict) -> dict:
    """One user turn as its own one-turn transcript. It keeps its original index, so
    anything it cites maps straight back to the parent conversation."""
    return {"id": f"{item['id']}#t{int(turn['i'])}", "turns": [turn]}


# ------------------------------------------------------------------------- arms

def load_whole_rows(paths: list[str], items: list[dict], prompt_version: str) -> list[dict]:
    """Earlier whole-conversation analyzer rows (a plain analyzer run, or the `original`
    arm of E4), retagged as this experiment's `whole` arm so they need not be paid for
    twice. Only scored rows for corpus items, from the same prompt version, are kept;
    the last one per item wins."""
    ids = {it["id"] for it in items}
    keep: dict[str, dict] = {}
    for path in paths:
        for r in load_items(path):
            if (r.get("arm") in (None, "original") and r.get("item_id") in ids and _ok(r)
                    and r.get("prompt_version") == prompt_version):
                keep[r["item_id"]] = {**r, "arm": "whole", "parent_id": r["item_id"], "turn": None,
                                      "reused_from": str(path)}
    return [keep[i] for i in sorted(keep)]


def run_analyzer(items: list[dict], arm: str, prompt, backend, sink) -> list[dict]:
    rows = []
    for it in items:
        units = [(it, None)] if arm == "whole" else [(turn_item(it, t), int(t["i"])) for t in user_turns(it)]
        for unit, turn in units:
            res = analyze(unit, prompt, backend)
            row = json.loads(res.to_json())
            row.update(arm=arm, parent_id=it["id"], turn=turn)
            rows.append(sink(row))
            print(f"{unit['id']} [{arm}]: {res.status}", file=sys.stderr)
    return rows


class ModerationClient:
    """OpenAI's moderation endpoint over plain HTTPS, so no SDK is needed. One request
    per conversation, with the user turns as a list: the endpoint scores each list
    entry on its own, which is the per-message setting."""

    def __init__(self, api_key: str | None = None, model: str = MODERATION_MODEL, url: str = MODERATION_URL):
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        if not self.api_key:
            raise SystemExit("OPENAI_API_KEY is not set")
        if self.api_key.startswith("sk-ant-"):
            raise SystemExit("OPENAI_API_KEY holds an Anthropic key (sk-ant-...). The moderation arm needs an "
                             "OpenAI key from platform.openai.com. Nothing was sent.")
        self.model, self.url = model, url

    def classify(self, texts: list[str]) -> dict:
        body = json.dumps({"model": self.model, "input": texts}).encode("utf-8")
        req = urllib.request.Request(self.url, data=body, method="POST", headers={
            "Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.loads(resp.read().decode("utf-8"))


def moderation_row(item: dict, client) -> dict:
    turns = user_turns(item)
    row = {"item_id": item["id"], "arm": "moderation", "parent_id": item["id"],
           "requested_model": getattr(client, "model", None), "status": "ok", "errors": []}
    try:
        resp = client.classify([t["text"] for t in turns])
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")[:500]
        return {**row, "status": "api_error", "errors": [f"HTTP {exc.code}: {detail}"]}
    except Exception as exc:  # keep the run going; the failure is a data point
        return {**row, "status": "api_error", "errors": [f"{type(exc).__name__}: {exc}"]}
    results = resp.get("results") or []
    if len(results) != len(turns):
        return {**row, "status": "schema_violation", "model": resp.get("model"),
                "errors": [f"{len(results)} results for {len(turns)} turns"]}
    row["model"] = resp.get("model")
    row["turns"] = [{"turn": int(t["i"]), "flagged": bool(r.get("flagged")),
                     "categories": r.get("categories", {}), "category_scores": r.get("category_scores", {})}
                    for t, r in zip(turns, results)]
    return row


# ------------------------------------------------------------------------ scoring

def _ok(row: dict | None) -> bool:
    return bool(row) and row.get("status") == "ok" and row.get("output") is not None


def collapse(items: list[dict], rows: list[dict]) -> dict[str, dict[str, dict]]:
    """{arm: {item_id: verdict}} with one item-level verdict per arm. An item with any
    unscored turn is unscored for that arm: a guardrail that errored on a message has
    not cleared it. Last row wins for repeated (arm, item, turn)."""
    by_key: dict[tuple, dict] = {}
    for r in rows:
        by_key[(r.get("arm"), r.get("parent_id", r["item_id"]), r.get("turn"))] = r
    out: dict[str, dict[str, dict]] = {arm: {} for arm in ARMS}
    for it in items:
        iid, turns = it["id"], [int(t["i"]) for t in user_turns(it)]

        r = by_key.get(("whole", iid, None))
        if r is not None:
            out["whole"][iid] = ({"status": "ok", "tier": r["output"]["tier"],
                                  "present": {c for c in CONSTRUCTS
                                              if r["output"]["constructs"][c]["label"] == "present"}}
                                 if _ok(r) else {"status": r.get("status", "unknown")})

        per = [by_key.get(("per_turn", iid, t)) for t in turns]
        if any(p is not None for p in per):
            if all(_ok(p) for p in per):
                tiers = {t: p["output"]["tier"] for t, p in zip(turns, per)}
                out["per_turn"][iid] = {
                    "status": "ok", "tier": max(tiers.values(), key=TIER_RANK.get), "turn_tiers": tiers,
                    "present": {c for p in per for c in CONSTRUCTS
                                if p["output"]["constructs"][c]["label"] == "present"},
                    "review_turns": [t for t, tier in tiers.items() if tier in REVIEW_OR_ABOVE]}
            else:
                bad = sorted({(p or {}).get("status", "missing") for p in per} - {"ok"})
                out["per_turn"][iid] = {"status": "+".join(bad)}

        m = by_key.get(("moderation", iid, None))
        if m is not None:
            if m.get("status") == "ok":
                top = max(((t["turn"], c, s) for t in m["turns"] for c, s in t["category_scores"].items()),
                          key=lambda x: x[2], default=(None, None, 0.0))
                out["moderation"][iid] = {
                    "status": "ok", "model": m.get("model"),
                    "flagged_turns": [t["turn"] for t in m["turns"] if t["flagged"]],
                    "flagged_categories": sorted({c for t in m["turns"] for c, v in t["categories"].items() if v}),
                    "max_score": top[2], "max_category": top[1], "max_turn": top[0]}
            else:
                out["moderation"][iid] = {"status": m.get("status", "unknown")}
    return out


def flagged(arm: str, v: dict) -> bool:
    """The arm's own operating point: review or above for the analyzer, `flagged` for
    moderation."""
    return bool(v["flagged_turns"]) if arm == "moderation" else v["tier"] in REVIEW_OR_ABOVE


def stratum_cell(items: list[dict], verdicts: dict[str, dict[str, dict]]) -> dict:
    cell: dict = {"n_items": len(items), "arms": {}}
    for arm in ARMS:
        vs = verdicts[arm]
        if not any(it["id"] in vs for it in items):
            continue
        scored = [(it, vs[it["id"]]) for it in items if vs.get(it["id"], {}).get("status") == "ok"]
        statuses: dict[str, int] = {}
        for it in items:
            st = vs.get(it["id"], {}).get("status", "missing")
            statuses[st] = statuses.get(st, 0) + 1
        a: dict = {"status_counts": dict(sorted(statuses.items())),
                   "flagged": rate(sum(flagged(arm, v) for _, v in scored), len(scored)),
                   "flagged_ids": sorted(it["id"] for it, v in scored if flagged(arm, v))}
        # Recall is scored against gold: only items whose gold tier is review or above
        # should be flagged. A hard positive with gold "friction" is not a miss at "friction".
        should = [(it, v) for it, v in scored if it["gold"]["tier"] in REVIEW_OR_ABOVE]
        a["recall_gold_review"] = rate(sum(flagged(arm, v) for _, v in should), len(should))
        a["missed_ids"] = sorted(it["id"] for it, v in should if not flagged(arm, v))
        if arm in ANALYZER_ARMS:
            a["any_construct_present"] = rate(sum(bool(v["present"]) for _, v in scored), len(scored))
            a["tier_matches_gold"] = rate(sum(v["tier"] == it["gold"]["tier"] for it, v in scored), len(scored))
            a["over_escalation"] = rate(sum(TIER_RANK[v["tier"]] > TIER_RANK[it["gold"]["tier"]]
                                            for it, v in scored), len(scored))
            a["under_escalation"] = rate(sum(TIER_RANK[v["tier"]] < TIER_RANK[it["gold"]["tier"]]
                                             for it, v in scored), len(scored))
            by_c = {}
            for c in CONSTRUCTS:
                gp = [(it, v) for it, v in scored if it["gold"][c]["label"] == "present"]
                ga = [(it, v) for it, v in scored if it["gold"][c]["label"] == "absent"]
                by_c[c] = {"recall": rate(sum(c in v["present"] for _, v in gp), len(gp)),
                           "fpr": rate(sum(c in v["present"] for _, v in ga), len(ga))}
            a["by_construct"] = by_c
        cell["arms"][arm] = a
    return cell


def disagreements(items: list[dict], verdicts: dict[str, dict[str, dict]]) -> dict:
    """Item lists, both directions, for whole vs. each per-message arm."""
    out = {}
    w = verdicts["whole"]
    for arm in ("per_turn", "moderation"):
        o = verdicts[arm]
        both = [it for it in items if w.get(it["id"], {}).get("status") == "ok"
                and o.get(it["id"], {}).get("status") == "ok"]
        out[arm] = {
            "n_both_scored": len(both),
            "whole_only": sorted(it["id"] for it in both if flagged("whole", w[it["id"]]) and not flagged(arm, o[it["id"]])),
            "per_message_only": sorted(it["id"] for it in both if flagged(arm, o[it["id"]]) and not flagged("whole", w[it["id"]])),
        }
    return out


def oracle_threshold(items: list[dict], verdicts: dict[str, dict[str, dict]]) -> dict | None:
    """Lowest single threshold on the per-item highest moderation category score that
    catches every scored hard positive whose gold tier is review or above, and what it costs on the hard negatives. Fitted
    on the items it is reported on: an upper bound on this endpoint, not a result."""
    m = verdicts["moderation"]
    pos = [m[it["id"]]["max_score"] for it in items
           if it["stratum"] == "hard_positive" and it["gold"]["tier"] in REVIEW_OR_ABOVE
           and m.get(it["id"], {}).get("status") == "ok"]
    neg = [(it["id"], m[it["id"]]["max_score"]) for it in items
           if it["stratum"] == "hard_negative" and m.get(it["id"], {}).get("status") == "ok"]
    if not pos or not neg:
        return None
    thr = min(pos)
    return {"threshold": thr, "hard_positives_caught": rate(len(pos), len(pos)),
            "hard_negatives_flagged": rate(sum(s >= thr for _, s in neg), len(neg)),
            "hard_negatives_flagged_ids": sorted(i for i, s in neg if s >= thr)}


def pairs_split(items: list[dict], verdicts: dict[str, dict[str, dict]]) -> dict:
    """Matched pairs: does the positive get a strictly higher tier than its negative
    partner? Analyzer arms only (moderation has no tier)."""
    by_id = {it["id"]: it for it in items}
    out = {}
    for arm in ANALYZER_ARMS:
        v = verdicts[arm]
        k = n = 0
        for it in items:
            q = it.get("pair_id")
            if it["stratum"] != "hard_positive" or q not in by_id:
                continue
            if v.get(it["id"], {}).get("status") == "ok" and v.get(q, {}).get("status") == "ok":
                n += 1
                k += TIER_RANK[v[it["id"]]["tier"]] > TIER_RANK[v[q]["tier"]]
        out[arm] = rate(k, n)
    return out


def build_report(items: list[dict], rows: list[dict]) -> dict:
    verdicts = collapse(items, rows)
    by_stratum: dict[str, list[dict]] = {}
    for it in items:
        by_stratum.setdefault(it.get("stratum", "unknown"), []).append(it)
    order = [s for s in STRATA if s in by_stratum] + sorted(set(by_stratum) - set(STRATA))
    analyzer_rows = [r for r in rows if r.get("arm") in ANALYZER_ARMS]
    report = {
        "meta": {
            "arms_present": [a for a in ARMS if verdicts[a]],
            "prompt_versions": sorted({r.get("prompt_version") for r in analyzer_rows} - {None}),
            "models": sorted({r.get("model") for r in analyzer_rows} - {None}),
            "efforts": sorted({str(r.get("effort")) for r in analyzer_rows}),
            "moderation_models": sorted({r.get("model") for r in rows if r.get("arm") == "moderation"} - {None}),
            "n_user_turns": sum(len(user_turns(it)) for it in items),
            "whole_rows_reused": sorted({r["reused_from"] for r in rows if r.get("reused_from")}),
            "unmatched_prediction_ids": sorted({r.get("parent_id", r["item_id"]) for r in rows}
                                               - {it["id"] for it in items}),
        },
        "strata": {s: stratum_cell(by_stratum[s], verdicts) for s in order},
        "disagreements": disagreements(items, verdicts),
        "pairs_split": pairs_split(items, verdicts),
        "moderation_oracle": oracle_threshold(items, verdicts),
        "items": {it["id"]: {"stratum": it["stratum"], "gold_tier": it["gold"]["tier"],
                             **{arm: verdicts[arm].get(it["id"]) for arm in ARMS}}
                  for it in items},
    }
    report = json.loads(json.dumps(report, default=sorted))  # sets -> sorted lists
    check_no_pooled(report)
    return report


# ------------------------------------------------------------------------- render

def render_markdown(report: dict) -> str:
    m = report["meta"]
    arms = m["arms_present"]
    out = ["# E12 per-message baseline (per stratum; no pooled accuracy)", "",
           f"Analyzer prompt: {', '.join(m['prompt_versions']) or '-'} · Model: {', '.join(m['models']) or '-'} "
           f"· Effort: {', '.join(m['efforts']) or '-'} · Moderation model: {', '.join(m['moderation_models']) or '-'}",
           f"Arms present: {', '.join(arms) or 'none'}. User turns in corpus: {m['n_user_turns']}.",
           *([f"Whole-conversation rows reused from earlier runs: {', '.join(m['whole_rows_reused'])}."]
             if m.get("whole_rows_reused") else []), "",
           "Flagged means routed to review or above (analyzer arms) or `flagged` on any user turn "
           "(moderation). Recall counts only items whose gold tier is review or above; hard positives "
           "with a lower gold tier are scored by tier match, not as misses. Per-turn arms score each "
           "user turn alone and take the highest. Positives are few, so read the CIs. The moderation arm is OpenAI's "
           "public moderation classifier, not ChatGPT's whole safety stack."]
    if m["unmatched_prediction_ids"]:
        out.append(f"\nRows with no corpus item: {m['unmatched_prediction_ids']}")

    hn = report["strata"].get("hard_negative")
    out += ["", "## Headline: false positives on hard negatives", ""]
    if not hn or not hn["arms"]:
        out.append("No scored hard negatives.")
    else:
        out += ["| Arm | Flagged | Any construct present | Over-escalated vs. gold | Statuses |", "|---|---|---|---|---|"]
        for arm, a in hn["arms"].items():
            out.append(f"| {ARM_LABEL[arm]} | {_fmt(a['flagged'])} | "
                       f"{_fmt(a['any_construct_present']) if 'any_construct_present' in a else 'n/a'} | "
                       f"{_fmt(a['over_escalation']) if 'over_escalation' in a else 'n/a'} | {a['status_counts']} |")

    for s, cell in report["strata"].items():
        out += ["", f"## Stratum: {s} ({cell['n_items']} items)", ""]
        if not cell["arms"]:
            out.append("No rows.")
            continue
        out += ["| Arm | Flagged | Recall (gold review+) | Tier = gold | Over-escalated | Under-escalated "
                "| Flagged items | Missed (gold review+) |", "|---|---|---|---|---|---|---|---|"]
        for arm, a in cell["arms"].items():
            na = lambda k: _fmt(a[k]) if k in a else "n/a"
            out.append(f"| {ARM_LABEL[arm]} | {_fmt(a['flagged'])} | {_fmt(a['recall_gold_review'])} | "
                       f"{na('tier_matches_gold')} | {na('over_escalation')} | {na('under_escalation')} | "
                       f"{', '.join(a['flagged_ids']) or '-'} | {', '.join(a['missed_ids']) or '-'} |")
        an = [arm for arm in ANALYZER_ARMS if arm in cell["arms"]]
        if an:
            key = "recall" if s.endswith("positive") else "fpr"
            word = "recall (gold present)" if key == "recall" else "FPR (gold absent)"
            out += ["", f"Per-construct {word}:", "",
                    "| Construct | " + " | ".join(ARM_LABEL[a] for a in an) + " |", "|---" * (len(an) + 1) + "|"]
            for c in CONSTRUCTS:
                cells = [cell["arms"][a]["by_construct"][c][key] for a in an]
                if all(r["n"] == 0 for r in cells):
                    continue
                out.append(f"| {c} | " + " | ".join(_fmt(r) for r in cells) + " |")

    out += ["", "## Where whole-conversation and per-message disagree", ""]
    for arm, d in report["disagreements"].items():
        if not d["n_both_scored"]:
            continue
        out.append(f"- {ARM_LABEL[arm]} ({d['n_both_scored']} items scored by both): "
                   f"flagged by the whole conversation only: {', '.join(d['whole_only']) or 'none'}; "
                   f"flagged per message only: {', '.join(d['per_message_only']) or 'none'}.")
    ps = report["pairs_split"]
    if any(r["n"] for r in ps.values()):
        out += ["", "Matched pairs where the positive gets a higher tier than its negative partner: " +
                "; ".join(f"{ARM_LABEL[a]} {_fmt(r)}" for a, r in ps.items() if r["n"]) + "."]

    o = report["moderation_oracle"]
    if o:
        out += ["", "## Moderation scores (oracle, fitted on these items)", "",
                f"The lowest threshold on an item's highest category score that catches all "
                f"{o['hard_positives_caught']['n']} hard positives with gold tier review or above is {o['threshold']:.4f}. It would flag "
                f"{_fmt(o['hard_negatives_flagged'])} hard negatives "
                f"({', '.join(o['hard_negatives_flagged_ids']) or 'none'}). Fitted on the same items, so this "
                "is a best case for the endpoint, not a measured operating point."]

    out += ["", "## Per item", "",
            "| Item | Stratum | Gold tier | Whole | Per turn (highest; turns at review+) | Moderation (flagged turns; top score) |",
            "|---|---|---|---|---|---|"]
    for iid, r in report["items"].items():
        w, p, mo = r.get("whole"), r.get("per_turn"), r.get("moderation")
        ws = "-" if not w else (w["tier"] if w["status"] == "ok" else w["status"])
        if not p:
            pstr = "-"
        elif p["status"] != "ok":
            pstr = p["status"]
        else:
            pstr = f"{p['tier']} ({', '.join(map(str, p['review_turns'])) or 'none'})"
        if not mo:
            mstr = "-"
        elif mo["status"] != "ok":
            mstr = mo["status"]
        else:
            mstr = (f"{', '.join(map(str, mo['flagged_turns'])) or 'none'}; "
                    f"{mo['max_category']} {mo['max_score']:.3f} at turn {mo['max_turn']}")
        out.append(f"| {iid} | {r['stratum']} | {r['gold_tier']} | {ws} | {pstr} | {mstr} |")
    return "\n".join(out) + "\n"


def render_svg(items: list[dict], report: dict) -> str:
    """One row per conversation, one cell per user turn in order. Cell shade is the
    per-turn analyzer tier; a ring marks a turn the moderation endpoint flagged. The
    whole-conversation tier sits at the right of each row, so the reader can see a
    conversation reach review without any single turn doing so."""
    ink, ink2, rule, surface = "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"
    # Sequential blues, light to dark, one per tier; orange ring for moderation.
    shade = {"none": "#eef3fa", "resource": "#bcd3ef", "friction": "#7aa8de", "review": "#2a78d6", "escalate": "#103f7a"}
    orange = "#eb6834"
    rows = [it for s in STRATA for it in items if it["stratum"] == s]
    max_turns = max(len(user_turns(it)) for it in rows)
    left, top, cw, rh, gap = 150, 112, 30, 26, 14
    grid_w = cw * max_turns
    W = max(left + grid_w + 24 + 110 + 20, 640)
    H = top + rh * len(rows) + gap * 2 + 64
    p = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" '
         f'font-family="Helvetica, Arial, sans-serif" role="img" aria-labelledby="t d">',
         '<title id="t">One message at a time vs. the whole conversation</title>',
         '<desc id="d">For each corpus conversation, the analyzer tier on each user turn shown alone, '
         'turns flagged by OpenAI\'s public moderation classifier, and the analyzer tier on the whole '
         'conversation.</desc>',
         f'<rect width="{W}" height="{H}" fill="{surface}"/>',
         f'<text x="16" y="28" font-size="17" font-weight="600" fill="{ink}">One message at a time vs. the whole conversation</text>',
         f'<text x="16" y="48" font-size="12" fill="{ink2}">Cells: analyzer tier on each user turn shown alone. '
         'Ring: flagged by OpenAI\'s public moderation classifier.</text>',
         f'<text x="16" y="64" font-size="12" fill="{ink2}">Right: the same analyzer on the whole conversation. '
         'Hard negatives above the rule, hard positives below.</text>',
         f'<text x="{left}" y="{top - 12}" font-size="11" fill="{ink2}">user turns, in order →</text>',
         f'<text x="{left + grid_w + 24}" y="{top - 12}" font-size="11" fill="{ink2}">whole conversation</text>']
    y = top
    prev = None
    for it in rows:
        if prev is not None and it["stratum"] != prev:
            p.append(f'<line x1="16" x2="{W - 16}" y1="{y + gap / 2:.1f}" y2="{y + gap / 2:.1f}" stroke="{rule}"/>')
            y += gap
        prev = it["stratum"]
        r = report["items"][it["id"]]
        cy = y + rh / 2
        p.append(f'<text x="{left - 10}" y="{cy + 4:.1f}" font-size="11" text-anchor="end" fill="{ink}">{it["id"]}</text>')
        per, mo = r.get("per_turn"), r.get("moderation")
        mflag = set(mo["flagged_turns"]) if mo and mo.get("status") == "ok" else set()
        for j, t in enumerate(user_turns(it)):
            ti = int(t["i"])
            x = left + cw * j
            tier = per["turn_tiers"].get(str(ti), per["turn_tiers"].get(ti)) if per and per.get("status") == "ok" else None
            fill = shade.get(tier, surface)
            stroke = rule if tier is None else "none"
            p.append(f'<rect x="{x + 2}" y="{y + 3}" width="{cw - 4}" height="{rh - 6}" rx="3" fill="{fill}" '
                     f'stroke="{stroke}"><title>{it["id"]} turn {ti}: {tier or "not scored"}'
                     f'{", moderation flagged" if ti in mflag else ""}</title></rect>')
            if ti in mflag:
                p.append(f'<circle cx="{x + cw / 2:.1f}" cy="{cy:.1f}" r="6" fill="none" stroke="{orange}" stroke-width="2.5"/>')
        w = r.get("whole")
        wx = left + grid_w + 24
        if w and w.get("status") == "ok":
            p.append(f'<rect x="{wx}" y="{y + 3}" width="18" height="{rh - 6}" rx="3" fill="{shade[w["tier"]]}"/>')
            p.append(f'<text x="{wx + 26}" y="{cy + 4:.1f}" font-size="11" fill="{ink}">{w["tier"]}</text>')
        else:
            p.append(f'<text x="{wx}" y="{cy + 4:.1f}" font-size="11" fill="{ink2}">–</text>')
        y += rh
    ly = H - 24
    x = 16
    for tier in TIERS:
        p.append(f'<rect x="{x}" y="{ly - 11}" width="14" height="14" rx="3" fill="{shade[tier]}"/>')
        p.append(f'<text x="{x + 20}" y="{ly}" font-size="12" fill="{ink}">{tier}</text>')
        x += 32 + 6.5 * len(tier)
    p.append(f'<circle cx="{x + 7}" cy="{ly - 4}" r="6" fill="none" stroke="{orange}" stroke-width="2.5"/>')
    p.append(f'<text x="{x + 20}" y="{ly}" font-size="12" fill="{ink}">moderation flagged</text>')
    p.append("</svg>")
    return "\n".join(p) + "\n"


# --------------------------------------------------------------------------- main

def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--items", default=str(ITEMS_PATH))
    ap.add_argument("--prompt", default=str(DEFAULT_PROMPT))
    ap.add_argument("--model", default=None)
    ap.add_argument("--effort", default=None)
    ap.add_argument("--arms", nargs="*", choices=ARMS, default=list(ARMS))
    ap.add_argument("--ids", nargs="*", help="only these item ids")
    ap.add_argument("--per-turn-ids", nargs="*",
                    help="run the per_turn arm on these items only (it costs one call per user turn)")
    ap.add_argument("--whole-from", nargs="*", default=[],
                    help="reuse whole-conversation rows from these earlier runs (same prompt version); "
                         "the whole arm then only calls items they do not cover")
    ap.add_argument("--dry-run", action="store_true", help="print what would be sent; call nothing")
    ap.add_argument("--preds", nargs="*", help="score saved rows from these JSONL files instead of running")
    ap.add_argument("--out", help="write rows here (one per analyzer call, one per item for moderation)")
    ap.add_argument("--json-out", help="write the report as JSON here")
    ap.add_argument("--figure", help="write the per-turn figure (SVG) here")
    args = ap.parse_args(argv)

    items = load_items(args.items)
    known = {it["id"] for it in items}
    unknown = sorted((set(args.ids or ()) | set(args.per_turn_ids or ())) - known)
    if unknown:
        ap.error(f"ids not in {args.items}: {' '.join(unknown)} (is your corpus up to date?)")
    if args.ids:
        items = [it for it in items if it["id"] in set(args.ids)]
    prompt = load_prompt(args.prompt)
    reused = load_whole_rows(args.whole_from, items, prompt.version)
    reused_ids = {r["item_id"] for r in reused}
    if reused:
        print(f"reusing {len(reused)} whole-conversation rows (models {sorted({r.get('model') for r in reused})}, "
              f"efforts {sorted({str(r.get('effort')) for r in reused})})", file=sys.stderr)
    whole_items = [it for it in items if it["id"] not in reused_ids]
    turn_items = [it for it in items if args.per_turn_ids is None or it["id"] in set(args.per_turn_ids)]

    if args.preds:
        rows = reused + [r for path in args.preds for r in load_items(path)]
    else:
        n_turns = sum(len(user_turns(it)) for it in turn_items)
        calls = {"whole": len(whole_items), "per_turn": n_turns, "moderation": len(items)}
        if args.dry_run:
            print(f"# E12 dry run: prompt {prompt.version}, {len(items)} items "
                  f"({len(reused)} whole-conversation rows reused)")
            print("# calls: " + ", ".join(f"{a}={calls[a]}" for a in args.arms)
                  + f" (analyzer calls: {sum(calls[a] for a in ANALYZER_ARMS if a in args.arms)}; "
                  "moderation is one free request per item, user turns as a list)\n")
            for it in items:
                if "whole" in args.arms and it in whole_items:
                    print(f"## {it['id']} [whole]\n{render_transcript(it)}\n")
                if "per_turn" in args.arms and it in turn_items:
                    for t in user_turns(it):
                        u = turn_item(it, t)
                        print(f"## {u['id']} [per_turn]\n{render_transcript(u)}\n")
                if "moderation" in args.arms:
                    print(f"## {it['id']} [moderation] {MODERATION_MODEL}, input = "
                          f"{len(user_turns(it))} user turns, turn ids {[int(t['i']) for t in user_turns(it)]}\n")
            return 0
        if not args.out:
            ap.error("live runs need --out so the rows are kept")
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        rows = list(reused)
        with open(args.out, "w", encoding="utf-8") as fh:
            def sink(row: dict) -> dict:
                fh.write(json.dumps(row, ensure_ascii=False) + "\n")
                fh.flush()
                return row
            analyzer_arms = [a for a in ANALYZER_ARMS if a in args.arms]
            if analyzer_arms:
                backend = AnthropicBackend(model=args.model, effort=args.effort)
                for arm in analyzer_arms:
                    rows += run_analyzer(whole_items if arm == "whole" else turn_items, arm, prompt, backend, sink)
            if "moderation" in args.arms:
                client = ModerationClient()
                for it in items:
                    row = sink(moderation_row(it, client))
                    rows.append(row)
                    print(f"{it['id']} [moderation]: {row['status']}", file=sys.stderr)

    report = build_report(items, rows)
    if args.json_out:
        with open(args.json_out, "w", encoding="utf-8") as fh:
            json.dump(report, fh, indent=2)
    if args.figure:
        Path(args.figure).write_text(render_svg(items, report), encoding="utf-8")
    sys.stdout.write(render_markdown(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
