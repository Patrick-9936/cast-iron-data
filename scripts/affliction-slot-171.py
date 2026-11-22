#!/usr/bin/env python3
"""Survey and fix the affliction type tags and the item `slot` values (issue #171).

A filter menu or a search facet group shows these two fields, so each has a closed vocabulary that
`cargo xtask corpus-check` validates (phynics/cast-iron, `crates/corpus/src/check.rs`:
`AFFLICTION_TYPES`, `ITEM_BODY_SLOTS`, `ITEM_QUALITY_SLOTS`, `is_item_slot`). This script keeps the
corpus on those lists:

  * `scripts/affliction-slot-vocabulary-171.tsv` holds each value with its basis and a print
    citation (book title and page). The lists in `check.rs` must equal it. A `slot` value is one
    row of the list, or two distinct body slots joined by ` or ` (the `{slot} or {slot}` row);
  * `scripts/affliction-slot-review-171.tsv` holds one row per item whose slot was outside the
    list: the entry, the field, the action, the old value, the new value and the reason with the
    print citation. The actions are `set` (replace the value), `remove` (take the field out: the
    text is no slot, and the body prints it) and `keep` (leave the value; an owner decision or a
    body edit is open). A row never changes a body, an `id` or a file path.

Affliction types. The type of an affliction is a tag: exactly one of the six words. Each
affliction without one gets the lower-case first word of its printed `Type:` line (the body line
stays as printed). A first word outside the six goes to the review file and the entry stays
untagged. The survey prints the count per type and the entries left over.

Item slots. `--write` applies each open `set` and `remove` row. The old value must be the current
value, so a rerun finds nothing to do. Two guards apply before a row writes:
  * when the new value is the start of the old one (`eye; Price ...` to `eye`, `none (see below)`
    to `none`), the rest of the old value must be printed in the body, so no text is lost;
  * when the body has a stat block `Slot:` row, the drift check compares it with the field, so the
    new value must equal that row. Otherwise the row cannot be a `set` or `remove`: the body wins.

Survey (default): prints the tag counts, the untagged afflictions, the count per `slot` value,
every value outside the vocabulary and its review row. Exit status 1 when an affliction has no
tag and no review row, a `slot` value is outside the vocabulary without a review row, or a `set`
or `remove` row is still open.

Run from the corpus root, then format and check the corpus with the cast-iron tool:

    python3 -I scripts/affliction-slot-171.py [--write]
    cargo xtask corpus-fmt --check <dir>
    cargo xtask corpus-check <dir>
"""

from __future__ import annotations

import argparse
import collections
import csv
import re
import sys
import tomllib
from pathlib import Path

FRONT = re.compile(r"\A\+\+\+\n(.*?)\n\+\+\+\n", re.S)
TYPE_LINE = re.compile(r"^(?:\*\*)?Type:?(?:\*\*)?:?\s*(\w+)", re.I | re.M)
STATBLOCK_SLOT = re.compile(r"^Slot:\s*(.*)$", re.M)
VOCABULARY = "scripts/affliction-slot-vocabulary-171.tsv"
REVIEW = "scripts/affliction-slot-review-171.tsv"


def read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t", quoting=csv.QUOTE_NONE))


def entries(root: Path):
    for path in sorted((root / "entries").rglob("*.md")):
        text = path.read_text()
        match = FRONT.match(text)
        if match:
            yield path, text, tomllib.loads(match.group(1)), match.end()


def normalize(text: str) -> str:
    return " ".join(text.replace("**", "").replace("\\", " ").split()).lower().rstrip(".;")


class Vocabulary:
    def __init__(self, rows: list[dict[str, str]]):
        self.afflictions = {r["value"] for r in rows if r["field"] == "affliction_type"}
        self.slots = {r["value"] for r in rows if r["field"] == "slot"}
        self.qualities = {r["value"] for r in rows if r["field"] == "slot" and r["basis"] == "enhancement"}
        self.pair_row = any(r["value"] == "{slot} or {slot}" for r in rows if r["field"] == "slot")
        self.slots.discard("{slot} or {slot}")

    def has_slot(self, value: str) -> bool:
        if value in self.slots:
            return True
        parts = value.split(" or ")
        return (
            self.pair_row
            and len(parts) == 2
            and parts[0] != parts[1]
            and all(p in self.slots and p not in self.qualities for p in parts)
        )


def afflictions(root: Path, vocabulary: Vocabulary):
    """Yield (path, text, data, body_start, type_word) for every affliction."""
    for path, text, data, end in entries(root):
        if data.get("kind") != "affliction":
            continue
        found = TYPE_LINE.search(text[end:])
        yield path, text, data, end, (found.group(1).lower() if found else None)


def survey_afflictions(root: Path, vocabulary: Vocabulary, review: list[dict[str, str]]) -> int:
    counts: collections.Counter[str] = collections.Counter()
    untagged: list[tuple[str, str | None]] = []
    total = 0
    reviewed = {row["entry_id"] for row in review if row["field"] == "affliction_type"}
    bad = 0
    for _path, _text, data, _end, word in afflictions(root, vocabulary):
        total += 1
        types = [tag for tag in data.get("tags", []) if tag in vocabulary.afflictions]
        counts[",".join(types) or "(none)"] += 1
        if not types:
            untagged.append((data["id"], word))
    print(f"{total} afflictions")
    for value, count in sorted(counts.items(), key=lambda item: (-item[1], item[0])):
        print(f"  {count:5}  {value}")
    for entry_id, word in untagged:
        if word in vocabulary.afflictions:
            continue
        mark = "review row" if entry_id in reviewed else "NO REVIEW ROW"
        bad += entry_id not in reviewed
        print(f"  {entry_id}  Type line starts with {word!r}  ({mark})")
    taggable = sum(1 for _id, word in untagged if word in vocabulary.afflictions)
    print(f"{taggable} untagged afflictions the Type line names; {len(untagged) - taggable} need a review row")
    return 1 if untagged and (taggable or bad) else 0


