"""Build docs/data.js for the Pathway site from files already in the repo.

No API calls. Run from the repo root:

    python docs/build_data.py

Reads:
    corpus/items.jsonl                       the anchor pair's turns and gold labels
    eval/results/e9_moderation*.jsonl       per-turn moderation scores (E9)
    eval/results/e4_run.jsonl, results_v2*.jsonl
                                             whole-conversation analyzer rows, chosen the
                                             same way eval/e9_per_message.py chooses them
    corpus/refusal_sequences.jsonl, corpus/refusal_sessions.jsonl, eval/results/e5_run_v3.jsonl
                                             the Paper Lanterns refusal examples (rule tracker run
                                             here; model tracker read from the saved E5 run)
Writes:
    docs/data.js                             window.PATHWAY_DATA = {...}
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from analyzer.refusal_state import track_rules  # noqa: E402
from eval.e12_sessions import cross_attempts  # noqa: E402
from eval.e9_per_message import collapse, load_items, load_whole_rows  # noqa: E402

PAIR = ("hn-teen-02", "hp-teen-02")
# Paper Lanterns family: one refused request, different next moves (E5 same day, E12 next day).
REFUSAL_SAME_DAY = ("cp-rslyrics-01", "hp-rsimplicit-02", "hn-rsalt-01")
REFUSAL_NEXT_DAY = ("cp-xslyrics-01", "hp-xsparaphrase-01", "hn-xsthemes-01", "hn-xsfiction-01",
                    "hn-xsfacts-01", "cn-xsunrelated-01")
WHOLE_FROM = [ROOT / "eval/results/e4_run.jsonl", ROOT / "results_v2.jsonl", ROOT / "results_v2_batch3.jsonl"]
MODERATION = [ROOT / "eval/results/e9_moderation.jsonl", ROOT / "eval/results/e9_moderation_novelist.jsonl"]


def moderation_rows() -> list[dict]:
    rows = []
    for p in MODERATION:
        rows += [r for r in load_items(str(p)) if r.get("status") == "ok"]
    return rows


def per_turn_scores(row: dict) -> dict[int, dict]:
    out = {}
    for t in row["turns"]:
        cat, score = max(t["category_scores"].items(), key=lambda kv: kv[1])
        out[int(t["turn"])] = {"flagged": bool(t["flagged"]), "top": round(score, 3), "category": cat}
    return out


def refusal_examples() -> dict:
    """The Paper Lanterns family, with what each tracker said. Rule tracker computed here;
    model tracker read from the saved E5 run (prompt v3). Model tracker was not run on E12."""
    model = {}
    for line in (ROOT / "eval/results/e5_run_v3.jsonl").open(encoding="utf-8"):
        r = json.loads(line)
        if r["tracker"] == "model" and r["status"] == "ok":
            model[r["item_id"]] = r["undone"]
    same = {it["id"]: it for it in load_items(str(ROOT / "corpus/refusal_sequences.jsonl"))}
    nxt = {it["id"]: it for it in load_items(str(ROOT / "corpus/refusal_sessions.jsonl"))}
    out = {"same_day": [], "next_day": []}
    for iid in REFUSAL_SAME_DAY:
        it = same[iid]
        out["same_day"].append({
            "id": iid, "stratum": it["stratum"], "turns": [{"role": t["role"], "text": t["text"]} for t in it["turns"]],
            "gold": it["refusal_sequence"]["present"] and not it["refusal_sequence"]["benign"],
            "note": it["refusal_sequence"].get("note", ""),
            "per_message": False, "rules": track_rules(it).summary()["undone"], "model": model.get(iid)})
    for iid in REFUSAL_NEXT_DAY:
        it = nxt[iid]
        out["next_day"].append({
            "id": iid, "stratum": it["stratum"],
            "turns": [{"role": t["role"], "text": t["text"], "session": t.get("session")} for t in it["turns"]],
            "gold": it["cross_session"]["attempt"], "note": it["cross_session"].get("note", ""),
            "reset": bool(cross_attempts(it, track_rules(it, "reset"))),
            "rules": bool(cross_attempts(it, track_rules(it, "carry")))})
    return out


def main() -> int:
    items = load_items(str(ROOT / "corpus/items.jsonl"))
    by_id = {it["id"]: it for it in items}
    whole = load_whole_rows([str(p) for p in WHOLE_FROM], items, "v2")
    mod = moderation_rows()
    verdicts = collapse(items, whole + [{**m, "arm": "moderation", "parent_id": m["item_id"], "turn": None}
                                        for m in mod])
    mod_by_id = {m["item_id"]: m for m in mod}  # last row wins (novelist re-run)
    whole_by_id = {r["item_id"]: r for r in whole}

    def conv(iid: str) -> dict:
        it, out = by_id[iid], whole_by_id[iid]["output"]
        scores = per_turn_scores(mod_by_id[iid])
        return {
            "id": iid, "stratum": it["stratum"], "persona": it["persona"], "gold_tier": it["gold"]["tier"],
            "turns": [{"i": t["i"], "role": t["role"], "text": t["text"],
                       "moderation": scores.get(int(t["i"])) if t["role"] == "user" else None}
                      for t in it["turns"]],
            "gold": {c: v for c, v in it["gold"].items() if c != "tier"},
            "analyzer": {"tier": out["tier"], "tier_rationale": out["tier_rationale"],
                         "competing_explanation": out["competing_explanation"], "trajectory": out["trajectory"],
                         "constructs": {c: {"label": v["label"], "evidence_turns": v["evidence_turns"],
                                            "reasoning": v["reasoning"]}
                                        for c, v in out["constructs"].items()}},
        }

    pair = [conv(i) for i in PAIR]
    # Every matched pair, negative first, for the pair explorer.
    pairs = [[conv(it["id"]), conv(it["pair_id"])] for it in items
             if it["stratum"] == "hard_negative" and it.get("pair_id")]

    corpus = []
    for it in items:
        w, m = verdicts["whole"].get(it["id"]), verdicts["moderation"].get(it["id"])
        if not (w and m and w.get("status") == "ok" and m.get("status") == "ok"):
            continue
        corpus.append({"id": it["id"], "stratum": it["stratum"], "persona": it["persona"],
                       "gold_tier": it["gold"]["tier"], "analyzer_tier": w["tier"],
                       "moderation_flagged": bool(m["flagged_turns"]), "moderation_top": round(m["max_score"], 3),
                       "moderation_category": m["max_category"], "pair_id": it.get("pair_id")})

    data = {"pair": pair, "pairs": pairs, "corpus": corpus, "refusal": refusal_examples(),
            "source": "Built by docs/build_data.py from corpus/items.jsonl, eval/results/e9_moderation*.jsonl "
                      "and the v2 whole-conversation analyzer rows."}
    dest = ROOT / "docs/data.js"
    dest.write_text("window.PATHWAY_DATA = " + json.dumps(data, ensure_ascii=False, indent=1) + ";\n", encoding="utf-8")
    hn = [c for c in corpus if c["stratum"] == "hard_negative"]
    print(f"wrote {dest.relative_to(ROOT)}: pair {PAIR}, {len(corpus)} items "
          f"(hard negatives: moderation flagged {sum(c['moderation_flagged'] for c in hn)}/{len(hn)}, "
          f"analyzer review+ {sum(c['analyzer_tier'] in ('review', 'escalate') for c in hn)}/{len(hn)})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
