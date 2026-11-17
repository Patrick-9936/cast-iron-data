#!/usr/bin/env python3
"""Place Bestiary 2's printed Universal Monster Rules in its Universal Monster Rules chapter
(issue phynics/cast-iron#420, follow-up to cast-iron-data #86).

    python3 scripts/place-bestiary-2-umr.py <corpus-dir>

Bestiary 2 prints 28 of these rules in Appendix 3: Glossary (printed contents page: p. 294), under
the heading Universal Monster Rules, which runs pp. 294 to 303; Creature Types follows on p. 304.
They sat only in the residual `New entries (page order)` chapter, so Contents did not show them.
This script moves each into the `Universal Monster Rules` chapter, in printed page order. The
chapter already holds Lycanthropic Empathy (p. 298), which stays and is ordered with them.
Entries on one page keep the printed alphabetical order. No entry id or file changes.

The pages come from the printed Bestiary 2 (the PDF page number is the printed number plus one);
each rule's name and format line was found on the page given. The script is idempotent: a second
run changes nothing.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import booktoml as bt  # noqa: E402

BOOK = "bestiary-2"
CHAPTER = "Universal Monster Rules"
CATCH_ALL = "New entries (page order)"
PREFIX = "ref/carried/bestiary/rules/universal-monster-rules/"

# (title, entry id, printed page). The entry ids are the carried rules; none changes.
RULES: list[tuple[str, str, int]] = [
    ("All-Around Vision", PREFIX + "all-around-vision", 294),
    ("Amorphous", PREFIX + "amorphous", 294),
    ("Attach", PREFIX + "attach", 294),
    ("Blood Drain", PREFIX + "blood-drain", 294),
    ("Blood Rage", PREFIX + "blood-rage", 294),
    ("Compression", PREFIX + "compression", 295),
    ("Curse of Lycanthropy", PREFIX + "curse-of-lycanthropy", 295),
    ("Earth Glide", PREFIX + "earth-glide", 296),
    ("Engulf", PREFIX + "engulf", 296),
    ("Entrap", PREFIX + "entrap", 296),
    ("Fast Swallow", PREFIX + "fast-swallow", 297),
    ("Freeze", PREFIX + "freeze", 297),
    ("Heat", PREFIX + "heat", 298),
    ("Hold Breath", PREFIX + "hold-breath", 298),
    ("Jet", PREFIX + "jet", 298),
    ("Keen Scent", PREFIX + "keen-scent", 298),
    ("Lifesense", PREFIX + "lifesense", 298),
    ("Multiweapon Mastery", PREFIX + "multiweapon-mastery", 299),
    ("Natural Invisibility", PREFIX + "natural-invisibility", 299),
    ("Negative Energy Affinity", PREFIX + "negative-energy-affinity", 299),
    ("No Breath", PREFIX + "no-breath", 299),
    ("See in Darkness", PREFIX + "see-in-darkness", 301),
    ("Sound Mimicry", PREFIX + "sound-mimicry", 301),
    ("Split", PREFIX + "split", 302),
    ("Strangle", PREFIX + "strangle", 302),
    ("Sunlight Powerlessness", PREFIX + "sunlight-powerlessness", 302),
    ("Undersized Weapons", PREFIX + "undersized-weapons", 303),
    ("Unnatural Aura", PREFIX + "unnatural-aura", 303),
]
# The placements the chapter already held, both Bestiary 2 p. 298: the rule, and its format split
# nested under it. The rule's printed page orders it among the others; the split stays under it.
EXISTING: list[tuple[str, str, int]] = [
    ("Lycanthropic Empathy", "ref/umr/lycanthropic-empathy", 298),
    ("Lycanthropic Empathy", "ref/rule/umr-lycanthropic-empathy/lycanthropic-empathy", 298),
]


def main(corpus: Path) -> None:
    path = corpus / "books.toml"
    text = path.read_text()
    bt.selftest(text)
    books = bt.parse(text)
    book = next(b for b in books if b.source == BOOK)
    chapter = next(c for c in book.node.children if c.title == CHAPTER)
    catch_all = next(c for c in book.node.children if c.title == CATCH_ALL)

    ids = {entry for _, entry, _ in RULES}
    taken = {c.entry for c in chapter.children}
    # Remove the catch-all placements (each is a leaf), then add the ones the chapter lacks.
    catch_all.children = [c for c in catch_all.children if c.entry not in ids]
    pages = {entry: page for _, entry, page in RULES}
    pages.update({entry: page for _, entry, page in EXISTING})
    for title, entry, _ in RULES:
        if entry not in taken:
            node = bt.Node(
                header="[[books.chapters.children]]\n",
                lines=[f'title = "{title}"\n', f'entry = "{entry}"\n', "\n"],
            )
            chapter.children.append(node)
    for node in chapter.children:  # every placement in the chapter, nested ones included
        for c in node.walk():
            if c.entry not in pages:
                raise SystemExit(f"unexpected placement in {CHAPTER}: {c.entry}")
    chapter.children.sort(key=lambda c: (pages[c.entry], c.title))
    for c in chapter.children:
        bt.ensure_blank_after(c)
        for g in c.children:
            bt.ensure_blank_after(g)
    bt.fix_headers(books)
    out = bt.render(books)
    if out != text:
        path.write_text(out)
        print("books.toml updated")
    else:
        print("nothing to do")


if __name__ == "__main__":
    main(Path(sys.argv[1]))
