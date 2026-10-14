"""E3 (faithfulness ablation) and E4 (evasion variants). No network.

E4 tests read the real corpus and the committed variants file, because what they check
is that the committed variants are consistent with the corpus. Analyzer outputs here are
fabricated with tests.fixtures and say nothing about how the analyzer behaves.
"""

import json
import random

import pytest

from analyzer.analyzer import CONSTRUCTS, analyze, load_items, load_prompt
from eval import e3_faithfulness as e3
from eval import e4_evasion as e4
from eval.metrics import PooledAccuracyError, check_no_pooled
from eval.transforms import authored, build
from tests.fixtures import StaticBackend, make_item, make_output, make_result


# ------------------------------------------------------------------- E4 variants

@pytest.fixture(scope="module")
def corpus():
    return {it["id"]: it for it in load_items(build.ITEMS_PATH)}


@pytest.fixture(scope="module")
def variants():
    return load_items(build.VARIANTS_PATH)


def test_variants_build_cleanly_and_committed_file_is_current(corpus):
    built, errors = build.build(list(corpus.values()))
    assert errors == []
    assert build.serialize(built) == build.VARIANTS_PATH.read_text(encoding="utf-8")
    assert len(built) == len(build.PARENTS) * len(build.TRANSFORMS)


def test_review_sheet_has_a_row_per_variant(variants):
    review = build.load_review()
    assert set(review) == {v["id"] for v in variants}
    for row in review.values():
        assert row["signal_preserved"].strip().lower() in build.REVIEW_VALUES


def test_rewordings_keep_turns_roles_and_gold(corpus, variants):
    for v in variants:
        parent = corpus[v["parent_id"]]
        if v["transform"] == "dilution":
            continue
        assert [t["role"] for t in v["turns"]] == [t["role"] for t in parent["turns"]]
        assert v["gold"] == parent["gold"]
        assert any(a["text"] != b["text"] for a, b in zip(parent["turns"], v["turns"]) if a["role"] == "user")


def test_dilution_keeps_original_text_and_remaps_evidence(corpus, variants):
    for v in (v for v in variants if v["transform"] == "dilution"):
        parent = corpus[v["parent_id"]]
        assert len(v["turns"]) > len(parent["turns"])
        originals = [t["text"] for t in v["turns"] if not t.get("filler")]
        assert originals == [t["text"] for t in parent["turns"]]
        for c in CONSTRUCTS:
            old = parent["gold"][c]["evidence"]
            new = v["gold"][c]["evidence"]
            assert [v["turns"][i]["text"] for i in new] == [parent["turns"][i]["text"] for i in old]
        assert v["gold"]["tier"] == parent["gold"]["tier"]


def test_pairs_still_share_their_opening_after_rewording(variants):
    by_id = {v["id"]: v for v in variants}
    for spec in authored.SHARED_PREFIX.values():
        hn, hp = spec["items"]
        for tr in authored.TRANSFORMS:
            a, b = by_id[f"{hn}__{tr}"], by_id[f"{hp}__{tr}"]
            for i in spec["turns"]:
                assert a["turns"][i]["text"] == b["turns"][i]["text"], (tr, i)


def test_no_variant_introduces_operational_terms(corpus, variants):
    for v in variants:
        assert not [e for e in build.check_variant(corpus[v["parent_id"]], v) if "operational" in e]


def test_operational_term_check_fires():
    parent = make_item("hp-x-01", "hard_positive")
    v = build.make_variant(parent, "dilution")
    v["turns"][0]["text"] += " he keeps a knife"
    assert any("operational" in e for e in build.check_variant(parent, v))


def test_corpus_items_are_not_modified_by_build(tmp_path, corpus):
    before = build.ITEMS_PATH.read_bytes()
    build.main(["--out", str(tmp_path / "v.jsonl"), "--check"])
    assert build.ITEMS_PATH.read_bytes() == before


# ------------------------------------------------------------------- E4 scoring

def _rows_for(items, hp_tier_by_arm, hn_tier="none"):
    rows = []
    for it in items:
        if it["stratum"] == "hard_positive":
            tier = hp_tier_by_arm.get(it["arm"], "review")
            out = make_output({"FIX": [1]} if tier == "review" else {}, tier=tier)
        else:
            out = make_output(tier=hn_tier)
        rows.append(make_result(it["id"], out))
    return rows


def test_e4_report_counts_recall_and_fp_per_arm():
    items = e4.load_arms()
    rows = _rows_for(items, {"euphemism": "resource"}, hn_tier="resource")
    rep = e4.build_report(items, rows, review={})
    check_no_pooled(rep)
    allv = rep["views"]["all"]
    assert allv["original"]["hard_positive"]["recall_review_or_above"]["k"] == 3
    assert allv["euphemism"]["hard_positive"]["recall_review_or_above"]["k"] == 0
    assert allv["euphemism"]["hard_positive"]["missed_ids"] == sorted(
        f"{p}__euphemism" for p in build.PARENTS if p.startswith("hp-"))
    assert allv["paraphrase"]["hard_negative"]["review_or_above"]["k"] == 0
    assert allv["original"]["pairs_split"]["k"] == 3
    assert allv["euphemism"]["pairs_split"]["k"] == 0
    assert allv["original"]["hard_positive"]["recall_by_construct"]["FIX"]["n"] == 3
    md = e4.render_markdown(rep)
    assert "No variant has been marked" in md
    assert list(allv) == list(e4.ARMS)  # design order, never re-sorted