def tag_afflictions(root: Path, vocabulary: Vocabulary) -> None:
    changed = 0
    for path, text, data, end, word in afflictions(root, vocabulary):
        if any(tag in vocabulary.afflictions for tag in data.get("tags", [])):
            continue
        if word not in vocabulary.afflictions:
            continue
        head, body = text[:end], text[end:]
        if re.search(r"^tags = ", head, re.M):
            sys.exit(f"{data['id']}: has tags without an affliction type; edit it by hand")
        # The writer's order: aon, source_ids, section, parent, tags, race_group, provenance.
        line = f'tags = ["{word}"]\n'
        head, count = re.subn(r"^(race_group = |provenance = )", line + r"\1", head, count=1, flags=re.M)
        if count != 1:
            sys.exit(f"{data['id']}: no place for the tags line")
        path.write_text(head + body)
        changed += 1
    print(f"{changed} afflictions tagged")


def survey_slots(root: Path, vocabulary: Vocabulary, review: list[dict[str, str]]) -> int:
    counts: collections.Counter[str] = collections.Counter()
    outside: list[tuple[str, str]] = []
    for _path, _text, data, _end in entries(root):
        if data.get("kind") != "item":
            continue
        slot = data.get("fields", {}).get("slot")
        if slot is None:
            counts["(no slot)"] += 1
            continue
        counts[slot] += 1
        if not vocabulary.has_slot(slot):
            outside.append((data["id"], slot))
    for value, count in sorted(counts.items(), key=lambda item: (-item[1], item[0])):
        mark = "" if value == "(no slot)" or vocabulary.has_slot(value) else "   <- outside"
        print(f"  {count:5}  {value}{mark}")
    unused = sorted(vocabulary.slots - set(counts))
    if unused:
        print("vocabulary values no item uses:", ", ".join(unused))
    by_id = {(row["entry_id"], row["field"]): row for row in review}
    status = collections.Counter()
    failing = 0
    for entry_id, slot in outside:
        row = by_id.get((entry_id, "slot"))
        if row is None:
            status["NO REVIEW ROW"] += 1
            failing += 1
            print(f"  {entry_id}  slot = {slot!r}  (NO REVIEW ROW)")
        else:
            status[row["action"]] += 1
            failing += row["action"] in ("set", "remove")
    print(f"{len(outside)} values outside the vocabulary:", dict(status) or "none")
    return 1 if failing else 0


def apply_slots(root: Path, review: list[dict[str, str]]) -> None:
    rows = {(row["entry_id"], row["field"]): row for row in review if row["field"] == "slot"}
    changed = 0
    for path, text, data, end in entries(root):
        row = rows.get((data["id"], "slot"))
        if row is None or row["action"] not in ("set", "remove"):
            continue
        current = data.get("fields", {}).get("slot")
        if current != row["old"]:
            continue  # applied already
        new = row["new"] if row["action"] == "set" else None
        head, body = text[:end], text[end:]
        rest = row["old"][len(new):] if new is not None and row["old"].startswith(new) else None
        if rest is not None and normalize(rest.strip(" ;,")) not in normalize(body):
            sys.exit(f"{row['entry_id']}: the text {rest!r} that leaves the slot is not printed in the body")
        printed = STATBLOCK_SLOT.search(body)
        if printed and (new is None or normalize(printed.group(1)) != normalize(new)):
            sys.exit(f"{row['entry_id']}: the stat block row `Slot: {printed.group(1)}` would disagree; the body wins, make the row `keep`")
        if new is None:
            head, count = re.subn(r'^slot = ".*"\n', "", head, count=1, flags=re.M)
        else:
            head, count = re.subn(r'^slot = ".*"\n', f'slot = "{new}"\n', head, count=1, flags=re.M)
        if count != 1:
            sys.exit(f"{row['entry_id']}: the slot line was not found")
        path.write_text(head + body)
        changed += 1
        print(f"{row['entry_id']}: slot {row['old']!r} -> {new!r}")
    print(f"{changed} items changed")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--write", action="store_true", help="tag the afflictions and apply the open review rows")
    args = parser.parse_args()
    root = Path(".")
    vocabulary = Vocabulary(read_tsv(root / VOCABULARY))
    review = read_tsv(root / REVIEW)
    for row in review:
        if row["action"] not in ("set", "remove", "keep"):
            sys.exit(f"{row['entry_id']}: unknown action {row['action']!r}")
        if row["action"] == "set" and not vocabulary.has_slot(row["new"]):
            sys.exit(f"{row['entry_id']}: the new value {row['new']!r} is outside the vocabulary")
    if args.write:
        tag_afflictions(root, vocabulary)
        apply_slots(root, review)
    print("-- affliction types")
    status = survey_afflictions(root, vocabulary, review)
    print("-- item slots")
    return max(status, survey_slots(root, vocabulary, review))


if __name__ == "__main__":
    sys.exit(main())
