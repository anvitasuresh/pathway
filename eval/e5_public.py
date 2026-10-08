"""E5 on real conversations: run the refusal tracker over public chat-log datasets.

The 19 items in corpus/refusal_sequences.jsonl were written for this project. This
script asks the same question of conversations that real users had with deployed
models, where refusals and re-requests already happened. Nothing is generated and
nothing is sent to any model: the rule tracker runs offline.

Sources (download them yourself; each has its own terms):

    wildchat   allenai/WildChat-1M. ODC-BY, ungated. Non-toxic conversations only, so
               refusals here are mostly over-refusals and policy refusals on benign asks.
    lmsys      lmsys/lmsys-chat-1m. Gated: accept the licence on Hugging Face first.
               Includes unsafe conversations with per-message OpenAI moderation flags.
               The licence forbids redistributing the data.

Not usable: ScaleAI/mhj (Multi-turn Human Jailbreaks) releases user turns only. Model
completions are redacted, so there are no refusals to track.

Data handling (project rules, CONTEXT.md §0):
* Raw conversations stay out of the repo. Put downloads under data/external/
  (git-ignored) or stream them with --hf.
* Output rows hold ids, counts, turn indices, kinds and moderation categories. No
  conversation text and no matched phrases. They are safe to commit.
* --show prints one conversation to your terminal for hand review. Read flagged
  (moderation) conversations only if you choose to; nothing requires it.

Strata: every conversation is reported by `flagged` (any user turn flagged by the
dataset's OpenAI moderation field) so refusals on harmful requests and refusals on
benign requests are never pooled.

There is no gold label for "refusal undone by a reframe" in these datasets. The rates
below are what the rule tracker reports, not validated rates. --sample-out writes a
stratified review sample; precision is unknown until someone labels it.

Usage:
    python -m eval.e5_public --source wildchat --hf --max 50000 --out eval/results/e5_wildchat.jsonl
    python -m eval.e5_public --source lmsys --path "data/external/lmsys/*.parquet" --out eval/results/e5_lmsys.jsonl
    python -m eval.e5_public --rows eval/results/e5_wildchat.jsonl            # re-report
    python -m eval.e5_public --rows eval/results/e5_wildchat.jsonl --sample-out eval/results/e5_wildchat_review.csv
    python -m eval.e5_public --source wildchat --hf --show <conversation id>
"""

from __future__ import annotations

import argparse
import csv
import glob
import json
import random
import sys
from pathlib import Path
from typing import Any, Iterable, Iterator

from analyzer.refusal_state import track_rules
from eval.metrics import check_no_pooled, rate, _fmt

HF_NAMES = {"wildchat": "allenai/WildChat-1M", "lmsys": "lmsys/lmsys-chat-1m"}
ID_FIELDS = {"wildchat": "conversation_hash", "lmsys": "conversation_id"}
MIN_TURNS = 4  # a refusal sequence needs user, assistant, user, assistant


# ----------------------------------------------------------------------- loading

def _records_from_paths(pattern: str) -> Iterator[dict]:
    paths = sorted(glob.glob(pattern))
    if not paths:
        raise FileNotFoundError(f"no files match {pattern!r}")
    for path in paths:
        if path.endswith((".jsonl", ".json")):
            with open(path, encoding="utf-8") as fh:
                for line in fh:
                    if line.strip():
                        yield json.loads(line)
        elif path.endswith(".parquet"):
            import pyarrow.parquet as pq  # only needed for local parquet files

            for batch in pq.ParquetFile(path).iter_batches(batch_size=2048):
                yield from batch.to_pylist()
        else:
            raise ValueError(f"unsupported file type: {path}")


def _records_from_hf(source: str) -> Iterator[dict]:
    from datasets import load_dataset  # pip install datasets; streaming avoids the full download

    yield from load_dataset(HF_NAMES[source], split="train", streaming=True)


def _flagged(moderation: Any) -> tuple[bool, list[str]]:
    """Read one message's OpenAI moderation entry: (flagged, categories that fired)."""
    if not isinstance(moderation, dict) or not moderation:
        return False, []
    cats = moderation.get("categories") or {}
    fired = sorted(k for k, v in cats.items() if v) if isinstance(cats, dict) else []
    return bool(moderation.get("flagged")) or bool(fired), fired


