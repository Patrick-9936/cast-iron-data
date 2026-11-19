#!/usr/bin/env python3
"""Find feats whose `prerequisite_feats` list and `**Prerequisites:**` line disagree.

A feat states its prerequisites twice: the body line, where a named feat is a
link to `ref/feat/<slug>`, and the `prerequisite_feats` list in the front
matter. The two must name the same feats. The scan reports two kinds of drift:

    unlinked  an id in `prerequisite_feats` that the body line does not link
              (the text lost a printed prerequisite, or the list gained a feat
              that print does not require)
    unlisted  a feat the body line links that `prerequisite_feats` lacks
              (the list lost a printed prerequisite)

A link is read from the first `**Prerequisites:**` line of the body. These are
not drift and the scan skips them: a link with an anchor (a footnote), the
entry's own id, and a feat that the entry already states as a `prerequisite`
relation (the `or` alternatives). `KNOWN` lists the rows that look like drift
but are correct, each with the reason.

Usage (from the corpus root, read-only, no edits):

    python3 scripts/scan-feat-prerequisites.py [--count]

It prints one line per row, sorted, and exits 1 when it finds a row that
`KNOWN` does not excuse. `--count` prints only the number of rows.
"""

import argparse
import re
import sys
import tomllib
from pathlib import Path

# (entry id, kind of drift, feat id): why the row is correct.
KNOWN = {
    ("ref/feat/center-of-power", "unlisted", "ref/feat/leadership"): "prerequisite is a Leadership score, not the feat",
    ("ref/feat/child-of-two-worlds", "unlisted", "ref/feat/racial-heritage"): "the prerequisites field holds the flavor text, which names Racial Heritage",
    ("ref/feat/titan-strike", "unlisted", "ref/feat/improved-unarmed-strike"): "the prerequisite is the mythic version of the feat",
}

PREREQ = re.compile(r"\*\*Prerequisites?:\*\*(.*?)(?:\\\n|\n\n)", re.S)
LINK = re.compile(r"\]\((ref/feat/[^)\s#]+)\)")


def read(path):
    head, _, body = path.read_text(encoding="utf-8").partition("\n+++\n")
    return tomllib.loads(head[4:]), body


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--count", action="store_true")
    ap.add_argument("root", nargs="?", default=".")
    args = ap.parse_args()
    root = Path(args.root)
    rows = []
    for path in sorted((root / "entries" / "feat").rglob("*.md")):
        data, body = read(path)
        m = PREREQ.search(body)
        if not m:
            continue
        entry = data["id"]
        linked = []
        for target in LINK.findall(m.group(1)):
            if target != entry and target not in linked:
                linked.append(target)
        stored = data.get("fields", {}).get("prerequisite_feats", [])
        stated = {
            r["target"] for r in data.get("relations", []) if r["kind"] == "prerequisite"
        }
        for target in stored:
            if target not in linked:
                rows.append((entry, "unlinked", target))
        for target in linked:
            if target not in stored and target not in stated:
                rows.append((entry, "unlisted", target))
    bad = [r for r in rows if r not in KNOWN]
    if args.count:
        print(len(bad))
    else:
        for entry, kind, target in bad:
            print(f"{entry}: {kind} {target}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
