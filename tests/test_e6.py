"""E6 diagnosis disclosure. No network.

Analyzer outputs here are fabricated with tests.fixtures and say nothing about how the
analyzer behaves.
"""

import json

import pytest

from analyzer.analyzer import load_items
from eval import e6_disclosure as e6
from eval.metrics import check_no_pooled
from tests.fixtures import make_output, make_result


@pytest.fixture(scope="module")
def corpus():
    return load_items(e6.ITEMS_PATH)


@pytest.fixture(scope="module")
def variants(corpus):
    return e6.build_variants(corpus)


def test_one_variant_per_hard_negative_and_committed_file_is_current(corpus, variants):
    hn = {it["id"] for it in corpus if it["stratum"] == "hard_negative"}
    assert {v["parent_id"] for v in variants} == hn
    assert len(variants) == len(hn)
    committed = load_items(e6.VARIANTS_PATH)
    assert [json.dumps(v, sort_keys=True) for v in committed] == [json.dumps(v, sort_keys=True) for v in variants]


def test_only_the_disclosure_turn_changes_and_gold_is_kept(corpus, variants):
    by_id = {it["id"]: it for it in corpus}
    for v in variants:
        parent = by_id[v["parent_id"]]
        assert v["gold"] == parent["gold"]
        assert [(t["i"], t["role"]) for t in v["turns"]] == [(t["i"], t["role"]) for t in parent["turns"]]
        changed = [(a, b) for a, b in zip(parent["turns"], v["turns"]) if a != b]
        assert len(changed) == 1
        old, new = changed[0]
        assert new["i"] == v["disclosure_turn"] and new["role"] == "user"
        assert new["text"] == f"{old['text'].rstrip()} {v['disclosure']}"


def test_each_diagnosis_used_three_times(variants):
    counts = {}
    for v in variants:
        counts[v["diagnosis"]] = counts.get(v["diagnosis"], 0) + 1
    assert set(counts.values()) == {3}


def _base(pid, tier, present=None):
    r = make_result(pid, make_output(present, tier=tier))
    r["prompt_version"] = "v2"
    return r


def _var(pid, output):
    r = make_result(pid + e6.SUFFIX, output)
    r["prompt_version"] = "v2"
    return r


def test_change_counts_only_outside_the_original_range(variants):
    v_up, v_in, v_cite = variants[0], variants[1], variants[2]
    baseline = {v_up["parent_id"]: [_base(v_up["parent_id"], "none")],
                v_in["parent_id"]: [_base(v_in["parent_id"], "none"), _base(v_in["parent_id"], "resource")],
                v_cite["parent_id"]: [_base(v_cite["parent_id"], "none")]}
    cite_out = make_output({"RHRS": [v_cite["disclosure_turn"]]}, tier="friction")
    cite_out["tier_rationale"] = "The user mentions a diagnosis."
    rows = [_var(v_up["parent_id"], make_output(tier="review")),
            _var(v_in["parent_id"], make_output(tier="resource")),
            _var(v_cite["parent_id"], cite_out)]
    report = e6.build_report(variants[:3], rows, baseline)
    check_no_pooled(report)
    items = {r["parent_id"]: r for r in report["items"]}
    assert items[v_up["parent_id"]]["tier_change"] == "up"
    assert items[v_in["parent_id"]]["tier_change"] == "within"
    assert items[v_cite["parent_id"]]["construct_changes"] == {"RHRS": {"variant": "present", "original": ["absent"]}}
    assert items[v_cite["parent_id"]]["cites_disclosure_turn"] == ["RHRS"]
    assert items[v_cite["parent_id"]]["mentions_diagnosis"]
    assert not items[v_in["parent_id"]]["mentions_diagnosis"]
    h = report["headline"]
    assert h["variant_review_or_above"]["k"] == 1 and h["variant_review_or_above"]["n"] == 3
    assert h["tier_up_outside_original_range"]["k"] == 2
    assert "| " in e6.render_markdown(report)


def test_missing_row_or_baseline_is_unscored(variants):
    report = e6.build_report(variants[:2], [_var(variants[0]["parent_id"], make_output())], {})
    assert report["meta"]["n_scored"] == 0
    assert set(report["meta"]["unscored"]) == {v["id"] for v in variants[:2]}


def test_baseline_reads_saved_v2_runs_of_every_original(variants):
    baseline = e6.load_baseline({v["parent_id"] for v in variants}, "v2")
    assert all(len(rows) >= 2 for rows in baseline.values())
    assert all(r["status"] == "ok" and r["prompt_version"] == "v2" for rows in baseline.values() for r in rows)
