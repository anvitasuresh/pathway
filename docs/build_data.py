"""Build docs/data.js for the Pathway site from files already in the repo.

No API calls. Run from the repo root:

    python docs/build_data.py

Reads:
    corpus/items.jsonl                       the anchor pair's turns and gold labels
    eval/results/e9_moderation*.jsonl       per-turn moderation scores (E9)
    eval/results/e4_run.jsonl, results_v2*.jsonl
                                             whole-conversation analyzer rows, chosen the
                                             same way eval/e9_per_message.py chooses them
Writes:
    docs/data.js                             window.PATHWAY_DATA = {...}
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from eval.e9_per_message import collapse, load_items, load_whole_rows  # noqa: E402

PAIR = ("hn-teen-02", "hp-teen-02")
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


def main() -> int:
    items = load_items(str(ROOT / "corpus/items.jsonl"))
    by_id = {it["id"]: it for it in items}
    whole = load_whole_rows([str(p) for p in WHOLE_FROM], items, "v2")
    mod = moderation_rows()
    verdicts = collapse(items, whole + [{**m, "arm": "moderation", "parent_id": m["item_id"], "turn": None}
                                        for m in mod])
    mod_by_id = {m["item_id"]: m for m in mod}  # last row wins (novelist re-run)
    whole_by_id = {r["item_id"]: r for r in whole}

    pair = []
    for iid in PAIR:
        it, out = by_id[iid], whole_by_id[iid]["output"]
        scores = per_turn_scores(mod_by_id[iid])
        pair.append({
            "id": iid, "stratum": it["stratum"], "gold_tier": it["gold"]["tier"],
            "turns": [{"i": t["i"], "role": t["role"], "text": t["text"],
                       "moderation": scores.get(int(t["i"])) if t["role"] == "user" else None}
                      for t in it["turns"]],
            "gold": {c: v for c, v in it["gold"].items() if c != "tier"},
            "analyzer": {"tier": out["tier"], "tier_rationale": out["tier_rationale"],
                         "competing_explanation": out["competing_explanation"], "trajectory": out["trajectory"],
                         "constructs": {c: {"label": v["label"], "evidence_turns": v["evidence_turns"],
                                            "reasoning": v["reasoning"]}
                                        for c, v in out["constructs"].items()}},
        })

    corpus = []
    for it in items:
        w, m = verdicts["whole"].get(it["id"]), verdicts["moderation"].get(it["id"])
        if not (w and m and w.get("status") == "ok" and m.get("status") == "ok"):
            continue
        corpus.append({"id": it["id"], "stratum": it["stratum"], "persona": it["persona"],
                       "gold_tier": it["gold"]["tier"], "analyzer_tier": w["tier"],
                       "moderation_flagged": bool(m["flagged_turns"]), "moderation_top": round(m["max_score"], 3),
                       "moderation_category": m["max_category"], "pair_id": it.get("pair_id")})

    data = {"pair": pair, "corpus": corpus,
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
