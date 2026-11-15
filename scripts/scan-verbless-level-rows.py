#!/usr/bin/env python3
"""List "At Nth level:" summary rows that lost their verb in the upstream import.

A defective row is a body line of the shape

    At <level> level: <subject> <value>[ <unit>].

where the subject is a bare noun phrase followed directly by the value, as in
"At 10th level: The bonus +2." (print: "This bonus increases to +2.").

The value is a signed number, a dice expression, a fraction or a percentage.
It may carry a unit word, such as "feet", "rounds" or "points" (the first
version of this scan missed those rows).

A row is left out when a verb or a linking word already sits between the
subject and the value: "increases by 2", "increases to +3", "is 2d6",
"acts like summon monster +2", "becomes the Charisma mod + 2d6". The first
version of this scan matched "by" rows as defective.

Usage (from the corpus root, read-only, no edits):

    python3 scripts/scan-verbless-level-rows.py [--excluded] [--count] [PATH ...]

With no PATH the scan covers `entries/`. It prints `path:line`, one per row,
sorted. `--excluded` prints the rows that match the value shape but were left
out as grammatical, with the reason, to audit the word lists below.
`--count` prints the number of rows and files instead of the rows.
"""

import argparse
import re
import sys
from pathlib import Path

VALUE = r"[+\-−–]?\d[\d,]*(?:d\d+)?(?:/\d+)?%?"
UNIT = (
    r"(?:feet|foot|ft\.|miles?|rounds?|minutes?|hours?|days?|squares?|"
    r"(?:hit )?points?|damage|creatures?|weapons?|attacks?|waypoints?|"
    r"times|per (?:day|round|level))"
)
ROW = re.compile(
    r"^At [^:]{1,40} level: (?P<pre>.*?)\s*(?P<value>" + VALUE + r"(?:\s+" + UNIT + r")?)\.?$"
)

# A word before the value that links subject and value: the row has its verb.
LINKING = {"to", "by", "for", "from", "at", "than", "of", "+", "-", "plus", "minus"}
# A finite verb anywhere before the value: the row is a full sentence.
VERBS = {
    "is", "are", "was", "were", "be", "becomes", "become", "increases", "increase",
    "improves", "improve", "acts", "act", "gains", "grants", "grant", "penetrate",
    "retain", "persists", "persist", "take", "takes", "affect", "affects", "maintain",
    "maintains", "reduces", "reduce", "deals", "gets", "get", "rises", "changes",
    "change", "remains", "remain", "applies", "apply", "equals", "doubles", "extends",
    "lasts", "has", "have", "uses", "use", "used", "grow", "grows", "reaches", "heals",
}
PRONOUNS = {"he", "she", "you", "they", "it", "i", "we", "allies", "enemies"}


def exclusion(pre: str) -> str | None:
    """Return why the row already has its verb, or None when it is defective."""
    words = pre.split()
    if not words:
        return None
    last = words[-1].lower()
    if last in LINKING:
        return f"linking word '{last}' before the value"
    for w in words:
        if w.lower().strip("_*,") in VERBS:
            return f"verb '{w}'"
    # "The dimensional occultist can maintain 2 waypoints" is a sentence;
    # "The distance she can travel 30 feet" is a noun phrase with a relative
    # clause (a pronoun directly before "can", not at the start).
    low = [w.lower() for w in words]
    if "can" in low:
        i = low.index("can")
        if i == 0 or low[i - 1] not in PRONOUNS or i == 1:
            return "'can' in a main clause"
    return None


def scan(paths):
    for root in paths:
        files = [root] if root.is_file() else sorted(root.rglob("*.md"))
        for f in files:
            for n, line in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
                m = ROW.match(line)
                if m and m["pre"]:
                    yield f, n, exclusion(m["pre"]), line


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("paths", nargs="*", type=Path, default=[Path("entries")])
    ap.add_argument("--excluded", action="store_true", help="print left-out rows with the reason")
    ap.add_argument("--count", action="store_true", help="print the totals only")
    args = ap.parse_args()

    hits = [(f, n) for f, n, why, _ in scan(args.paths) if why is None]
    if args.excluded:
        for f, n, why, line in scan(args.paths):
            if why:
                print(f"{f}:{n}: {why}: {line}")
    elif args.count:
        print(f"{len(hits)} rows in {len({f for f, _ in hits})} files")
    else:
        for f, n in hits:
            print(f"{f}:{n}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
