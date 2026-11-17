#!/usr/bin/env python3
"""Fix the placements whose book is not in the entry's `source_ids` (issue phynics/cast-iron#420).

    python3 scripts/fix-placements.py <corpus-dir> <step>

Steps, in the order they were applied (one commit each). Every step is idempotent: on a corpus
where it has nothing to do it changes nothing.

  source-ids   (a) add the book to `source_ids` where a body `**Sources:**` line names it
  listing      (b) remove the catch-all, `Page order` and `Unpaged` placements with no evidence
  core-rules   place each Core Rulebook rule that would lose its only printed placement into its
               printed Core Rulebook chapter, by its Core Rulebook page
  phantoms     (c) delete the books that have no `publications.toml` row
  bestiary     (d) settle the 33 curated placements from the printed books
  contents-diff <before books.toml> <after books.toml>
               count the Contents rows (placements outside a catch-all chapter) per book

The classification comes from `scripts/placement-audit.py`, which this script runs. Entry ids and
file locations never change. Only `books.toml`, `source_ids` and `[[sources]]` rows are edited.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
import tomllib
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import booktoml as bt  # noqa: E402

HERE = Path(__file__).resolve().parent
CATCH_ALL = "New entries (page order)"

# ---------------------------------------------------------------------------------------------
# Core Rulebook chapters by printed page. The first pages are the printed contents page of the
# Core Rulebook (6th printing); `docs/research/book-order-evidence.md` in cast-iron records the
# same table. The PDF page number equals the printed page number throughout.
#
# Print check for the appendices, made against the printed pages:
#   - Appendix 1 Special Abilities begins p. 554 and runs to p. 565. The section on Spell
#     Resistance ends in the left column of p. 565, and the Appendix 2 heading follows it lower on
#     that page.
#   - Appendix 2 Conditions begins on p. 565, runs over p. 566 and 567, and ends on p. 568, where
#     the Appendix 3 Inspiring Reading heading follows the last condition (Unconscious).
#   - Appendix 3 Inspiring Reading (p. 568) and Appendix 4 Game Aids (p. 569) have no corpus entries
#     and no group. A rule on p. 568 above the Appendix 3 heading belongs to Conditions.
CORE_CHAPTERS: list[tuple[str, int]] = [
    ("Getting Started", 8),
    ("Races", 20),
    ("Classes", 30),
    ("Skills", 86),
    ("Feats", 112),
    ("Equipment", 140),
    ("Additional Rules", 166),
    ("Combat", 178),
    ("Magic", 206),
    ("Spells", 224),
    ("Prestige Classes", 374),
    ("Gamemastering", 396),
    ("Environment", 410),
    ("Creating NPCs", 448),
    ("Magic Items", 458),
    ("Special Abilities", 554),
    ("Conditions", 565),
]
LAST_CORE_PAGE = 568  # the last page that can hold a corpus entry

# Sections of the curated Core Rulebook tree whose entries record no page. Their first printed pages
# come from the printed contents page, so a rule is placed beside the section it prints next to.
PRINTED_SECTION_START = {
    ("Getting Started", "Playing the Game"): 9,
    ("Getting Started", "Generating a Character"): 14,
    ("Additional Rules", "Alignment"): 166,
    ("Additional Rules", "Vital Statistics"): 168,
    ("Additional Rules", "Exploration"): 172,
    ("Combat", "Special Initiative Actions"): 202,
    ("Environment", "Weather"): 437,
    ("Magic Items", "Cursed Items"): 536,
}

# Three rules whose recorded page is not where the rule prints. Print: the Spell Resistance
# section (with "When Spell Resistance Applies" and "Successful Spell Resistance") is p. 564 to
# 565, in Appendix 1 Special Abilities. Each of the three goes into Special Abilities. The two
# entries whose recorded page is past the Appendix 2 heading get the printed page, p. 565.
SPECIAL_ABILITIES_BY_PRINT = {
    "ref/rule/spell-resistance-2": None,
    "ref/rule/when-spell-resistance-applies": ("566", "565"),
    "ref/rule/successful-spell-resistance": ("567", "565"),
}

# (d), settled from print. The printed Bestiary (Appendix 3 Glossary, Universal Monster Rules,
# pp. 298 to 306) holds none of these rules; Bestiary 2 (pp. 294 to 303) and Bestiary 3 (pp. 292
# to 301) print the ones that name them. The printed Bestiary prints no skaveling: the Skaveling
# bat template and its Ghoul Fever disease are in Bestiary 2, p. 42.
SKAVELING = "ref/carried/bestiary-2/monsters/bat/skaveling/special-abilities/disease/skaveling-ghoul-fever"

# ---------------------------------------------------------------------------------------------


def audit(root: Path) -> dict:
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "audit.json"
        subprocess.run(
            [sys.executable, "-I", str(HERE / "placement-audit.py"), str(root), "--json", str(out)],
            check=True,
            stdout=subprocess.DEVNULL,
        )
        return json.loads(out.read_text(encoding="utf-8"))


def read_books(root: Path) -> list[bt.Book]:
    text = (root / "books.toml").read_text(encoding="utf-8")
    bt.selftest(text)
    return bt.parse(text)


def write_books(root: Path, books: list[bt.Book]) -> None:
    # The file's last table ends with one newline, the others with a blank line.
    text = bt.render(books).rstrip("\n") + "\n"
    (root / "books.toml").write_text(text, encoding="utf-8")


def entry_path(root: Path, eid: str) -> Path:
    return root / "entries" / (eid.removeprefix("ref/") + ".md")


def split_entry(text: str) -> tuple[str, str]:
    assert text.startswith("+++\n")
    end = text.index("\n+++\n", 4)
    return text[4:end], text[end + 5 :]


def front_matter(root: Path, eid: str) -> dict:
    return tomllib.loads(split_entry(entry_path(root, eid).read_text(encoding="utf-8"))[0])


def core_page(root: Path, eid: str, publication: str = "core-rulebook") -> int | None:
    for src in front_matter(root, eid).get("sources", []):
        if src["publication"] == publication and str(src.get("page", "")).isdigit():
            return int(src["page"])
    return None


def set_source_ids(root: Path, eid: str, ids: list[str]) -> bool:
    path = entry_path(root, eid)
    text = path.read_text(encoding="utf-8")
    new = re.sub(r"^source_ids = \[.*\]$", "source_ids = [" + ", ".join(f'"{i}"' for i in ids) + "]", text, count=1, flags=re.M)
    assert re.search(r"^source_ids = \[", text, re.M), f"{path}: source_ids is not a one-line list"
    if new == text:
        return False
    path.write_text(new, encoding="utf-8")
    return True


def replace_source_page(root: Path, eid: str, publication: str, old: str, new: str) -> bool:
    path = entry_path(root, eid)
    text = path.read_text(encoding="utf-8")
    block = f'[[sources]]\npublication = "{publication}"\npage = "{old}"\n'
    if block not in text:
        assert f'publication = "{publication}"\npage = "{new}"\n' in text, f"{path}: unexpected sources row"
        return False
    path.write_text(text.replace(block, block.replace(f'"{old}"', f'"{new}"')), encoding="utf-8")
    return True


def add_source_row(root: Path, eid: str, publication: str, page: str) -> bool:
    path = entry_path(root, eid)
    text = path.read_text(encoding="utf-8")
    if f'publication = "{publication}"' in text:
        return False
    row = f'[[sources]]\npublication = "{publication}"\npage = "{page}"\n'
    # The writer puts `[[sources]]` rows after the front matter keys, before `[fields]`.
    marker = "\n[fields]\n"
    head, sep, rest = text.partition(marker)
    assert sep, f"{path}: no [fields] table"
    head = head.rstrip("\n") + "\n" + row
    path.write_text(head + sep + rest, encoding="utf-8")
    return True


def by_book(violations: list[dict], *groups: str) -> dict[str, set[str]]:
    out: dict[str, set[str]] = defaultdict(set)
    for v in violations:
        if v["group"] in groups:
            out[v["book"]].add(v["entry"])
    return out


# ---------------------------------------------------------------------------------------------


def step_source_ids(root: Path) -> None:
    changed = 0
    for v in audit(root)["violations"]:
        if v["group"] != "a":
            continue
        ids = list(v["source_ids"])
        if v["book"] not in ids:
            ids.append(v["book"])
            changed += set_source_ids(root, v["entry"], ids)
            print(f"  {v['entry']}: source_ids += {v['book']}")
    print(f"(a) source_ids edited: {changed}")


def step_listing(root: Path) -> None:
    drop = by_book(audit(root)["violations"], "b")
    books = read_books(root)
    removed: Counter[str] = Counter()
    for book in books:
        if book.source in drop:
            removed[book.source] = bt.remove_placements(book, drop[book.source])
    write_books(root, books)
    for src, n in removed.most_common():
        print(f"  {src}: {n}")
    print(f"(b) placements removed: {sum(removed.values())} in {len(removed)} books")


def chapter_of(page: int) -> str:
    assert 8 <= page <= LAST_CORE_PAGE, f"page {page} is outside the printed chapters"
    title = CORE_CHAPTERS[0][0]
    for name, first in CORE_CHAPTERS:
        if page >= first:
            title = name
    return title


def start_page(root: Path, chapter: str, node: bt.Node, cache: dict[str, int | None]) -> int | None:
    """First printed page of a node: its own entry's page, else the first page below it, else
    the printed first page of the section."""
    for n in node.walk():
        eid = n.entry
        if eid is None:
            continue
        if eid not in cache:
            cache[eid] = core_page(root, eid)
        if cache[eid] is not None:
            return cache[eid]
    return PRINTED_SECTION_START.get((chapter, node.title))


def step_core_rules(root: Path) -> None:
    unreachable = audit(root)["newly_unreachable_mech"]
    if not unreachable:
        print("core-rules: nothing to place")
        return
    books = read_books(root)
    core = next(b for b in books if b.source == "core-rulebook")
    chapters = {c.title: c for c in core.node.children if c.title in dict(CORE_CHAPTERS)}
    assert set(chapters) == {t for t, _ in CORE_CHAPTERS}, sorted(chapters)

    # The dataset order inside a page: the order of the retired page-ordered listing.
    prpg = next((b for b in books if b.source == "prpg-core-rulebook"), None)
    order: dict[str, int] = {}
    if prpg:
        for i, n in enumerate(prpg.node.walk()):
            if n.entry and n.entry not in order:
                order[n.entry] = i

    # Take the nodes out of the catch-all chapter; they keep their title and entry lines.
    catch_all = next(c for c in core.node.children if c.title == CATCH_ALL)
    todo = set(unreachable)
    moved: dict[str, bt.Node] = {}
    keep = []
    for node in catch_all.children:
        if node.entry in todo and not node.children:
            moved[node.entry] = node
        else:
            keep.append(node)
    catch_all.children = keep
    assert set(moved) == todo, f"not all placed in the catch-all: {sorted(todo - set(moved))[:5]}"

    pages: dict[str, int] = {}
    for eid in sorted(todo):
        fm = front_matter(root, eid)
        assert fm["kind"] == "rule" and "core-rulebook" in fm["source_ids"], eid
        page = core_page(root, eid)
        assert page is not None, f"{eid}: no Core Rulebook page"
        if eid in SPECIAL_ABILITIES_BY_PRINT:
            fix = SPECIAL_ABILITIES_BY_PRINT[eid]
            if fix:
                replace_source_page(root, eid, "core-rulebook", *fix)
                page = int(fix[1])
        pages[eid] = page

    cache: dict[str, int | None] = {}
    counts: Counter[str] = Counter()
    for eid in sorted(todo, key=lambda e: (pages[e], order.get(e, 10**9), e)):
        title = "Special Abilities" if eid in SPECIAL_ABILITIES_BY_PRINT else chapter_of(pages[eid])
        chapter = chapters[title]
        # Before the first child that starts on a later printed page; else at the end.
        at = len(chapter.children)
        for i, child in enumerate(chapter.children):
            sp = start_page(root, title, child, cache)
            if sp is not None and sp > pages[eid]:
                at = i
                break
        chapter.children.insert(at, moved[eid])
        cache[eid] = pages[eid]
        counts[title] += 1
    write_books(root, books)
    for name, _ in CORE_CHAPTERS:
        if counts[name]:
            print(f"  {name}: {counts[name]}")
    print(f"core-rules: placed {sum(counts.values())} rules in {len(counts)} Core Rulebook chapters")


def step_phantoms(root: Path) -> None:
    result = audit(root)
    assert not result["newly_unreachable_mech"], "place the Core Rulebook rules first (core-rules)"
    phantoms = {v["book"] for v in result["violations"] if v["group"] == "c"}
    books = read_books(root)
    gone = [b for b in books if b.source in phantoms]
    elsewhere = {n.entry for b in books if b.source not in phantoms for n in b.node.walk() if n.entry}
    stranded = {n.entry for b in gone for n in b.node.walk() if n.entry} - elsewhere
    assert not stranded, f"entries with no other placement: {sorted(stranded)[:5]}"
    placements = 0
    for b in gone:
        placements += sum(1 for n in b.node.walk() if n.entry)
        print(f"  {b.source}: {sum(1 for n in b.node.walk() if n.entry)}")
    write_books(root, [b for b in books if b.source not in phantoms])
    print(f"(c) books deleted: {len(gone)}, placements: {placements}")


def step_bestiary(root: Path) -> None:
    violations = [v for v in audit(root)["violations"] if v["group"] == "d"]
    books = read_books(root)
    drop: dict[str, set[str]] = defaultdict(set)
    for v in violations:
        if v["entry"] == SKAVELING:
            continue
        assert v["book"] == "bestiary" and v["top_chapter"] == "Universal Monster Rules", v
        drop["bestiary"].add(v["entry"])
    # Skaveling Ghoul Fever: Bestiary 2 (p. 42) prints it, Bestiary does not.
    skav = front_matter(root, SKAVELING)
    if skav["source_ids"] != ["bestiary-2"]:
        assert skav["source_ids"] == ["bestiary"], skav["source_ids"]
        set_source_ids(root, SKAVELING, ["bestiary-2"])
    add_source_row(root, SKAVELING, "bestiary-2", "42")
    drop["bestiary"].add(SKAVELING)
    removed = 0
    for book in books:
        if book.source in drop:
            removed += bt.remove_placements(book, drop[book.source])
    write_books(root, books)
    print(f"(d) placements removed: {removed}; source_ids of the Skaveling disease set to bestiary-2 (p. 42)")


def contents_rows(path: Path) -> Counter[str]:
    rows: Counter[str] = Counter()
    for book in bt.parse(path.read_text(encoding="utf-8")):
        for chapter in book.node.children:
            if chapter.title == CATCH_ALL:
                continue
            rows[book.source] += sum(1 for n in chapter.walk() if n.entry)
    return rows


def step_contents_diff(before: Path, after: Path) -> None:
    a, b = contents_rows(before), contents_rows(after)
    changed = {k: (a[k], b[k]) for k in sorted(set(a) | set(b)) if a[k] != b[k]}
    print("book | rows before | rows after | change   (rows outside the catch-all chapter)")
    for k, (x, y) in sorted(changed.items(), key=lambda kv: kv[1][1] - kv[1][0]):
        print(f"{k} | {x} | {y} | {y - x:+d}")
    print(f"books changed: {len(changed)}")


def main(argv: list[str]) -> int:
    if len(argv) >= 2 and argv[1] == "contents-diff":
        step_contents_diff(Path(argv[2]), Path(argv[3]))
        return 0
    if len(argv) != 3:
        print(__doc__)
        return 2
    root, step = Path(argv[1]), argv[2]
    steps = {
        "source-ids": step_source_ids,
        "listing": step_listing,
        "core-rules": step_core_rules,
        "phantoms": step_phantoms,
        "bestiary": step_bestiary,
    }
    if step not in steps:
        print(f"unknown step {step!r}; one of {', '.join(steps)}")
        return 2
    steps[step](root)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
