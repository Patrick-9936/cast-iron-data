#!/usr/bin/env python3
"""List spell entries whose `levels` equal the `levels` of their `variant` target.

A numbered spell series (Summon Nature's Ally II-IX, Summon Monster II-IX) was imported with
the level-1 class list of its base spell on every member (phynics/cast-iron#402). A spell that
carries a `variant` relation and the same `levels` list as its target is a suspect: the list may
be copied, or the variant may legitimately share its base's level.

The scan also reports, for each suspect, the other typed spell fields that equal the target's
(school, subschools, descriptors, components, range, duration, saving throw, spell resistance,
casting time). Those are expected to match in a series, so they only help to see whether the
import copied fields wholesale.

Usage (from the corpus root, read-only, no edits):

    python3 scripts/scan-variant-levels.py [--count] [--fields] [ENTRIES_DIR]

With no argument the scan covers `entries/`. It prints one row per suspect, sorted by id:
`id`, the shared levels, and the target. `--count` prints only the number of rows.
`--fields` adds the spell fields that match the target. An entry or target that is not a
spell, or has no `levels`, is skipped. A suspect that the corpus has already fixed does not
show again, so the scan is rerunnable.
"""

import argparse
import sys
import tomllib
from pathlib import Path

FIELDS = (
    "school", "subschools", "descriptors", "casting_time", "components", "range",
    "duration", "saving_throw", "spell_resistance",
)


def front_matter(path: Path) -> dict | None:
    """Return the TOML front matter of an entry, or None when the file has none."""
    text = path.read_text(encoding="utf-8")
    if not text.startswith("+++\n"):
        return None
    end = text.find("\n+++\n", 4)
    if end < 0:
        return None
    return tomllib.loads(text[4:end])


def load_spells(root: Path) -> dict[str, dict]:
    spells = {}
    for path in sorted(root.rglob("*.md")):
        head = front_matter(path)
        if head is None or head.get("kind") != "spell":
            continue
        spells[head["id"]] = head
    return spells


def level_key(levels: list[dict]) -> tuple:
    return tuple(sorted((row["class"], row["level"]) for row in levels))


def describe(levels: list[dict]) -> str:
    by_level: dict[int, list[str]] = {}
    for row in levels:
        by_level.setdefault(row["level"], []).append(row["class"])
    return "; ".join(f"{lvl}: {', '.join(sorted(c))}" for lvl, c in sorted(by_level.items()))


def scan(spells: dict[str, dict]):
    for sid in sorted(spells):
        head = spells[sid]
        fields = head.get("fields", {})
        levels = fields.get("levels")
        if not levels:
            continue
        for rel in head.get("relations", []):
            if rel.get("kind") != "variant":
                continue
            target = spells.get(rel["target"])
            if target is None:
                continue
            tfields = target.get("fields", {})
            tlevels = tfields.get("levels")
            if tlevels and level_key(levels) == level_key(tlevels):
                same = [f for f in FIELDS if fields.get(f) == tfields.get(f) and fields.get(f)]
                yield sid, levels, rel["target"], same


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("root", nargs="?", default="entries")
    ap.add_argument("--count", action="store_true", help="print the number of rows only")
    ap.add_argument("--fields", action="store_true", help="add the fields that match the target")
    args = ap.parse_args()

    rows = list(scan(load_spells(Path(args.root))))
    if args.count:
        print(len(rows))
        return 0
    print(f"{'id':44} {'target':44} levels" + ("  | same fields" if args.fields else ""))
    for sid, levels, target, same in rows:
        line = f"{sid:44} {target:44} {describe(levels)}"
        if args.fields:
            line += "  | " + ", ".join(same)
        print(line)
    print(f"{len(rows)} spell(s) share their variant target's levels", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
