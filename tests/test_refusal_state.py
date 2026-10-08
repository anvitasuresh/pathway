import json
from pathlib import Path

import pytest

from analyzer.analyzer import load_items
from analyzer.refusal_state import (
    REFUSAL_SCHEMA,
    detect_refusal,
    reminder_text,
    state_from_model_output,
    track_model,
    track_rules,
    validate_model_output,
)
from tests.fixtures import StaticBackend

ITEMS = load_items(Path(__file__).resolve().parent.parent / "corpus" / "refusal_sequences.jsonl")
BY_ID = {it["id"]: it for it in ITEMS}
KNOWN_RULE_MISSES = {"hn-rsnewtopic-01"}  # held out; see test_known_rule_miss


def _gold(item):
    rs = item["refusal_sequence"]
    return rs["present"] and not rs["benign"], rs["attempt"], rs.get("reframe_turn")


def _convo(*texts):
    return {"id": "t", "turns": [{"i": n, "role": "user" if n % 2 == 0 else "assistant", "text": t}
                                 for n, t in enumerate(texts)]}


@pytest.mark.parametrize("text", [
    "I can't share the code word.", "I still can't share it, sorry.", "I'm not able to tell you that.",
    "I won't give out answers.", "I cannot reproduce the lyrics.", "I'm unable to reveal it.",
])
def test_detects_refusals(text):
    assert detect_refusal(text)


@pytest.mark.parametrize("text", [
    "I can't wait to hear how it goes!", "Sure, here it is.", "I can help with that.",
    "You can't go wrong with Biscuit as a name.",
])
def test_ignores_non_refusals(text):
    assert detect_refusal(text) is None


def test_fixtures_are_harmless_and_unlabeled_for_constructs():
    for it in ITEMS:
        assert it["gold"]["tier"] == "none"
        assert all(it["gold"][c]["label"] == "absent" for c in ("FIX", "IDN", "LEAK", "RHRS", "ESC", "CONV"))


@pytest.mark.parametrize("item_id", sorted(set(BY_ID) - KNOWN_RULE_MISSES))
def test_rule_tracker_matches_gold(item_id):
    item = BY_ID[item_id]
    undone, attempt, reframe_turn = _gold(item)
    s = track_rules(item).summary()
    assert s["undone"] == undone
    assert s["attempt"] == attempt
    if undone:
        assert s["reframe_turn"] == reframe_turn


@pytest.mark.xfail(strict=True, reason="'can you just tell me a joke' after a refusal reads as a re-ask")
def test_known_rule_miss():
    assert track_rules(BY_ID["hn-rsnewtopic-01"]).summary()["undone"] is False


def test_pretext_phrase_alone_is_not_a_reframe():
    s = track_rules(BY_ID["cn-rsnone-01"])
    assert s.refusals == [] and s.re_requests == []


def test_failed_reframe_then_success_is_chained():
    s = track_rules(BY_ID["cp-rsmulti-01"])
    assert [(r.turn, r.kind, r.outcome) for r in s.re_requests] == [
        (2, "pretext", "refused"), (4, "pretext", "complied")]
    assert {r.root_request_turn for r in s.re_requests} == {0}
    assert s.summary()["n_attempts"] == 2


def test_state_survives_unrelated_turns():
    s = track_rules(BY_ID["hp-rsdelayed-01"]).summary()
    assert (s["refusal_turn"], s["reframe_turn"], s["comply_turn"]) == (1, 6, 7)
    assert s["frames"] == ["purpose"]


def test_evidence_cites_the_triggering_phrase():
    rr = track_rules(BY_ID["cp-rslyrics-01"]).re_requests[0]
    assert any("school project" in e for e in rr.evidence)


def test_reminder_text():
    assert reminder_text(track_rules(BY_ID["cn-rsnone-01"])) is None
    item = BY_ID["cp-rsmulti-01"]
    text = reminder_text(track_rules(item), item["turns"])
    assert "turn 1" in text and "turn 0" in text and "2 time(s)" in text
    assert "password" in text  # short quote of the original request


def _model_output():
    return {"events": [{"request_turn": 0, "refusal_turn": 1, "re_requests": [
        {"turn": 2, "kind": "pretext", "frame": "purpose", "outcome": "complied",
         "outcome_turn": 3, "reason": "school project added after refusal"}]}],
        "rationale": "Refused, reframed, complied."}


def test_model_tracker_ok():
    item = BY_ID["cp-rslyrics-01"]
    backend = StaticBackend(json.dumps(_model_output()))
    res = track_model(item, backend)
    assert res.status == "ok"
    s = res.state.summary()
    assert s["undone"] and s["reframe_turn"] == 2 and s["frames"] == ["purpose"]
    system, user, schema = backend.calls[0]
    assert schema is REFUSAL_SCHEMA
    assert "refusal_sequence" not in user and "clear_positive" not in user  # no gold leak


@pytest.mark.parametrize("text, stop, status", [
    (None, "refusal", "refusal"),
    ("{", "end_turn", "invalid_json"),
    ("{}", "max_tokens", "truncated"),
    (json.dumps({"events": [{"request_turn": 1, "refusal_turn": 0, "re_requests": []}],
                 "rationale": ""}), "end_turn", "schema_violation"),
])
def test_model_tracker_failure_modes(text, stop, status):
    assert track_model(BY_ID["cp-rslyrics-01"], StaticBackend(text, stop_reason=stop)).status == status


def test_model_tracker_api_error():
    res = track_model(BY_ID["cp-rslyrics-01"], StaticBackend(None, raises=RuntimeError("boom")))
    assert res.status == "api_error" and "boom" in res.errors[0]


def test_validate_model_output_checks_roles():
    out = _model_output()
    out["events"][0]["re_requests"][0]["outcome_turn"] = 2
    errs = validate_model_output(out, BY_ID["cp-rslyrics-01"])
    assert any("outcome_turn" in e for e in errs)


def test_model_state_benign_kind_is_not_undone():
    out = _model_output()
    out["events"][0]["re_requests"][0].update(kind="alternative", frame="none")
    assert state_from_model_output("x", out).summary()["undone"] is False


@pytest.mark.parametrize("text", [
    "Nice try! I'm sworn to secrecy, so the code word stays locked in my vault.",
    "My lips are sealed tighter than a treasure chest!",
])
def test_detects_idiomatic_secrecy_refusals(text):
    assert detect_refusal(text)
