#!/usr/bin/env python3
"""Survey school-like class options for rules that a later book added without attribution (phynics/cast-iron-data#163).

A class option such as a school, domain, bloodline, mystery, patron, spirit, order, inquisition,
discipline, implement school, blessing or aspect belongs to the book that prints it. The earlier
import also merged text from later books into some entries ("a transmuter may learn an annointing
instead of gaining a wizard bonus feat", an *Arcane Anthology* rule) with no attribution. The
corpus style for another book's addition is an extension section: a heading, a `**Sources:** Book
pg N` line, then the rule as printed (`### Enhancement School` in `ref/arcaneschool/transmutation`).

Usage
-----
    scripts/survey-later-book-rules.py [CORPUS]            list the candidates (read-only)
    scripts/survey-later-book-rules.py [CORPUS] --counts   only the counts by group and signal
    scripts/survey-later-book-rules.py [CORPUS] --check    exit 1 for a candidate that scripts/later-book-rules-reviewed.tsv does not list

CORPUS defaults to the repository that holds this script.

Entries covered: the class-option `group` values in GROUPS below.

Signals (a candidate is a block or a link that has at least one; unattributed blocks only)
    styled         a styled paragraph (`::: paragraph ...`) after the first power of the entry: a
                   resolution or the import put prose there that no power row holds
    selection      a paragraph, `Special`, `Info` or `Details` row, or styled paragraph that says a
                   character may take or learn another class's feature type "instead of" or "in
                   place of" something (annointing, discovery, hex, rage power, arcana, exploit,
                   trick, talent, archetype)
    later-link     a link to an entry (a class option, a class ability, a spell, a creature, a
                   feat, ...) whose books are all absent from this entry's `source_ids` and all
                   printed after this entry's last book. Rule glossary targets other than class
                   abilities (umr, faith, family, ref/rule) and companions are skipped: they are
                   not rules that a later book added to the entry
    resolution     the entry has a hand resolution (scripts/class-option-power-resolutions.toml)
                   whose replacement keeps blocks after the power: prose that print may not set
                   there

An attributed block is one inside a heading section whose first block is a `**Sources:**` line.
Those sections name their book already and are never candidates.

`scripts/later-book-rules-reviewed.tsv` records the outcome of each reviewed candidate: entry id,
signal, a short key (the first words of the block, or the link target), the outcome and the reason
with the book title and page. The outcomes are `fixed` (now an attributed section, or removed),
`left` (print shows the text belongs to the entry's own book) and `OPEN` (the later book is not
among the reviewed PDFs, or the source needs an owner decision; nothing changed). `--check` fails
when a candidate is not in the file.

The survey finds candidates only. Confirming one against print, in the entry's own book and in the
later book, is the reviewer's work. It does not reach everything: `ref/class/alchemist` and
`ref/invtalent/alchemist-discovery` carry the anointing rule too, but a class and an investigator
talent are not in GROUPS. The issue named both, and they were checked by hand (their rows are in the
file as `fixed`).
"""

from __future__ import annotations

import argparse
import importlib.util
import re
import sys
import tomllib
from collections import Counter
from pathlib import Path

GROUPS = {
    "arcane-school": "arcane and elemental schools",
    "cleric-domain": "domains and subdomains",
    "druid-domain": "druid domains",
    "sorcerer-bloodline": "bloodlines",
    "bloodrager-bloodline": "bloodlines",
    "oracle-mystery": "mysteries",
    "witch-patron": "patrons",
    "medium-spirit": "spirits",
    "shaman-spirit": "spirits",
    "order": "orders",
    "hellknight-order": "orders",
    "inquisition": "inquisitions",
    "psychic-discipline": "disciplines",
    "hellknight-discipline": "disciplines",
    "occultist-implement": "implement schools",
    "warpriest-blessing": "blessings",
    "shifter-aspect": "aspects",
}
SELECTION = re.compile(r"\b(?:instead of|in place of|rather than)\b", re.I)
FEATURE_TYPE = re.compile(
    r"annointing|anointing|discover(?:y|ies)\b|\bhexes?\b|rage powers?|magus arcana|arcanist exploits?"
    r"|mesmerist tricks?|ninja tricks?|(?:rogue|slayer|investigator|vigilante) talents?|\barchetypes?\b",
    re.I,
)
PROSE_ROWS = {"Special", "Info", "Details"}
SKIP_TARGETS = ("ref/umr/", "ref/faith/", "ref/family/", "ref/companion/")
LINK = re.compile(r"\]\((ref/[^)#\s]+)")
FRONT = re.compile(r"\A\+\+\+\n(.*?)\n\+\+\+\n", re.S)
REVIEWED = "scripts/later-book-rules-reviewed.tsv"


