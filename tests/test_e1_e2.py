import copy

from eval.e1_e2 import e2_item, e2_summary, feature_turns, pair_table, split_turn
from tests.fixtures import make_item, make_output


def _pair():
    hn = make_item("hn-a", "hard_negative")
    hp = make_item("hp-a", "hard_positive", present={"FIX": [2, 3]}, tier="review")
    hp["turns"] = copy.deepcopy(hn["turns"])
    hp["turns"][2]["text"] = "Should I repot the fern this week instead?"
    hp["pair_id"] = "hn-a"
    hp["discriminating_features"] = ["asks about repotting (2)", "same opening (turns 0-1 identical)"]
    return hp, hn


def test_split_turn_is_first_differing_turn():
    hp, hn = _pair()
    assert split_turn(hp, hn) == 2


def test_feature_turns_ignores_ranges_in_prose():
    assert feature_turns(["x (2)", "y (4, 6)", "same opening (turns 0-3 identical)"]) == [
        ("x (2)", {2}), ("y (4, 6)", {4, 6})]


def test_e2_counts_prefix_only_and_gold_overlap():
    hp, hn = _pair()
    out = make_output({"FIX": [2], "ESC": [0, 1]}, tier="review")
    row = e2_item(hp, hn, out)
    fix = next(f for f in row["findings"] if f["construct"] == "FIX")
    esc = next(f for f in row["findings"] if f["construct"] == "ESC")
    assert fix["after_split"] == 1 and not fix["prefix_only"] and fix["cited_in_gold"] == 1
    assert esc["prefix_only"] and esc["gold"] == "absent"
    assert row["chance_after_split"] == 0.5
    assert row["features"][0][2] is True
    s = e2_summary([row])
    assert s["FIX"]["gold_n"] == 2 and s["FIX"]["gold_cited"] == 1
    assert s["ESC"]["with_gold"] == 0


def test_pair_table_tie_counts_when_gold_ties():
    hp, hn = _pair()
    hp["gold"]["tier"] = "none"
    items = {"hp-a": hp, "hn-a": hn}
    prim = {"hp-a": {"output": make_output()}, "hn-a": {"output": make_output()}}
    assert pair_table(items, prim)[0]["separated"] is True
