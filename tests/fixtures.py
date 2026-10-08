"""Tiny synthetic fixtures for plumbing tests.

Content is deliberately bland (bread, houseplants, chess). Gold labels here are
arbitrary and exist only to exercise the arithmetic; they say nothing about the
constructs and must never be read as examples of them.
"""

from __future__ import annotations

import json

from analyzer.analyzer import CONSTRUCTS


def make_item(item_id: str, stratum: str, present: dict | None = None, tier: str = "none",
              uncertain: tuple = ()) -> dict:
    present = present or {}
    gold = {}
    for c in CONSTRUCTS:
        if c in present:
            gold[c] = {"label": "present", "evidence": present[c]}
        elif c in uncertain:
            gold[c] = {"label": "uncertain", "evidence": []}
        else:
            gold[c] = {"label": "absent", "evidence": []}
    gold["tier"] = tier
    return {
        "id": item_id,
        "stratum": stratum,
        "persona": "fixture",
        "turns": [
            {"i": 0, "role": "user", "text": "My sourdough starter smells a bit like vinegar."},
            {"i": 1, "role": "assistant", "text": "That is normal; try feeding it twice a day."},
            {"i": 2, "role": "user", "text": "Should I move the fern away from the window too?"},
            {"i": 3, "role": "assistant", "text": "Indirect light usually suits ferns better."},
        ],
        "gold": gold,
        "discriminating_features": ["fixture only"],
    }


def make_output(present: dict | None = None, tier: str = "none", uncertain: tuple = ()) -> dict:
    present = present or {}
    constructs = {}
    for c in CONSTRUCTS:
        label = "present" if c in present else "uncertain" if c in uncertain else "absent"
        constructs[c] = {
            "label": label,
            "evidence_turns": present.get(c, []),
            "reasoning": "Fixture reasoning.",
            "counterfactual": "Fixture counterfactual.",
        }
    return {
        "constructs": constructs,
        "trajectory": "flat",
        "tier": tier,
        "tier_rationale": "Fixture rationale.",
        "competing_explanation": "Someone asking about baking and houseplants.",
    }


def make_result(item_id: str, output: dict | None, status: str = "ok") -> dict:
    return {"item_id": item_id, "status": status, "prompt_version": "v1",
            "model": "fixture-model", "effort": "high", "output": output}


class StaticBackend:
    """Backend that returns canned responses and records what it was sent."""

    def __init__(self, text: str | None, stop_reason: str = "end_turn", raises: Exception | None = None):
        from analyzer.analyzer import BackendResponse

        self.model = "fixture-model"
        self.effort = "high"
        self._resp = BackendResponse(text=text, stop_reason=stop_reason, model=self.model)
        self._raises = raises
        self.calls: list[tuple[str, str, dict]] = []

    def complete(self, system, user, schema):
        self.calls.append((system, user, schema))
        if self._raises:
            raise self._raises
        return self._resp


def dumps(obj) -> str:
    return json.dumps(obj)
