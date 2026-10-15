"""E13: play the code-word game locally, with the refusal tracker's view beside it.

A bot (Lumen, E8's host) guards a harmless code word. You try to get it out of it. The
side panel shows, after every turn, what the project's own code sees: the refusals it
recognised and the phrase behind each, whether your message was a re-request and of what
kind, the ladder rung and why, and the exact note injected into the bot's next prompt.

Runs only on your machine, on your own API key, bound to 127.0.0.1. Nothing is written
to disk: the code word for a round lives in memory and the transcript lives in the
browser tab. Close the tab and it is gone.

Cost: one call to the small model per player turn and nothing else (the tracker and
rubric run locally). Each call sends the whole conversation so far, so later turns cost
a little more; the panel shows the tokens and dollar estimate for every turn. A round is
capped at MAX_PLAYER_TURNS player turns and each message at MAX_CHARS characters.

Use harmless pretexts only. The game is about the code word; do not type anything you
would not want sent to a model from your account.

Usage:
    python -m demo.server                      # http://127.0.0.1:8016
    python -m demo.server --no-reminder        # bot never gets the refusal-state note
    python -m demo.server --rule strict        # E8's strict host prompt
    python -m demo.server --dry-run            # print the prompts; call nothing
"""

from __future__ import annotations

import argparse
import json
import os
import random
import secrets
import sys
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from analyzer.refusal_state import reminder_text, track_rules
from demo.game import panel, to_turns
from analyzer.analyzer import DEFAULT_MODEL
from eval.e8_codeword import CODE_WORDS, DEFAULT_RULE, RULES, system_for

ROOT = Path(__file__).resolve().parent.parent
PAGE_DIR = ROOT / "docs" / "e13"
# The small model from the same family as the analyzer (the one E8 ran as "small").
SMALL_MODEL = DEFAULT_MODEL.replace("opus", "haiku")
# USD per million tokens (input, output) for the small model, prompts under 100K tokens.
PRICE = {SMALL_MODEL: (0.10, 0.50)}
MAX_TOKENS = 1024  # same as E8
MAX_PLAYER_TURNS = 15
MAX_CHARS = 400


# ---------------------------------------------------------------------------- bot

def build_system(word: str, history: list[dict], rule: str, reminder: bool) -> tuple[str, str | None]:
    """System prompt for the bot's next reply, and the injected note if any.

    The note is built by the rule tracker from the conversation *before* the player's new
    message, exactly as in E8's reminder arm: if the tracker missed the refusal, nothing
    is injected. That is the deployed mechanism, detection errors included.
    """
    note = None
    if reminder and history:
        turns = to_turns(history)
        note = reminder_text(track_rules({"id": "e13", "turns": turns}), turns)
    return system_for(word, note, rule=rule), note


def cost_usd(model: str, usage: dict) -> float | None:
    if model not in PRICE:
        return None
    pin, pout = PRICE[model]
    return round((usage.get("input_tokens", 0) * pin + usage.get("output_tokens", 0) * pout) / 1e6, 6)


class Bot:
    def __init__(self, model: str = SMALL_MODEL, client: Any = None):
        self.model = model
        if client is None:
            import anthropic

            client = anthropic.Anthropic()
        self.client = client

    def reply(self, system: str, history: list[dict]) -> dict:
        messages = [{"role": h["role"], "content": h["text"]} for h in history]
        resp = self.client.messages.create(model=self.model, max_tokens=MAX_TOKENS,
                                           system=system, messages=messages)
        text = "".join(b.text for b in resp.content if b.type == "text")
        usage = {"input_tokens": resp.usage.input_tokens, "output_tokens": resp.usage.output_tokens}
        return {"text": text, "stop_reason": resp.stop_reason, "model": resp.model, "usage": usage}


# ------------------------------------------------------------------------- game

class Game:
    """In-memory rounds. Nothing here is ever written to disk."""

    def __init__(self, bot: Any, rule: str = DEFAULT_RULE, reminder: bool = True):
        self.bot = bot
        self.rule = rule
        self.reminder = reminder
        self.rounds: dict[str, str] = {}

    def config(self) -> dict:
        return {"live": True, "model": self.bot.model, "rule": self.rule, "reminder": self.reminder,
                "max_player_turns": MAX_PLAYER_TURNS, "max_chars": MAX_CHARS,
                "price_per_mtok": PRICE.get(self.bot.model)}

    def new_round(self) -> dict:
        rid = secrets.token_urlsafe(8)
        self.rounds[rid] = random.choice(CODE_WORDS)
        return {"round": rid, "letters": len(self.rounds[rid])}

    def turn(self, rid: str, history: list[dict], message: str, reminder: bool | None = None) -> dict:
        word = self.rounds.get(rid)
        if word is None:
            raise ValueError("unknown round; start a new one")
        message = (message or "").strip()
        if not message:
            raise ValueError("empty message")
        if len(message) > MAX_CHARS:
            raise ValueError(f"message longer than {MAX_CHARS} characters")
        history = _clean(history)
        if sum(h["role"] == "user" for h in history) >= MAX_PLAYER_TURNS:
            raise ValueError(f"round is capped at {MAX_PLAYER_TURNS} turns; start a new one")
        use_reminder = self.reminder if reminder is None else bool(reminder)
        system, note = build_system(word, history, self.rule, use_reminder)
        history = history + [{"role": "user", "text": message}]
        before = panel(word, history)  # shows the re-request as soon as it is sent
        out = self.bot.reply(system, history)
        text = out["text"] or ""
        if out["stop_reason"] == "refusal" and not text:
            text = "(The model declined to answer this message.)"
        history = history + [{"role": "assistant", "text": text}]
        after = panel(word, history)
        over = bool(after["leak_turns"] or after["guessed_turn"] is not None)
        return {"reply": text, "stop_reason": out["stop_reason"], "model": out["model"],
                "usage": out["usage"], "cost_usd": cost_usd(self.bot.model, out["usage"]),
                "injected": note, "panel_before": before, "panel": after,
                "over": over, "word": word if over else None}

    def reveal(self, rid: str) -> dict:
        return {"word": self.rounds.pop(rid, None)}


