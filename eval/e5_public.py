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
    python -m eval.e5_public --source wildchat --hf --review-ids eval/results/e5_wildchat_review.csv \
        --review-text data/external/e5_wildchat_review.md   # sampled conversations, local only

With --hf the script exits hard once its output is written: the streaming reader keeps
background threads open that otherwise stop Python from quitting.
"""

from __future__ import annotations

import argparse
import csv
import glob
import json
import os
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


def review_sample(rows: list[dict], per_cell: int = 25, seed: int = 19,
                  exclude: set[str] | None = None) -> list[dict]:
    """Stratified sample for hand labeling: tracker-undone, attempt-not-undone, and
    refusal-with-no-attempt, in each moderation stratum. Precision comes from the first
    cell; the other two give a look at what it misses. `exclude` drops ids already
    reviewed, so a fresh sample can test anything tuned on an earlier one."""
    rng = random.Random(seed)
    exclude = exclude or set()
    cells = {
        "undone": lambda r: r["undone"],
        "attempt_not_undone": lambda r: r["n_attempts"] and not r["undone"],
        "refusal_no_attempt": lambda r: r["n_refusals"] and not r["n_attempts"],
    }
    out = []
    for flag in (False, True):
        for cell, pred in cells.items():
            pool = [r for r in rows if r["flagged"] is flag and pred(r) and r["id"] not in exclude]
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
    ap.add_argument("--seed", type=int, default=19, help="review sample seed")
    ap.add_argument("--exclude", nargs="*", default=[],
                    help="review CSVs whose ids the new sample must not reuse")
    ap.add_argument("--show", help="print one conversation by id, for hand review (local only)")
    ap.add_argument("--review-ids", help="review CSV from --sample-out; with --review-text")
    ap.add_argument("--review-text", help="write those conversations as markdown here (keep it out of git)")
    ap.add_argument("--model-review", help="run the model tracker on the --review-ids conversations; "
                    "write rows here (API calls; unflagged conversations only)")
    ap.add_argument("--labels", help="human labels CSV to score --model-review rows against")
    ap.add_argument("--model-id", default=None)
    ap.add_argument("--prompt", default=None, help="refusal tracker prompt file (default v2)")
    ap.add_argument("--dry-run", action="store_true", help="with --model-review: count and show, call nothing")
    args = ap.parse_args(argv)
    code = _run(args, ap)
    if args.hf:  # streaming leaves non-daemon threads alive; do not hang at exit
        sys.stdout.flush()
        sys.stderr.flush()
        os._exit(code)
    return code


def write_review_text(records: Iterable[dict], source: str, review_rows: list[dict], path: str) -> int:
    """Write the sampled conversations, with the tracker's turn marks, as markdown."""
    wanted = {r["id"]: r for r in review_rows}
    found: dict[str, str] = {}
    for rec in records:
        item = to_item(rec, source)
        if item is None or item["id"] not in wanted or item["id"] in found:
            continue
        r = wanted[item["id"]]
        marks = {int(r[k]): k.replace("_turn", "") for k in ("refusal_turn", "reframe_turn", "comply_turn")
                 if str(r.get(k, "")).strip() not in ("", "None")}
        lines = [f"## {item['id']}", "",
                 f"Tracker cell: {r['tracker_cell']}. Flagged: {item['flagged']}. "
                 "Label in the CSV: human_undone = yes / no / unclear.", ""]
        for t in item["turns"]:
            tag = f" <- tracker: {marks[t['i']]}" if t["i"] in marks else ""
            lines.append(f"**[turn {t['i']}] {t['role'].upper()}{tag}**\n\n{t['text'].strip()}\n")
        found[item["id"]] = "\n".join(lines)
        if len(found) == len(wanted):
            break
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    order = [r["id"] for r in review_rows if r["id"] in found]
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("# E5 review sample (local only; do not commit)\n\n" + "\n---\n\n".join(found[i] for i in order))
    return len(found)


def model_review(records: Iterable[dict], source: str, ids: list[str], backend, dry_run: bool = False,
                 prompt=None) -> list[dict]:
    """Model tracker on the given conversations. Moderation-flagged conversations are
    skipped, never sent: real harmful text stays off the API (account-safety rule)."""
    from analyzer.analyzer import render_transcript
    from analyzer.refusal_state import track_model

    wanted, rows = set(ids), []
    for rec in records:
        item = to_item(rec, source)
        if item is None or item["id"] not in wanted:
            continue
        wanted.discard(item["id"])
        if item["flagged"]:
            rows.append({"id": item["id"], "status": "skipped_flagged"})
        elif dry_run:
            if not rows:
                print(render_transcript(item)[:3000], "\n...", file=sys.stderr)
            rows.append({"id": item["id"], "status": "dry_run"})
        else:
            res = track_model(item, backend, prompt)
            s = res.state.summary() if res.state else None
            rows.append({"id": item["id"], "status": res.status, "model": res.model,
                         "prompt_version": res.prompt_version, "errors": res.errors,
                         "undone": s["undone"] if s else None, "attempt": s["attempt"] if s else None,
                         "n_refusals": s["n_refusals"] if s else None,
                         "re_request_kinds": [r.kind for r in res.state.re_requests] if res.state else None})
            print(f"model: {item['id'][:10]} {res.status}", file=sys.stderr)
        if not wanted:
            break
    return rows


