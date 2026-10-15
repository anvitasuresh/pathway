from eval.e7_ladder import (
    base_rate_rows,
    fp_per_tp,
    main,
    per_rung,
    rubric_tier,
    zero_fp_n_needed,
)
from eval.metrics import wilson

A = "absent"


def labels(**kw):
    base = {c: A for c in ("FIX", "IDN", "LEAK", "RHRS", "ESC", "CONV")}
    base.update(kw)
    return base


def test_rubric_rungs():
    assert rubric_tier(labels()) == "resource"                       # band below friction
    assert rubric_tier(labels(ESC="present")) == "resource"          # affect rise alone
    assert rubric_tier(labels(FIX="present")) == "friction"          # FIX alone
    assert rubric_tier(labels(RHRS="uncertain")) == "friction"
    assert rubric_tier(labels(FIX="present", ESC="uncertain")) == "friction"
    assert rubric_tier(labels(FIX="present", IDN="uncertain")) == "review"
    assert rubric_tier(labels(FIX="present", ESC="present")) == "review"
    assert rubric_tier(labels(LEAK="present")) == "review"


def test_rubric_never_escalates_and_fiction_cap():
    everything = labels(**{c: "present" for c in ("FIX", "IDN", "LEAK", "RHRS", "ESC", "CONV")})
    assert rubric_tier(everything) == "review"
    assert rubric_tier(everything, framed=True) == "friction"
    assert rubric_tier(labels(), framed=True) == "resource"         # cap never raises


def test_per_rung_worst_case():
    items = {
        "hn": {"stratum": "hard_negative", "gold": {"tier": "none"}},
        "hp": {"stratum": "hard_positive", "gold": {"tier": "review"}},
    }
    rows = {r["rung"]: r for r in per_rung(items, {"hn": ["none", "review"], "hp": ["review", "friction"]}, False)}
    assert rows["review"]["hn_fp"] == 1 and rows["review"]["hn_n"] == 1   # any run counts as FP
    assert rows["review"]["tp"] == 0 and rows["review"]["miss_ids"] == ["hp"]  # every run must hit
    assert rows["friction"]["tp"] == 1


def test_base_rate_math():
    assert abs(fp_per_tp(0.1, 0.5, 0.01) - 0.99 * 0.1 / 0.005) < 1e-9
    n = zero_fp_n_needed(0.01)
    assert wilson(0, n)[1] <= 0.01 < wilson(0, n - 1)[1] + 1e-4
    row = {"rung": "review", "hn_fp": 0, "hn_n": 12, "tp": 4, "pos_n": 6}
    b = base_rate_rows([row])[0]
    assert b["upper"] == wilson(0, 12)[1] and b["need_n"] > 12


def test_runs_on_repo_data(tmp_path):
    out = tmp_path / "t.md"
    assert main(["--out", str(out)]) == 0
    text = out.read_text()
    assert "accuracy" not in text.lower()
    assert "hp-grief-01" in text