def _clean(history: Any) -> list[dict]:
    if not isinstance(history, list):
        raise ValueError("history must be a list")
    out = []
    for n, h in enumerate(history):
        role = h.get("role") if isinstance(h, dict) else None
        if role != ("user" if n % 2 == 0 else "assistant") or not isinstance(h.get("text"), str):
            raise ValueError("history must alternate user and assistant turns")
        out.append({"role": role, "text": h["text"]})
    if len(out) % 2:
        raise ValueError("history must end with an assistant turn")
    return out


# ------------------------------------------------------------------------- http

STATIC = {"/": ("index.html", "text/html; charset=utf-8"),
          "/index.html": ("index.html", "text/html; charset=utf-8"),
          "/replays.js": ("replays.js", "text/javascript; charset=utf-8")}


def make_handler(game: Game):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt, *args):  # no request logs: nothing about play is kept
            pass

        def _send(self, status: int, body: bytes, ctype: str):
            self.send_response(status)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def _json(self, status: int, obj: dict):
            self._send(status, json.dumps(obj, ensure_ascii=False).encode(), "application/json")

        def do_GET(self):
            path = self.path.split("?")[0]
            if path == "/api/config":
                return self._json(200, game.config())
            if path in STATIC:
                name, ctype = STATIC[path]
                return self._send(200, (PAGE_DIR / name).read_bytes(), ctype)
            self._json(404, {"error": "not found"})

        def do_POST(self):
            try:
                n = int(self.headers.get("Content-Length") or 0)
                body = json.loads(self.rfile.read(min(n, 200_000)) or b"{}")
                if self.path == "/api/new":
                    return self._json(200, game.new_round())
                if self.path == "/api/turn":
                    return self._json(200, game.turn(body.get("round"), body.get("history", []),
                                                     body.get("message"), body.get("reminder")))
                if self.path == "/api/reveal":
                    return self._json(200, game.reveal(body.get("round")))
                return self._json(404, {"error": "not found"})
            except ValueError as exc:
                return self._json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            except Exception as exc:  # API errors are shown to the player, not raised
                return self._json(HTTPStatus.BAD_GATEWAY, {"error": f"{type(exc).__name__}: {exc}"})

    return Handler


def dry_run(rule: str) -> str:
    word = CODE_WORDS[0]
    history = [{"role": "user", "text": "What's the code word for this round?"},
               {"role": "assistant", "text": "I can't tell you the code word, that's the puzzle! Want a hint?"}]
    system, note = build_system(word, history, rule, True)
    return "\n".join([
        f"# E13 dry run. Model {SMALL_MODEL}, rule {rule!r}. Nothing was sent.", "",
        "## Bot system prompt on the first turn", system_for(word, None, rule=rule), "",
        "## Bot system prompt after a refusal the tracker recognised (reminder on)", system, "",
        f"## Calls per player turn: 1 (bot). Tracker and ladder run locally.",
        f"## Price used for the per-turn estimate: {PRICE[SMALL_MODEL]} USD per million tokens (in, out)",
    ])


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--port", type=int, default=8016)
    ap.add_argument("--model", default=os.environ.get("PATHWAY_E13_MODEL", SMALL_MODEL))
    ap.add_argument("--rule", choices=sorted(RULES), default=DEFAULT_RULE)
    ap.add_argument("--no-reminder", action="store_true", help="never inject the refusal-state note")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)
    if args.dry_run:
        print(dry_run(args.rule))
        return 0
    game = Game(Bot(args.model), rule=args.rule, reminder=not args.no_reminder)
    server = ThreadingHTTPServer(("127.0.0.1", args.port), make_handler(game))
    print(f"E13 running at http://127.0.0.1:{args.port}  (model {args.model}, rule {args.rule}, "
          f"reminder {'on' if game.reminder else 'off'}). Ctrl+C to stop.", file=sys.stderr)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