def score_against_labels(model_rows: list[dict], labels: list[dict]) -> dict:
    """Rule tracker vs model tracker on the same hand-labeled conversations.
    'unclear' labels are left out of both; nothing is pooled across trackers."""
    lab = {r["id"]: r for r in labels if r.get("human_undone") in ("yes", "no")}
    mod = {r["id"]: r for r in model_rows if r.get("status") == "ok"}

    def cell(pred):  # pred: id -> bool
        ids = [i for i in lab if i in pred]
        tp = sum(pred[i] and lab[i]["human_undone"] == "yes" for i in ids)
        fp = sum(pred[i] and lab[i]["human_undone"] == "no" for i in ids)
        fn = sum(not pred[i] and lab[i]["human_undone"] == "yes" for i in ids)
        return {"n": len(ids), "precision": rate(tp, tp + fp), "recall": rate(tp, tp + fn),
                "false_positives": fp}

    common = set(lab) & set(mod)
    report = {
        "rules": cell({i: lab[i]["tracker_cell"] == "undone" for i in common}),
        "model": cell({i: bool(mod[i]["undone"]) for i in common}),
        "model_statuses": dict(sorted({s: sum(r.get("status") == s for r in model_rows)
                                       for s in {r.get("status") for r in model_rows}}.items())),
    }
    check_no_pooled(report)
    return report


def _run(args: argparse.Namespace, ap: argparse.ArgumentParser) -> int:
    if args.model_review:
        if not (args.review_ids and args.source and (args.path or args.hf)):
            ap.error("--model-review needs --review-ids, --source and --path or --hf")
        with open(args.review_ids, newline="", encoding="utf-8") as fh:
            ids = [r["id"] for r in csv.DictReader(fh)]
        backend = None
        if not args.dry_run:
            from analyzer.analyzer import AnthropicBackend

            backend = AnthropicBackend(model=args.model_id)
        records = _records_from_hf(args.source) if args.hf else _records_from_paths(args.path)
        from analyzer.analyzer import load_prompt
        from analyzer.refusal_state import REFUSAL_PROMPT

        prompt = load_prompt(args.prompt or REFUSAL_PROMPT)
        print(f"prompt: {prompt.version}", file=sys.stderr)
        rows = model_review(records, args.source, ids, backend, args.dry_run, prompt)
        if args.dry_run:
            print(f"dry run: would send {sum(r['status'] == 'dry_run' for r in rows)} conversations; "
                  f"skipped flagged {sum(r['status'] == 'skipped_flagged' for r in rows)}")
            return 0
        Path(args.model_review).parent.mkdir(parents=True, exist_ok=True)
        with open(args.model_review, "w", encoding="utf-8") as fh:
            for r in rows:
                fh.write(json.dumps(r) + "\n")
        if args.labels:
            with open(args.labels, newline="", encoding="utf-8") as fh:
                rep = score_against_labels(rows, list(csv.DictReader(fh)))
            print(f"# Rule vs model tracker ({prompt.version}) on hand-labeled conversations\n")
            for t in ("rules", "model"):
                c = rep[t]
                print(f"- {t}: precision {_fmt(c['precision'])}; recall {_fmt(c['recall'])}; "
                      f"false positives {c['false_positives']} of {c['n']}")
            print(f"- model statuses: {rep['model_statuses']}")
        return 0

    if args.review_text:
        if not (args.review_ids and args.source and (args.path or args.hf)):
            ap.error("--review-text needs --review-ids, --source and --path or --hf")
        with open(args.review_ids, newline="", encoding="utf-8") as fh:
            review_rows = list(csv.DictReader(fh))
        records = _records_from_hf(args.source) if args.hf else _records_from_paths(args.path)
        n = write_review_text(records, args.source, review_rows, args.review_text)
        print(f"wrote {n} of {len(review_rows)} conversations to {args.review_text}", file=sys.stderr)
        return 0

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
        exclude: set[str] = set()
        for f in args.exclude:
            with open(f, newline="", encoding="utf-8") as fh:
                exclude |= {r["id"] for r in csv.DictReader(fh)}
        sample = review_sample(rows, args.per_cell, args.seed, exclude)
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