def load_power_module(here: Path):
    spec = importlib.util.spec_from_file_location("rw", here / "rewrite-class-option-powers.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules["rw"] = module
    spec.loader.exec_module(module)
    return module


def key_of(text: str) -> str:
    return " ".join(re.sub(r"[*_\[\]]|\(ref/[^)]*\)", "", text).split()[:8])


def attributed_flags(blocks) -> list[bool]:
    """Per block: inside a heading section that opens with a `**Sources:**` line."""
    flags, current = [], False
    for i, b in enumerate(blocks):
        if b.kind == "boundary" and b.lines[0].startswith("#"):
            nxt = blocks[i + 1] if i + 1 < len(blocks) else None
            current = bool(nxt and nxt.text.startswith("**Sources:**"))
            flags.append(True)
            continue
        flags.append(current)
    return flags


def attributed_tail(tail, i: int) -> bool:
    """Whether tail block `i` of a resolution is part of a section that opens with a Sources line."""
    current = False
    for k, b in enumerate(tail[: i + 1]):
        if b.kind == "boundary" and b.lines[0].startswith("#"):
            nxt = tail[k + 1] if k + 1 < len(tail) else None
            current = bool(nxt and nxt.text.startswith("**Sources:**"))
            if k == i:
                return True
    return current


def survey(corpus: Path, rw):
    publications = {p["id"]: p.get("publication_date", "") for p in
                    tomllib.loads((corpus / "publications.toml").read_text())["publication"]}
    entries = {}
    for path in sorted((corpus / "entries").rglob("*.md")):
        text = path.read_text()
        front = FRONT.match(text)
        if front:
            entries[tomllib.loads(front.group(1))["id"]] = (tomllib.loads(front.group(1)), text[front.end():])
    resolutions = rw.load_resolutions(corpus / rw.RESOLUTIONS_FILE)
    tails = {}
    for (eid, name, _), res in resolutions.items():
        blocks = rw.parse_blocks(res.replacement.strip("\n").split("\n"))
        cands = rw.candidates(blocks)
        tail = [b for b in blocks[cands[0].end:]] if cands else []
        # the blocks of an attributed section (heading, Sources line, text) are fine
        if any(not attributed_tail(tail, i) for i in range(len(tail))):
            tails[eid] = name
    found = []   # (entry id, group, signal, key, excerpt)
    for eid, (front, body) in sorted(entries.items()):
        group = front.get("fields", {}).get("group")
        if group not in GROUPS:
            continue
        blocks = rw.parse_blocks(body.split("\n"))
        flags = attributed_flags(blocks)
        names = [i for i, b in enumerate(blocks) if b.kind == "name"]
        first = names[0] if names else None
        for i, b in enumerate(blocks):
            if flags[i]:
                continue
            styled = b.kind == "boundary" and b.lines[0].startswith(":::")
            if styled and first is not None and i > first:
                found.append((eid, group, "styled", key_of(b.text), b.text.replace("\n", " ")))
            prose = (b.kind == "para" or styled or (b.kind == "row" and b.label in PROSE_ROWS))
            if prose and SELECTION.search(b.text) and FEATURE_TYPE.search(b.text):
                found.append((eid, group, "selection", key_of(b.text), b.text.replace("\n", " ")))
        mine = set(front["source_ids"])
        last_own = max((publications.get(s, "") for s in mine), default="")
        unattributed = "\n\n".join(b.text for b, done in zip(blocks, flags) if not done)
        for target in sorted(set(LINK.findall(unattributed))):
            if target not in entries or target.startswith(SKIP_TARGETS):
                continue
            tfront = entries[target][0]
            theirs = set(tfront["source_ids"])
            if theirs & mine:
                continue
            if tfront["kind"] == "rule" and not target.startswith("ref/ability/"):
                continue
            if min((publications.get(s, "") for s in theirs), default="") > last_own:
                found.append((eid, group, "later-link", target, f"{target} ({', '.join(sorted(theirs))})"))
        if eid in tails:
            found.append((eid, group, "resolution", key_of(tails[eid]), f"resolution of {tails[eid]} keeps blocks after the power"))
    return found


def load_reviewed(corpus: Path) -> set[tuple[str, str, str]]:
    path = corpus / REVIEWED
    if not path.exists():
        return set()
    out = set()
    for line in path.read_text().splitlines()[1:]:
        cols = line.split("\t")
        if len(cols) >= 5:
            out.add((cols[0], cols[1], cols[2]))
    return out


def main() -> int:
    here = Path(__file__).resolve().parent
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("corpus", nargs="?", default=str(here.parent))
    ap.add_argument("--counts", action="store_true")
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    corpus = Path(args.corpus)
    found = survey(corpus, load_power_module(here))
    reviewed = load_reviewed(corpus)
    by_kind = Counter((GROUPS[g], s) for _, g, s, _, _ in found)
    print(f"candidates: {len(found)} in {len({f[0] for f in found})} entries")
    for (kind, signal), n in sorted(by_kind.items()):
        print(f"  {kind}\t{signal}\t{n}")
    open_items = [f for f in found if (f[0], f[2], f[3]) not in reviewed]
    print(f"not yet reviewed: {len(open_items)}")
    if not args.counts:
        for eid, group, signal, key, excerpt in found:
            mark = " " if (eid, signal, key) in reviewed else "?"
            print(f"{mark}\t{eid}\t{signal}\t{key}\t{excerpt[:200]}")
    return 1 if args.check and open_items else 0


if __name__ == "__main__":
    sys.exit(main())