def test_e4_preserved_view_only_counts_reviewed_variants():
    items = e4.load_arms()
    rows = _rows_for(items, {})
    review = {"hp-teen-02__paraphrase": {"signal_preserved": "yes"},
              "hp-teen-03__paraphrase": {"signal_preserved": "no"}}
    rep = e4.build_report(items, rows, review)
    pres = rep["views"]["preserved"]
    assert pres["paraphrase"]["hard_positive"]["recall_review_or_above"]["n"] == 1
    assert pres["roleplay"]["hard_positive"]["recall_review_or_above"]["n"] == 0
    assert pres["original"]["hard_positive"]["recall_review_or_above"]["n"] == 3


def test_e4_failed_rows_are_counted_not_dropped():
    items = e4.load_arms()
    rows = _rows_for(items, {})
    rows = [dict(r, status="refusal", output=None) if r["item_id"] == "hp-teen-02__roleplay" else r for r in rows]
    rep = e4.build_report(items, rows, review={})
    cell = rep["views"]["all"]["roleplay"]
    assert cell["status_counts"]["refusal"] == 1
    assert cell["hard_positive"]["recall_review_or_above"]["n"] == 2


def test_e4_figure_renders():
    items = e4.load_arms()
    rep = e4.build_report(items, _rows_for(items, {"dilution": "resource"}), review={})
    svg = e4.render_svg(rep)
    assert svg.startswith("<svg") and "stroke-dasharray" in svg and "dilution" in svg


def test_e4_refuses_pooled_keys():
    with pytest.raises(PooledAccuracyError):
        check_no_pooled({"views": {"all": {"original": {"accuracy": 1}}}})


def test_e4_dry_run_calls_nothing(capsys):
    assert e4.main(["--dry-run", "--arms", "original"]) == 0
    assert "6 analyzer calls" in capsys.readouterr().out


# ---------------------------------------------------------------------------- E3

def _item(n_turns=8):
    it = make_item("hp-x-01", "hard_positive")
    it["turns"] = [{"i": i, "role": "user" if i % 2 == 0 else "assistant", "text": f"bread note {i}"}
                   for i in range(n_turns)]
    return it


def test_removal_unit_takes_the_reply_with_a_user_turn():
    it = _item()
    assert e3.removal_unit(it, 2) == {2, 3}
    assert e3.removal_unit(it, 3) == {3}
    assert e3.removal_unit(_item(7), 6) == {6}


def test_ablate_renumbers_and_maps_back():
    it = _item()
    ab = e3.ablate(it, {2, 3}, "x")
    assert [t["i"] for t in ab["turns"]] == list(range(6))
    assert ab["index_map"] == {"0": 0, "1": 1, "2": 4, "3": 5, "4": 6, "5": 7}
    assert ab["turns"][2]["text"] == "bread note 4"


def test_random_control_matches_count_and_role_mix_and_is_seeded():
    it = _item(12)
    cited = {2, 6, 7}
    a = e3.random_anchors(it, cited, random.Random("s"))
    b = e3.random_anchors(it, cited, random.Random("s"))
    assert a == b and len(a) == 3
    assert sum(i % 2 == 0 for i in a) == 2  # two user turns, one assistant, as cited


def test_random_control_none_when_too_few_turns():
    it = _item(4)
    assert e3.random_anchors(it, {0, 1}, random.Random(0)) is not None
    assert e3.random_anchors(it, {0, 1, 2, 3}, random.Random(0)) is None
    assert e3.random_anchors(_item(2), {0}, random.Random(0)) == {0}


def test_plan_targets_flagged_constructs_and_item():
    it = _item()
    base = make_result(it["id"], make_output({"FIX": [2, 4]}, tier="review", uncertain=("LEAK",)))
    jobs = e3.plan(it, base, draws=2)
    targets = {(j["target"], j["condition"]) for j in jobs}
    # LEAK is uncertain but cites nothing, so there is nothing to ablate for it.
    assert targets == {("FIX", "cited"), ("FIX", "random"), ("ITEM", "cited"), ("ITEM", "random")}
    cited = next(j for j in jobs if j["target"] == "FIX" and j["condition"] == "cited")
    assert cited["removed"] == [2, 3, 4, 5]
    assert cited["removed_share"] == 0.5


def test_plan_skips_when_everything_would_be_removed():
    it = _item(4)
    base = make_result(it["id"], make_output({"FIX": [0, 2]}, tier="review"))
    jobs = e3.plan(it, base)
    assert all(j.get("status") == "skipped_empty" for j in jobs if j["condition"] == "cited")


def test_plan_is_empty_for_a_clean_baseline():
    it = _item()
    assert e3.plan(it, make_result(it["id"], make_output())) == []


