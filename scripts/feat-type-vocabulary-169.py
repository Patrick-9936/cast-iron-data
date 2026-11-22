#!/usr/bin/env python3
"""Survey and fix the closed vocabularies of `feat_types` and creature `size` (issue #169).

A filter menu or a search facet group shows the values of a field, so the field has a closed
vocabulary that `cargo xtask corpus-check` validates (phynics/cast-iron, `crates/corpus/src/check.rs`,
`FEAT_TYPES` and `SIZE_CATEGORIES`). This script keeps the corpus on that list:

  * the feat types are the rows of `scripts/feat-type-vocabulary-169.tsv`: each value with the
    print basis and a citation (book title and page). The list in `check.rs` must equal it;
  * the sizes are the nine Pathfinder size categories. The compiler lower-cases `size`, so the
    survey compares without case; the corpus keeps the case of the printed stat block;
  * a value outside the vocabulary is a row of `scripts/feat-type-review-169.tsv`: the entry, the
    field, the old value, the new value (empty: the field is removed) and the reason with the
    print citation. A feat that print gives no type tag stays untyped: the compiler shows it as
    `General` in the facet, and the corpus does not invent the label.

Survey (default): prints the count per feat type, the untyped feats, every value outside the
vocabulary, and the review rows that are still open. Exit status 1 when a value is outside the
vocabulary.

`--write` applies each open review row: the old value must be the current value, so a rerun
finds nothing to do. It removes the `feat_types` or `size` line of the front matter, and for
`size` the `Size:` line of the stat block with the same value. It never changes an `id` or
moves a file. Then format and check the corpus with the cast-iron tool:

    cargo xtask corpus-fmt --check <dir>
    cargo xtask corpus-check <dir>

Run from the corpus root:

    python3 -I scripts/feat-type-vocabulary-169.py [--write]
"""

from __future__ import annotations

import argparse
import collections
import csv
import re
import sys
import tomllib
from pathlib import Path

SIZES = {
    "fine",
    "diminutive",
    "tiny",
    "small",
    "medium",
    "large",
    "huge",
    "gargantuan",
    "colossal",
}
FRONT = re.compile(r"\A\+\+\+\n(.*?)\n\+\+\+\n", re.S)


def read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t", quoting=csv.QUOTE_NONE))


def entries(root: Path):
    for path in sorted((root / "entries").rglob("*.md")):
        text = path.read_text()
        match = FRONT.match(text)
        if match:
            yield path, text, tomllib.loads(match.group(1))


def survey(root: Path, vocabulary: set[str], review: list[dict[str, str]]) -> int:
    counts: collections.Counter[str] = collections.Counter()
    untyped = feats = 0
    outside: list[tuple[str, str, str]] = []
    for _path, _text, data in entries(root):
        fields = data.get("fields", {})
        if data.get("kind") == "feat":
            feats += 1
            types = fields.get("feat_types", [])
            untyped += not types
            for value in types:
                counts[value] += 1
                if value not in vocabulary:
                    outside.append((data["id"], "feat_types", value))
        size = fields.get("size")
        if size is not None and size.strip().lower() not in SIZES:
            outside.append((data["id"], "size", size))
    print(f"{feats} feats, {untyped} untyped (the facet shows them as General)")
    for value, count in sorted(counts.items(), key=lambda item: (-item[1], item[0])):
        print(f"  {count:5}  {value}{'' if value in vocabulary else '   <- outside'}")
    unused = sorted(vocabulary - set(counts))
    if unused:
        print("vocabulary values no feat uses:", ", ".join(unused))
    print(f"{len(outside)} values outside the vocabulary")
    open_ids = {(row["entry_id"], row["field"]) for row in review}
    for entry_id, field, value in outside:
        mark = "review row" if (entry_id, field) in open_ids else "NO REVIEW ROW"
        print(f"  {entry_id}  {field} = {value!r}  ({mark})")
    return 1 if outside else 0


def apply(root: Path, review: list[dict[str, str]]) -> int:
    by_id = {row["entry_id"]: row for row in review}
    changed = 0
    for path, text, data in entries(root):
        row = by_id.get(data["id"])
        if row is None:
            continue
        field = row["field"]
        current = data.get("fields", {}).get(field)
        old = row["old"]
        if row["new"]:
            sys.exit(f"{row['entry_id']}: only removal rows are supported")
        if field == "feat_types":
            if current != [old]:
                continue
            pattern = re.compile(r"^feat_types = \[.*\]\n", re.M)
        elif field == "size":
            if current != old:
                continue
            pattern = re.compile(r'^size = ".*"\n', re.M)
        else:
            sys.exit(f"{row['entry_id']}: unknown field {field}")
        front = FRONT.match(text)
        head, body = text[: front.end()], text[front.end() :]
        head, count = pattern.subn("", head, count=1)
        if count != 1:
            sys.exit(f"{row['entry_id']}: the {field} line was not found")
        if field == "size":
            body = re.sub(rf"^Size: {re.escape(old)}\n", "", body, count=1, flags=re.M)
        path.write_text(head + body)
        changed += 1
        print(f"{row['entry_id']}: removed {field} = {old!r}")
    print(f"{changed} entries changed")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--write", action="store_true", help="apply the review rows")
    args = parser.parse_args()
    root = Path(".")
    vocabulary = {row["value"] for row in read_tsv(root / "scripts/feat-type-vocabulary-169.tsv")}
    review = read_tsv(root / "scripts/feat-type-review-169.tsv")
    if args.write:
        apply(root, review)
    return survey(root, vocabulary, review)


if __name__ == "__main__":
    sys.exit(main())
