"""E14: count named prohibited behaviours per harm area per provider.

Reads eval/e14/policy_items.csv (one row per prohibited-use item, hand-coded to a
harm area) and prints a markdown table. Offline, no API.

Item counts are only comparable within a document: OpenAI writes short noun phrases,
Anthropic writes verb clauses, so a count says how finely a provider splits an area,
not how seriously it takes it.
"""
import csv
import sys
from collections import Counter
from pathlib import Path

AREAS = ["violence_to_persons", "extremism_terrorism", "weapons", "child_safety", "self_harm"]
PROVIDERS = ["openai", "anthropic", "meta"]


def main(path: Path) -> None:
    rows = list(csv.DictReader(path.open()))
    c = Counter((r["provider"], r["harm_area"]) for r in rows)
    print("| Harm area | " + " | ".join(PROVIDERS) + " |")
    print("|---|" + "---|" * len(PROVIDERS))
    for a in AREAS:
        print(f"| {a} | " + " | ".join(str(c[(p, a)]) for p in PROVIDERS) + " |")
    print("\nWeapons items per violence-to-persons item: " + ", ".join(
        f"{p} {c[(p, 'weapons')]}:{c[(p, 'violence_to_persons')]}" for p in PROVIDERS))


if __name__ == "__main__":
    main(Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).with_name("policy_items.csv"))