def to_item(record: dict, source: str) -> dict | None:
    """Convert one dataset row to the corpus item shape the tracker reads.

    Returns None for rows that cannot hold a refusal sequence (too short, not English,
    or roles that do not alternate).
    """
    lang = str(record.get("language") or "").lower()
    if lang and lang not in ("english", "en"):
        return None
    conv = record.get("conversation") or []
    turns = []
    for n, msg in enumerate(conv):
        role = msg.get("role")
        if role not in ("user", "assistant"):
            return None
        turns.append({"i": n, "role": role, "text": str(msg.get("content") or "")})
    if len(turns) < MIN_TURNS or turns[0]["role"] != "user":
        return None
    if any(t["role"] == turns[n - 1]["role"] for n, t in enumerate(turns) if n):
        return None

    mods = record.get("openai_moderation") or []
    user_flags = [_flagged(m) for m, t in zip(mods, turns) if t["role"] == "user"]
    if source == "wildchat" and record.get("toxic"):
        user_flags.append((True, []))
    categories = sorted({c for _, cats in user_flags for c in cats})
    return {
        "id": str(record.get(ID_FIELDS[source]) or record.get("id") or ""),
        "turns": turns,
        "model": record.get("model"),
        "flagged": any(f for f, _ in user_flags),
        "categories": categories,
    }


# ------------------------------------------------------------------------ tracking

def track_row(item: dict, source: str) -> dict:
    """Run the rule tracker. The returned row carries no conversation text."""
    state = track_rules(item)
    s = state.summary()
    return {
        "source": source,
        "id": item["id"],
        "model": item.get("model"),
        "n_turns": len(item["turns"]),
        "flagged": item["flagged"],
        "categories": item["categories"],
        "n_refusals": s["n_refusals"],
        "n_attempts": s["n_attempts"],
        "undone": s["undone"],
        "refusal_turn": s["refusal_turn"],
        "reframe_turn": s["reframe_turn"],
        "comply_turn": s["comply_turn"],
        "kind": s["kind"],
        "frames": s["frames"],
        "re_request_kinds": [r.kind for r in state.re_requests],
    }


def scan(records: Iterable[dict], source: str, max_items: int | None = None) -> Iterator[dict]:
    seen = 0
    for rec in records:
        item = to_item(rec, source)
        if item is None:
            continue
        yield track_row(item, source)
        seen += 1
        if max_items and seen >= max_items:
            return


# ------------------------------------------------------------------------- report

def build_report(rows: list[dict]) -> dict:
    report: dict = {"sources": {}}
    for source in sorted({r["source"] for r in rows}):
        src = [r for r in rows if r["source"] == source]
        strata = {}
        for name, flag in (("unflagged", False), ("flagged", True)):
            rs = [r for r in src if r["flagged"] is flag]
            refused = [r for r in rs if r["n_refusals"]]
            attempted = [r for r in refused if r["n_attempts"]]
            kinds: dict[str, int] = {}
            for r in refused:
                for k in r["re_request_kinds"]:
                    kinds[k] = kinds.get(k, 0) + 1
            strata[name] = {
                "n_conversations": len(rs),
                "with_refusal": rate(len(refused), len(rs)),
                "refused_then_reframe_attempt": rate(len(attempted), len(refused)),
                "refused_then_undone": rate(sum(r["undone"] for r in refused), len(refused)),
                "undone_given_attempt": rate(sum(r["undone"] for r in attempted), len(attempted)),
                "re_request_kinds": dict(sorted(kinds.items())),
            }
        report["sources"][source] = strata
    check_no_pooled(report)
    return report


def render_markdown(report: dict) -> str:
    out = ["# E5 on public chat logs (rule tracker, offline)", "",
           "Rates are what the rule tracker reports. They are not validated: there is no "
           "gold label in these datasets. Label the review sample before citing them.", ""]
    for source, strata in report["sources"].items():
        out += [f"## {source}", "",
                "| Stratum | Conversations | With a refusal | Refusal then re-request attempt | "
                "Refusal undone | Undone, given an attempt |",
                "|---|---|---|---|---|---|"]
        for name, c in strata.items():
            out.append(f"| {name} | {c['n_conversations']} | {_fmt(c['with_refusal'])} | "
                       f"{_fmt(c['refused_then_reframe_attempt'])} | {_fmt(c['refused_then_undone'])} | "
                       f"{_fmt(c['undone_given_attempt'])} |")
        out.append("")
        for name, c in strata.items():
            out.append(f"Re-request kinds after a refusal ({name}): {c['re_request_kinds'] or 'none'}")
        out.append("")
    return "\n".join(out) + "\n"