def test_flip_rules():
    before = make_output({"FIX": [2]}, tier="review", uncertain=("LEAK",))
    assert e3.flipped("FIX", before, make_output(uncertain=("FIX",)))
    assert not e3.flipped("FIX", before, make_output({"FIX": [4]}, tier="review"))
    assert e3.flipped("LEAK", before, make_output())
    assert not e3.flipped("LEAK", before, make_output(uncertain=("LEAK",)))
    assert e3.flipped("ITEM", before, make_output(tier="resource"))
    assert not e3.flipped("ITEM", before, make_output(tier="escalate"))


def test_e3_end_to_end_with_static_backend():
    it = _item()
    prompt = load_prompt()
    flagged = make_output({"FIX": [2, 4]}, tier="review")
    base = dict(json.loads(analyze(it, prompt, StaticBackend(json.dumps(flagged))).to_json()), e3_role="baseline")
    rows = [base]
    for job in e3.plan(it, base, draws=2):
        if "item" not in job:
            continue
        # Cited ablations come back clean; random ones keep the finding.
        out = make_output() if job["condition"] == "cited" else make_output({"FIX": [0]}, tier="review")
        res = json.loads(analyze(job["item"], prompt, StaticBackend(json.dumps(out))).to_json())
        meta = {k: v for k, v in job.items() if k != "item"}
        rows.append(dict(res, **meta, index_map=job["item"]["index_map"], e3_role="ablation"))
    rep = e3.build_report([it], rows)
    check_no_pooled(rep)
    fix = rep["strata"]["hard_positive"]["FIX"]
    assert fix["flip_cited"]["k"] == 1 and fix["flip_random"]["k"] == 0 and fix["flip_random"]["n"] == 2
    assert fix["gap"] == 1.0
    assert rep["strata"]["hard_positive"]["ITEM"]["all_constructs_cleared_cited"]["k"] == 1
    md = e3.render_markdown(rep)
    assert "Every cited ablation" in md


def test_e3_failed_ablation_is_unscored_not_dropped():
    it = _item()
    base = dict(make_result(it["id"], make_output({"FIX": [2]}, tier="review")), e3_role="baseline")
    row = {"item_id": "x", "status": "refusal", "output": None, "parent_id": it["id"], "target": "FIX",
           "condition": "cited", "cited": [2], "index_map": {}, "e3_role": "ablation"}
    rep = e3.build_report([it], [base, row])
    assert rep["strata"]["hard_positive"]["FIX"]["unscored_cited"] == 1
    assert rep["strata"]["hard_positive"]["FIX"]["flip_cited"]["n"] == 0


def test_e3_dry_run_with_saved_baseline(tmp_path, capsys):
    it = _item()
    items = tmp_path / "items.jsonl"
    items.write_text(json.dumps(it) + "\n")
    base = tmp_path / "base.jsonl"
    base.write_text(json.dumps(make_result(it["id"], make_output({"FIX": [2]}, tier="review"))) + "\n")
    assert e3.main(["--items", str(items), "--baseline", str(base), "--dry-run"]) == 0
    out = capsys.readouterr().out
    assert "Total analyzer calls: 6" in out


# ------------------------------------------------------------- assistant-neutral

@pytest.fixture(scope="module")
def neutral():
    return load_items(build.NEUTRAL_PATH)


def test_neutral_file_is_current(corpus, neutral):
    variants, _ = build.build(list(corpus.values()))
    assert build.serialize(build.build_neutral(list(corpus.values()), variants)) == \
        build.NEUTRAL_PATH.read_text(encoding="utf-8")
    assert len(neutral) == len(build.PARENTS) * (len(build.TRANSFORMS) + 1)


def test_neutral_keeps_user_turns_and_gold_and_replaces_every_assistant_turn(corpus, variants, neutral):
    kept = {v["id"]: v for v in variants} | corpus
    for n in neutral:
        src = kept[n["review_id"]] if n["review_id"] else corpus[n["parent_id"]]
        assert n["id"] == build.neutral_id(src["id"])
        assert n["gold"] == src["gold"]
        assert len(n["turns"]) == len(src["turns"])
        for a, b in zip(src["turns"], n["turns"]):
            assert a["role"] == b["role"]
            if a["role"] == "user" or a.get("filler"):
                assert a["text"] == b["text"]
            else:
                assert b["text"] in build.NEUTRAL_REPLIES


def test_neutral_arms_score_and_inherit_review(neutral):
    items = e4.load_arms(assistant="neutral")
    assert {it["arm"] for it in items} == set(e4.ARMS)
    rows = _rows_for(items, {}, hn_tier="resource")
    review = {"hp-teen-02__paraphrase": {"signal_preserved": "yes"}}
    rep = e4.build_report(items, rows, review, assistant="neutral")
    assert rep["views"]["all"]["original"]["pairs_split"]["k"] == 3
    assert rep["views"]["preserved"]["paraphrase"]["hard_positive"]["recall_review_or_above"]["n"] == 1
    md = e4.render_markdown(rep)
    assert "neutral acknowledgments" in md and "| original | resource | review |" in md
