#!/usr/bin/env python3
"""Survey the `Flavor` rows of the corpus for editorial notes that the import wrote (phynics/cast-iron-data#158).

A `Flavor` row holds printed text: the intro sentence of a power. The earlier import also wrote
notes there that say where the power's text came from ("Text from the barbarian class."). The power
layout shows `Flavor` without a label, so such a note reads as printed text.

Usage
-----
    scripts/survey-flavor-notes.py [CORPUS]            counts by pattern and entry kind, then the rows
    scripts/survey-flavor-notes.py [CORPUS] --check    exit 1 when a class-option entry still holds a placeholder note

CORPUS defaults to the repository that holds this script.

Patterns (the first one that matches names the row):
    placeholder      "Text from ...", "Relevant text from ...", "From the Aquatic domain": the import's
                     stand-in for text that it copied from a class feature, an archetype, a domain
                     or a monster entry. Print has no
                     such sentence. Remove the row, or replace it with the flavor that print shows at
                     the power's own place.
    cross-reference  "This is the same as ...", "This ability functions as ...": print has a
                     cross-reference at that place ("As per the battle mystery revelation of the
                     same name."), and the note paraphrases it. Keep it only when it is the printed
                     wording; otherwise set the printed wording.

A pattern list only finds candidates. Read the rest of the Flavor rows too (`--all` lists them): a
note that no pattern names is still an editorial note.

`--check` fails only for `placeholder` in `class_option` entries; the other kinds are reported (the
archetype features, rule entries and classes keep their notes until a later change).

The survey reads the entry files directly: a block is one paragraph, so a note that the corpus
formatter wrapped over several lines is one row.
"""

from __future__ import annotations

import argparse
import re
import sys
from collections import Counter
from pathlib import Path

PATTERNS = (
    ("placeholder", re.compile(r"^(?:(?:relevant )?text from\b|from the [\w' -]+ domain$)", re.I)),
    ("cross-reference", re.compile(r"^(?:this is the same as|this ability functions as)\b", re.I)),
)
FRONT = re.compile(r"\A\+\+\+\n(.*?)\n\+\+\+\n", re.S)


def flavor_rows(corpus: Path):
    """(kind, entry id, flavor text) of every Flavor row, in path order."""
    for path in sorted((corpus / "entries").rglob("*.md")):
        text = path.read_text()
        front = FRONT.match(text)
        if not front:
            continue
        kind = re.search(r'^kind = "([^"]+)"', front.group(1), re.M)
        entry_id = re.search(r'^id = "([^"]+)"', front.group(1), re.M)
        for block in re.split(r"\n\s*\n", text[front.end():]):
            if block.startswith("**Flavor:**"):
                flat = " ".join(line.strip() for line in block.split("\n"))
                yield kind.group(1), entry_id.group(1), flat[len("**Flavor:**"):].strip()


def classify(text: str) -> str | None:
    for name, pattern in PATTERNS:
        if pattern.search(text):
            return name
    return None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("corpus", nargs="?", default=str(Path(__file__).resolve().parent.parent))
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--all", action="store_true", help="list every Flavor row of class_option entries too")
    args = ap.parse_args()

    rows = list(flavor_rows(Path(args.corpus)))
    kinds = Counter(kind for kind, _, _ in rows)
    hits = [(kind, entry_id, text, classify(text)) for kind, entry_id, text in rows]
    counts = Counter((name, kind) for kind, _, _, name in hits if name)
    print(f"Flavor rows: {len(rows)} " + ", ".join(f"{k} {v}" for k, v in sorted(kinds.items())))
    for name, _ in PATTERNS:
        total = sum(v for (n, _), v in counts.items() if n == name)
        by_kind = ", ".join(f"{k} {v}" for (n, k), v in sorted(counts.items()) if n == name)
        print(f"  {name}: {total}" + (f" ({by_kind})" if by_kind else ""))
    failing = [(entry_id, text) for kind, entry_id, text, name in hits
               if name == "placeholder" and kind == "class_option"]
    for kind, entry_id, text, name in hits:
        if name and (kind == "class_option" or args.all):
            print(f"{name}\t{kind}\t{entry_id}\t{text}")
        elif args.all and kind == "class_option":
            print(f"-\t{kind}\t{entry_id}\t{text}")
    if args.check and failing:
        print(f"{len(failing)} class-option placeholder note(s) remain", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
