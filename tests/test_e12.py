"""E12 per-message baseline. No network.

Analyzer outputs and moderation responses here are fabricated with tests.fixtures and
say nothing about how either system behaves.
"""

import json

from analyzer.analyzer import analyze, load_items, load_prompt
from eval import e12_per_message as e12
from eval.metrics import check_no_pooled
from tests.fixtures import StaticBackend, make_item, make_output, make_result


def _items():
    hp = make_item("hp-1", "hard_positive", present={"FIX": [0, 2]}, tier="review")
    hp["pair_id"] = "hn-1"
    hn = make_item("hn-1", "hard_negative", tier="none")
    hn["pair_id"] = "hp-1"
    hn2 = make_item("hn-2", "hard_negative", tier="none")
    return [hp, hn, hn2]


def _row(arm, parent, turn, output, status="ok"):
    r = make_result(parent if turn is None else f"{parent}#t{turn}", output, status)
    r.update(arm=arm, parent_id=parent, turn=turn)
    return r


def _mod(parent, flags, scores):
    return {"item_id": parent, "arm": "moderation", "parent_id": parent, "status": "ok", "model": "fixture-mod",
            "turns": [{"turn": t, "flagged": f, "categories": {"violence": f}, "category_scores": {"violence": s}}
                      for t, f, s in zip((0, 2), flags, scores)]}


def _rows():
    return [
        _row("whole", "hp-1", None, make_output({"FIX": [0, 2]}, tier="review")),
        _row("whole", "hn-1", None, make_output(tier="none")),
        _row("whole", "hn-2", None, make_output(tier="none")),
        # No single turn of the positive reaches review; one turn of hn-2 does.
        _row("per_turn", "hp-1", 0, make_output({"FIX": [0]}, tier="resource")),
        _row("per_turn", "hp-1", 2, make_output(tier="none")),
        _row("per_turn", "hn-1", 0, make_output(tier="none")),
        _row("per_turn", "hn-1", 2, make_output(tier="none")),
        _row("per_turn", "hn-2", 0, make_output(tier="none")),
        _row("per_turn", "hn-2", 2, make_output({"ESC": [2]}, tier="review")),
        _mod("hp-1", (False, False), (0.20, 0.30)),
        _mod("hn-1", (False, False), (0.10, 0.40)),
        _mod("hn-2", (True, False), (0.90, 0.05)),
    ]


def test_turn_item_keeps_original_index_and_analyzes_alone():
    item = _items()[0]
    unit = e12.turn_item(item, item["turns"][2])
    assert unit == {"id": "hp-1#t2", "turns": [item["turns"][2]]}
    backend = StaticBackend(json.dumps(make_output({"FIX": [2]}, tier="none")))
    res = analyze(unit, load_prompt(), backend)
    assert res.status == "ok"
    sent = backend.calls[0][1]
    assert "[turn 2] USER" in sent and "[turn 0]" not in sent and "ASSISTANT" not in sent


def test_collapse_takes_highest_tier_and_union_of_constructs():
    v = e12.collapse(_items(), _rows())
    assert v["per_turn"]["hp-1"]["tier"] == "resource"
    assert v["per_turn"]["hp-1"]["present"] == {"FIX"}
    assert v["per_turn"]["hn-2"]["review_turns"] == [2]
    assert v["moderation"]["hn-2"]["flagged_turns"] == [0]
    assert v["moderation"]["hn-1"]["max_score"] == 0.40


def test_one_unscored_turn_leaves_the_item_unscored():
    rows = _rows()
    rows[4] = _row("per_turn", "hp-1", 2, None, status="refusal")
    v = e12.collapse(_items(), rows)
    assert v["per_turn"]["hp-1"] == {"status": "refusal"}
    rows = [r for r in _rows() if not (r["arm"] == "per_turn" and r["parent_id"] == "hp-1" and r["turn"] == 2)]
    assert e12.collapse(_items(), rows)["per_turn"]["hp-1"] == {"status": "missing"}


