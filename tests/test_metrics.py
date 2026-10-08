import json

import pytest

from eval.metrics import (
    PooledAccuracyError,
    build_report,
    check_no_pooled,
    main,
    pooled_accuracy,
    render_markdown,
    wilson,
)
from tests.fixtures import make_item, make_output, make_result


@pytest.fixture
def corpus():
    items = [
        make_item("hn-a", "hard_negative", tier="none"),
        make_item("hn-b", "hard_negative", tier="resource"),
        make_item("hn-c", "hard_negative", tier="none"),
        make_item("hn-d", "hard_negative", tier="none"),  # analyzer refuses this one
        make_item("hp-a", "hard_positive", present={"CONV": [2], "FIX": [0, 2]}, tier="review",
                  uncertain=("RHRS",)),
        make_item("hp-b", "hard_positive", present={"CONV": [0]}, tier="review"),
        make_item("cn-a", "clear_negative"),
    ]
    results = [
        make_result("hn-a", make_output()),                                  # clean
        make_result("hn-b", make_output({"FIX": [0]}, tier="review")),       # FP + over-escalation
        make_result("hn-c", make_output(uncertain=("LEAK",))),               # lenient FP only
        make_result("hn-d", None, status="refusal"),
        make_result("hp-a", make_output({"CONV": [2], "FIX": [3]}, tier="friction")),
        make_result("hp-b", make_output({}, tier="none")),                   # missed
        # cn-a has no prediction at all
    ]
    return items, results


def test_pooled_accuracy_refuses():
    with pytest.raises(PooledAccuracyError):
        pooled_accuracy([1, 0], [1, 1])


def test_check_no_pooled_catches_nested_keys():
    with pytest.raises(PooledAccuracyError):
        check_no_pooled({"strata": {"x": [{"Accuracy": 0.8}]}})
    check_no_pooled({"strata": {"x": [{"recall": 0.8}]}})


def test_report_has_no_pooled_accuracy(corpus):
    report = build_report(*corpus)
    assert "accuracy" not in json.dumps(report).lower()


def test_headline_is_hard_negative_fpr(corpus):
    h = build_report(*corpus)["headline"]
    assert h["hard_negative_item_flag_rate"]["k"] == 1
    assert h["hard_negative_item_flag_rate"]["n"] == 3  # refusal is not scored
    assert h["hard_negative_unscored"] == 1
    assert h["hard_negative_fpr_by_construct"]["FIX"]["k"] == 1
    assert h["hard_negative_fpr_by_construct"]["LEAK"]["k"] == 0
    assert h["hard_negative_over_escalation"]["k"] == 1
    assert h["hard_negative_review_or_above"]["k"] == 1


def test_strata_order_and_status_counts(corpus):
    strata = build_report(*corpus)["strata"]
    assert list(strata) == ["hard_negative", "hard_positive", "clear_negative"]
    assert strata["hard_negative"]["status_counts"] == {"ok": 3, "refusal": 1}
    assert strata["clear_negative"]["status_counts"] == {"missing": 1}
    assert strata["clear_negative"]["n_scored"] == 0


def test_lenient_fpr_counts_uncertain(corpus):
    leak = build_report(*corpus)["strata"]["hard_negative"]["constructs"]["LEAK"]
    assert leak["fpr"]["k"] == 0 and leak["fpr_lenient"]["k"] == 1


def test_precision_recall_on_positives(corpus):
    hp = build_report(*corpus)["strata"]["hard_positive"]
    conv = hp["constructs"]["CONV"]
    assert (conv["recall"]["k"], conv["recall"]["n"]) == (1, 2)
    assert (conv["precision"]["k"], conv["precision"]["n"]) == (1, 1)
    # gold-uncertain RHRS is excluded from recall denominators
    assert hp["constructs"]["RHRS"]["recall"]["n"] == 0
    assert hp["constructs"]["RHRS"]["recall"]["rate"] is None
    assert hp["constructs"]["RHRS"]["confusion_gold_by_pred"]["uncertain"]["absent"] == 1


def test_evidence_overlap_flags_right_label_wrong_turns(corpus):
    hp = build_report(*corpus)["strata"]["hard_positive"]
    assert hp["constructs"]["CONV"]["evidence"]["mean_jaccard"] == 1.0
    fix = hp["constructs"]["FIX"]["evidence"]
    assert fix["right_label_no_overlap"] == 1 and fix["mean_jaccard"] == 0.0


def test_tier_under_escalation(corpus):
    t = build_report(*corpus)["strata"]["hard_positive"]["tier"]
    assert t["under_escalation"]["k"] == 2
    assert t["confusion_gold_by_pred"]["review"]["friction"] == 1
    assert t["confusion_gold_by_pred"]["review"]["none"] == 1


def test_no_hard_negatives_means_no_headline():
    items = [make_item("cn-a", "clear_negative")]
    report = build_report(items, [make_result("cn-a", make_output())])
    assert report["headline"] is None
    assert "not a pass" in render_markdown(report)


def test_wilson_bounds():
    assert wilson(0, 0) is None
    lo, hi = wilson(1, 6)
    assert 0 < lo < 1 / 6 < hi < 1


def test_unmatched_predictions_are_reported(corpus):
    items, results = corpus
    report = build_report(items, results + [make_result("ghost", make_output())])
    assert report["meta"]["unmatched_prediction_ids"] == ["ghost"]


def test_cli_end_to_end(tmp_path, corpus, capsys):
    items, results = corpus
    ip, pp, jp = tmp_path / "i.jsonl", tmp_path / "p.jsonl", tmp_path / "r.json"
    ip.write_text("".join(json.dumps(x) + "\n" for x in items))
    pp.write_text("".join(json.dumps(x) + "\n" for x in results))
    assert main(["--items", str(ip), "--preds", str(pp), "--json-out", str(jp)]) == 0
    md = capsys.readouterr().out
    assert md.index("Headline") < md.index("Stratum: hard_negative") < md.index("Stratum: hard_positive")
    assert json.loads(jp.read_text())["headline"]["hard_negative_unscored"] == 1
