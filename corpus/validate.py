"""Validate corpus/items.jsonl against corpus/SCHEMA.md.

Usage: python3 corpus/validate.py [path/to/items.jsonl]
Exits non-zero and prints every problem found.
"""
import json
import re
import sys
from collections import Counter
from pathlib import Path

CONSTRUCTS = ["FIX", "IDN", "LEAK", "RHRS", "ESC", "CONV"]
LABELS = {"present", "absent", "uncertain"}
TIERS = ["none", "resource", "friction", "review", "escalate"]
STRATA = {"hard_negative": "hn", "hard_positive": "hp", "clear_positive": "cp", "clear_negative": "cn"}
REQUIRED = ["id", "stratum", "persona", "turns", "gold", "discriminating_features", "trap_for", "notes"]
OPTIONAL = ["refusal_sequence", "pair_id"]
ID_RE = re.compile(r"^(hn|hp|cp|cn)-[a-z0-9]+-\d{2}$")


def check_item(item, errors):
    iid = item.get("id", "<no id>")

    def err(msg):
        errors.append(f"{iid}: {msg}")

    for key in REQUIRED:
        if key not in item:
            err(f"missing field '{key}'")
    for key in item:
        if key not in REQUIRED and key not in OPTIONAL:
            err(f"unknown field '{key}'")
    if errors and errors[-1].startswith(f"{iid}: missing"):
        return

    if not ID_RE.match(iid):
        err("id must match {hn|hp|cp|cn}-{persona}-{nn}")
    if item["stratum"] not in STRATA:
        err(f"unknown stratum '{item['stratum']}'")
    elif not iid.startswith(STRATA[item["stratum"]] + "-"):
        err(f"id prefix does not match stratum '{item['stratum']}'")

    turns = item["turns"]
    if not turns:
        err("no turns")
    for n, t in enumerate(turns):
        if t.get("i") != n:
            err(f"turn {n}: 'i' is {t.get('i')}, expected {n}")
        if t.get("role") not in ("user", "assistant"):
            err(f"turn {n}: bad role {t.get('role')!r}")
        if not isinstance(t.get("text"), str) or not t["text"].strip():
            err(f"turn {n}: empty text")
    n_turns = len(turns)

    gold = item["gold"]
    for c in CONSTRUCTS:
        g = gold.get(c)
        if not isinstance(g, dict):
            err(f"gold.{c} missing")
            continue
        if g.get("label") not in LABELS:
            err(f"gold.{c}.label {g.get('label')!r} not in {sorted(LABELS)}")
        ev = g.get("evidence", None)
        if not isinstance(ev, list) or any(not isinstance(i, int) or not 0 <= i < n_turns for i in ev):
            err(f"gold.{c}.evidence must be a list of turn indices in [0, {n_turns})")
        elif g.get("label") == "absent" and ev:
            err(f"gold.{c} is absent but cites evidence")
        elif g.get("label") == "present" and not ev:
            err(f"gold.{c} is present but cites no evidence")
    if gold.get("tier") not in TIERS:
        err(f"gold.tier {gold.get('tier')!r} not in {TIERS}")
    extra = set(gold) - set(CONSTRUCTS) - {"tier"}
    if extra:
        err(f"unknown gold keys {sorted(extra)}")

    if item["stratum"] == "hard_negative":
        if any(gold[c]["label"] == "present" for c in CONSTRUCTS if c in gold):
            err("hard negative has a construct labeled present")
        if gold.get("tier") in ("review", "escalate"):
            err("hard negative has tier review/escalate")

    df = item["discriminating_features"]
    if not isinstance(df, list) or len(df) < 2 or not all(isinstance(s, str) and s for s in df):
        err("discriminating_features must list at least two non-empty strings")

    rs = item.get("refusal_sequence")
    if rs is not None:
        keys = ["request_turn", "refusal_turn", "reframe_turn", "comply_turn"]
        idx = [rs.get(k) for k in keys]
        if not isinstance(rs.get("present"), bool) or not isinstance(rs.get("benign"), bool):
            err("refusal_sequence.present and .benign must be booleans")
        if rs.get("present"):
            if not all(isinstance(i, int) and 0 <= i < n_turns for i in idx):
                err("refusal_sequence turn indices missing or out of range")
            elif idx != sorted(idx) or len(set(idx)) != 4:
                err("refusal_sequence turns must be strictly increasing")
            else:
                want = ["user", "assistant", "user", "assistant"]
                got = [turns[i]["role"] for i in idx]
                if got != want:
                    err(f"refusal_sequence roles are {got}, expected {want}")


def main(path):
    errors, items = [], []
    for lineno, line in enumerate(Path(path).read_text().splitlines(), 1):
        if not line.strip():
            continue
        try:
            items.append(json.loads(line))
        except json.JSONDecodeError as e:
            errors.append(f"line {lineno}: invalid JSON ({e})")
    for item in items:
        check_item(item, errors)
    dupes = [i for i, n in Counter(it.get("id") for it in items).items() if n > 1]
    for d in dupes:
        errors.append(f"{d}: duplicate id")

    strata = Counter(it.get("stratum") for it in items)
    tiers = Counter((it.get("stratum"), it.get("gold", {}).get("tier")) for it in items)
    print(f"{len(items)} items: " + ", ".join(f"{s}={n}" for s, n in sorted(strata.items())))
    for (s, t), n in sorted(tiers.items()):
        print(f"  {s} tier={t}: {n}")
    if errors:
        print(f"\n{len(errors)} problem(s):")
        for e in errors:
            print("  " + e)
        return 1
    print("OK")
    return 0


if __name__ == "__main__":
    default = Path(__file__).with_name("items.jsonl")
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else default))