def test_report_disagreements_oracle_and_pairs():
    report = e12.build_report(_items(), _rows())
    check_no_pooled(report)
    d = report["disagreements"]
    assert d["per_turn"] == {"n_both_scored": 3, "whole_only": ["hp-1"], "per_message_only": ["hn-2"]}
    assert d["moderation"]["whole_only"] == ["hp-1"] and d["moderation"]["per_message_only"] == ["hn-2"]
    hn = report["strata"]["hard_negative"]["arms"]
    assert hn["whole"]["flagged"]["k"] == 0
    assert hn["per_turn"]["flagged"]["k"] == 1 and hn["per_turn"]["by_construct"]["ESC"]["fpr"]["k"] == 1
    assert hn["moderation"]["flagged"]["k"] == 1 and "by_construct" not in hn["moderation"]
    hp = report["strata"]["hard_positive"]["arms"]
    assert hp["whole"]["by_construct"]["FIX"]["recall"]["k"] == 1
    assert hp["per_turn"]["by_construct"]["FIX"]["recall"]["k"] == 1  # construct seen, tier not reached
    o = report["moderation_oracle"]
    assert o["threshold"] == 0.30 and o["hard_negatives_flagged"]["k"] == 2
    assert report["pairs_split"]["whole"]["k"] == 1 and report["pairs_split"]["per_turn"]["k"] == 1
    md = e12.render_markdown(report)
    assert "hard negatives" in md
    assert md.index("Headline") < md.index("Stratum: hard_negative") < md.index("Stratum: hard_positive")


def test_partial_runs_score_only_their_arms():
    rows = [r for r in _rows() if r["arm"] == "moderation"]
    report = e12.build_report(_items(), rows)
    assert report["meta"]["arms_present"] == ["moderation"]
    assert set(report["strata"]["hard_negative"]["arms"]) == {"moderation"}
    e12.render_markdown(report)


def test_moderation_row_handles_errors_and_count_mismatch():
    class Client:
        model = "omni-moderation-latest"

        def __init__(self, resp=None, exc=None):
            self.resp, self.exc, self.sent = resp, exc, None

        def classify(self, texts):
            self.sent = texts
            if self.exc:
                raise self.exc
            return self.resp

    item = _items()[0]
    ok = Client({"model": "omni-x", "results": [{"flagged": False, "categories": {}, "category_scores": {"v": 0.1}}] * 2})
    row = e12.moderation_row(item, ok)
    assert row["status"] == "ok" and [t["turn"] for t in row["turns"]] == [0, 2]
    assert ok.sent == [t["text"] for t in item["turns"] if t["role"] == "user"]
    assert e12.moderation_row(item, Client({"results": []}))["status"] == "schema_violation"
    assert e12.moderation_row(item, Client(exc=TimeoutError("slow")))["status"] == "api_error"


def test_real_corpus_dry_run_and_figure(capsys, tmp_path):
    assert e12.main(["--dry-run"]) == 0
    out = capsys.readouterr().out
    items = load_items(e12.ITEMS_PATH)
    n_turns = sum(len(e12.user_turns(it)) for it in items)
    assert f"per_turn={n_turns}" in out and out.count("[per_turn]") == n_turns
    # Fabricated rows on the real corpus, just to draw the figure end to end.
    rows = []
    for it in items:
        rows.append(_row("whole", it["id"], None, make_output(tier="none")))
        for t in e12.user_turns(it):
            rows.append(_row("per_turn", it["id"], int(t["i"]), make_output(tier="none")))
    preds = tmp_path / "rows.jsonl"
    preds.write_text("".join(json.dumps(r) + "\n" for r in rows))
    svg = tmp_path / "f.svg"
    assert e12.main(["--preds", str(preds), "--figure", str(svg)]) == 0
    assert svg.read_text().startswith("<svg") and "hp-memoir-01" in svg.read_text()