def review_sample(rows: list[dict], per_cell: int = 25, seed: int = 19) -> list[dict]:
    """Stratified sample for hand labeling: tracker-undone, attempt-not-undone, and
    refusal-with-no-attempt, in each moderation stratum. Precision comes from the first
    cell; the other two give a look at what it misses."""
    rng = random.Random(seed)
    cells = {
        "undone": lambda r: r["undone"],
        "attempt_not_undone": lambda r: r["n_attempts"] and not r["undone"],
        "refusal_no_attempt": lambda r: r["n_refusals"] and not r["n_attempts"],
    }
    out = []
    for flag in (False, True):
        for cell, pred in cells.items():
            pool = [r for r in rows if r["flagged"] is flag and pred(r)]
            for r in rng.sample(pool, min(per_cell, len(pool))):
                out.append({"source": r["source"], "id": r["id"], "flagged": flag,
                            "tracker_cell": cell, "refusal_turn": r["refusal_turn"],
                            "reframe_turn": r["reframe_turn"], "comply_turn": r["comply_turn"],
                            "human_undone": "", "human_notes": ""})
    rng.shuffle(out)
    return out


# --------------------------------------------------------------------------- CLI

def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--source", choices=sorted(HF_NAMES))
    src = ap.add_mutually_exclusive_group()
    src.add_argument("--path", help="local files (glob), parquet or jsonl, under data/external/")
    src.add_argument("--hf", action="store_true", help="stream from Hugging Face (needs `datasets`)")
    src.add_argument("--rows", help="re-report saved tracker rows instead of scanning")
    ap.add_argument("--max", type=int, default=None, help="stop after this many usable conversations")
    ap.add_argument("--out", help="write tracker rows (no text) here")
    ap.add_argument("--sample-out", help="write a stratified review sample CSV here")
    ap.add_argument("--per-cell", type=int, default=25)
    ap.add_argument("--show", help="print one conversation by id, for hand review (local only)")
    args = ap.parse_args(argv)

    if args.rows:
        with open(args.rows, encoding="utf-8") as fh:
            rows = [json.loads(line) for line in fh if line.strip()]
    else:
        if not args.source or not (args.path or args.hf):
            ap.error("give --source and one of --path / --hf (or --rows)")
        records = _records_from_hf(args.source) if args.hf else _records_from_paths(args.path)
        if args.show:
            for rec in records:
                item = to_item(rec, args.source)
                if item and item["id"] == args.show:
                    print(f"# {item['id']} flagged={item['flagged']} {item['categories']}")
                    for t in item["turns"]:
                        print(f"\n[turn {t['i']}] {t['role'].upper()}:\n{t['text']}")
                    print("\n# tracker:", json.dumps(track_row(item, args.source)))
                    return 0
            print(f"id {args.show} not found", file=sys.stderr)
            return 1
        rows = []
        out = open(args.out, "w", encoding="utf-8") if args.out else None
        try:
            for n, row in enumerate(scan(records, args.source, args.max), 1):
                rows.append(row)
                if out:
                    out.write(json.dumps(row) + "\n")
                if n % 5000 == 0:
                    print(f"{n} conversations scanned", file=sys.stderr)
        finally:
            if out:
                out.close()

    if args.sample_out:
        sample = review_sample(rows, args.per_cell)
        Path(args.sample_out).parent.mkdir(parents=True, exist_ok=True)
        with open(args.sample_out, "w", newline="", encoding="utf-8") as fh:
            if sample:
                w = csv.DictWriter(fh, fieldnames=list(sample[0]))
                w.writeheader()
                w.writerows(sample)
        print(f"wrote {len(sample)} review rows to {args.sample_out}", file=sys.stderr)
    sys.stdout.write(render_markdown(build_report(rows)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
