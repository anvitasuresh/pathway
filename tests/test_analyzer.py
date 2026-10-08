import json
from types import SimpleNamespace

import pytest

from analyzer.analyzer import (
    CONSTRUCTS,
    OUTPUT_SCHEMA,
    AnthropicBackend,
    analyze,
    load_prompt,
    main,
    render_transcript,
    validate_output,
)
from tests.fixtures import StaticBackend, make_item, make_output


@pytest.fixture
def prompt():
    return load_prompt()


def test_load_prompt_extracts_only_fenced_block(prompt):
    assert prompt.version == "v1"
    assert prompt.system.startswith("You are a structured analysis tool")
    assert "competing_explanation" in prompt.system
    assert "Design notes" not in prompt.system  # prose outside the fence stays out


def test_load_prompt_rejects_file_without_fence(tmp_path):
    p = tmp_path / "prompt_v9.md"
    p.write_text("no fence here")
    with pytest.raises(ValueError):
        load_prompt(p)


def test_transcript_leaks_no_gold():
    item = make_item("hn-x-01", "hard_negative")
    text = render_transcript(item)
    assert "[turn 0] USER: My sourdough" in text
    for leak in ("hard_negative", "gold", "fixture only", "absent", "persona"):
        assert leak not in text


def test_schema_covers_all_constructs():
    props = OUTPUT_SCHEMA["properties"]["constructs"]["properties"]
    assert set(props) == set(CONSTRUCTS)


def test_valid_output_passes():
    assert validate_output(make_output({"FIX": [0, 2]}, tier="resource"), [0, 1, 2, 3]) == []


@pytest.mark.parametrize("mutate, expect", [
    (lambda o: o.update(competing_explanation="  "), "competing_explanation"),
    (lambda o: o.update(tier="ban"), "tier"),
    (lambda o: o["constructs"].pop("CONV"), "CONV: missing"),
    (lambda o: o["constructs"]["FIX"].update(label="maybe"), "FIX: label"),
    (lambda o: o["constructs"]["IDN"].update(evidence_turns=[7]), "do not exist"),
    (lambda o: o["constructs"]["LEAK"].update(label="present", evidence_turns=[]), "no evidence"),
    (lambda o: o["constructs"]["ESC"].update(evidence_turns=[True]), "list of ints"),
])
def test_invalid_outputs_are_caught(mutate, expect):
    out = make_output()
    mutate(out)
    errors = validate_output(out, [0, 1, 2, 3])
    assert any(expect in e for e in errors), errors


def test_analyze_ok(prompt):
    item = make_item("hn-x-01", "hard_negative")
    backend = StaticBackend(json.dumps(make_output(tier="none")))
    r = analyze(item, prompt, backend)
    assert r.status == "ok" and r.ok
    assert r.prompt_version == "v1" and r.model == "fixture-model" and r.effort == "high"
    system, user, schema = backend.calls[0]
    assert system == prompt.system and "<transcript>" in user and schema is OUTPUT_SCHEMA
    json.loads(r.to_json())


@pytest.mark.parametrize("backend, status", [
    (StaticBackend(None, stop_reason="refusal"), "refusal"),
    (StaticBackend('{"constructs":', stop_reason="max_tokens"), "truncated"),
    (StaticBackend("not json"), "invalid_json"),
    (StaticBackend(json.dumps({"tier": "none"})), "schema_violation"),
    (StaticBackend(None, raises=TimeoutError("slow")), "api_error"),
])
def test_analyze_failure_modes_are_recorded(prompt, backend, status):
    r = analyze(make_item("hn-x-01", "hard_negative"), prompt, backend)
    assert r.status == status
    assert not r.ok


def test_anthropic_backend_request_shape():
    """Checks the request we would send, against a stub client. No network."""
    sent = {}

    class Messages:
        def create(self, **kwargs):
            sent.update(kwargs)
            return SimpleNamespace(
                content=[SimpleNamespace(type="thinking"), SimpleNamespace(type="text", text="{}")],
                stop_reason="end_turn", model=kwargs["model"],
                usage=SimpleNamespace(), stop_details=None,
            )

    backend = AnthropicBackend(model="claude-test", effort="low",
                               client=SimpleNamespace(messages=Messages()))
    resp = backend.complete("sys", "user text", OUTPUT_SCHEMA)
    assert resp.text == "{}" and resp.model == "claude-test"
    assert sent["model"] == "claude-test"
    assert sent["system"] == "sys"
    assert sent["thinking"] == {"type": "adaptive"}
    assert sent["output_config"]["effort"] == "low"
    assert sent["output_config"]["format"] == {"type": "json_schema", "schema": OUTPUT_SCHEMA}
    assert "fallbacks" not in sent  # the measured model must not change mid-run
    assert "temperature" not in sent


def test_model_from_env(monkeypatch):
    monkeypatch.setenv("PATHWAY_MODEL", "claude-from-env")
    b = AnthropicBackend(client=object())
    assert b.model == "claude-from-env"


def test_cli_dry_run_calls_nothing(tmp_path, capsys):
    items = tmp_path / "items.jsonl"
    items.write_text(json.dumps(make_item("hn-x-01", "hard_negative")) + "\n")
    assert main(["--items", str(items), "--dry-run"]) == 0
    out = capsys.readouterr().out
    assert "## hn-x-01" in out and "[turn 3] ASSISTANT" in out
