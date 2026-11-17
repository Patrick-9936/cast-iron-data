#!/usr/bin/env python3
"""Apply the reviewed decisions of phynics/cast-iron#459 to a corpus.

    python3 scripts/expansion-credits-apply.py <corpus-dir>
        [--decisions scripts/expansion-credits-459.tsv] [--dry-run]

The decision file has one row per (entry, book). Its `action` column is one of

  remove       the book does not print the entry. The script takes the book out of the entry's
               `source_ids`, drops the entry's `[[sources]]` row for it, and drops the entry's
               placement in that book from `books.toml` (the compiler requires every placement
               to be in `source_ids`).
  expanded_in  the book expands the entry and the expanding text has no entry of its own. The
               script does what `remove` does, then writes an `[[expanded_in]]` row with the
               book, the page that the removed `[[sources]]` row held (`cited_page`) and, when
               the `via` column is set, that entry id.
  page         the book prints the entry on a different page: the `[[sources]]` page becomes
               `print_page`. Nothing else changes.

The page that a removed `[[sources]]` row cited stays in the decision file (`cited_page`): the
entry can no longer hold it, because a `[[sources]]` row needs its book in `source_ids`.

Safety rules
  * An `id` is never edited and an entry file is never moved.
  * The last book of an entry is never removed.
  * Removing an entry's first book changes its primary book. The row must name the book that
    becomes first in `primary_to`, and the script refuses when it does not match.
  * A placement node that has children is never dropped (it would orphan them).
  * Applying twice is safe: a row that is already applied is reported and left alone.

Run `cargo xtask corpus-fmt <dir>` (canonical form) and `cargo xtask corpus-check <dir>` after.
Output has ids and book ids only.
"""
from __future__ import annotations

import argparse
import csv
import re
import sys
from collections import defaultdict
from pathlib import Path

SOURCE_IDS = re.compile(r"^source_ids = \[(.*)\]$", re.M)
HEADER = re.compile(r"^\[\[books((?:\.chapters)(?:\.children)*)?\]\]$")


def read_decisions(path: Path) -> list[dict]:
    with open(path, encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f, delimiter="\t"))
    seen = set()
    for r in rows:
        if r["action"] not in ("remove", "expanded_in", "page"):
            raise SystemExit(f"refused: unknown action {r['action']!r} for {r['entry']}")
        key = (r["entry"], r["book"])
        if key in seen:
            raise SystemExit(f"refused: duplicate row {r['entry']} in {r['book']}")
        seen.add(key)
        if r["action"] == "page" and not r["print_page"]:
            raise SystemExit(f"refused: {r['entry']} has action page but no print_page")
        if r["action"] != "page" and not r["evidence"]:
            raise SystemExit(f"refused: {r['entry']} in {r['book']} has no evidence recorded")
    return rows


def entry_path(root: Path, eid: str) -> Path:
    if not eid.startswith("ref/"):
        raise SystemExit(f"refused: unexpected entry id {eid}")
    return root / "entries" / (eid[len("ref/"):] + ".md")


def source_ids(text: str, name: str) -> list[str]:
    m = SOURCE_IDS.search(text)
    if not m:
        raise SystemExit(f"refused: {name} has no single-line source_ids")
    return re.findall(r'"([^"]*)"', m.group(1))


def header_end(lines: list[str]) -> int:
    """Index of the line where the front matter's table section ends (`[fields]` or the closing +++)."""
    for i in range(1, len(lines)):
        if lines[i] == "[fields]" or lines[i] == "+++":
            return i
    raise SystemExit("refused: front matter does not end")


def drop_source_row(lines: list[str], book: str) -> tuple[list[str], str]:
    """Remove the `[[sources]]` block of `book`. Returns the lines and the page it held."""
    out, i, page = [], 0, ""
    end = header_end(lines)
    while i < len(lines):
        if i < end and lines[i] == "[[sources]]":
            j = i + 1
            while j < len(lines) and lines[j] and not lines[j].startswith("["):
                j += 1
            block = lines[i:j]
            if f'publication = "{book}"' in block:
                for l in block:
                    m = re.match(r'^page = "([^"]*)"$', l)
                    if m:
                        page = m.group(1)
                i = j
                continue
        out.append(lines[i])
        i += 1
    return out, page


def edit_entry(path: Path, r: dict) -> str:
    """Apply one decision to one entry file. Returns 'applied' or 'already'."""
    text = path.read_text(encoding="utf-8")
    ids = source_ids(text, path.name)
    book, action = r["book"], r["action"]
    lines = text.split("\n")

    if action == "page":
        end = header_end(lines)
        for i in range(end):
            if lines[i] == "[[sources]]" and i + 1 < end and lines[i + 1] == f'publication = "{book}"':
                j = i + 2
                if j < end and lines[j].startswith("page = "):
                    if lines[j] == f'page = "{r["print_page"]}"':
                        return "already"
                    lines[j] = f'page = "{r["print_page"]}"'
                    path.write_text("\n".join(lines), encoding="utf-8")
                    return "applied"
                raise SystemExit(f"refused: {r['entry']} has no page to change in {book}")
        raise SystemExit(f"refused: {r['entry']} has no [[sources]] row for {book}")

    if book not in ids:
        if action == "expanded_in" and f'publication = "{book}"' not in text.split("[fields]")[0]:
            raise SystemExit(f"refused: {r['entry']} has neither {book} in source_ids nor an expanded_in row")
        return "already"
    if len(ids) == 1:
        raise SystemExit(f"refused: {book} is the last book of {r['entry']}")
    rest = [i for i in ids if i != book]
    if ids[0] == book and r["primary_to"] != rest[0]:
        raise SystemExit(f"refused: {r['entry']} loses its first book {book}; primary_to must be {rest[0]}")
    if ids[0] != book and r["primary_to"]:
        raise SystemExit(f"refused: {r['entry']} names primary_to but {book} is not its first book")

    m = SOURCE_IDS.search(text)
    lines = (text[: m.start()] + "source_ids = [" + ", ".join(f'"{i}"' for i in rest) + "]" + text[m.end():]).split("\n")
    lines, page = drop_source_row(lines, book)
    if action == "expanded_in":
        block = ["[[expanded_in]]", f'publication = "{book}"']
        if page or r["cited_page"]:
            block.append(f'page = "{page or r["cited_page"]}"')
        if r["via"]:
            block.append(f'via = "{r["via"]}"')
        end = header_end(lines)
        at = end - 1 if end > 0 and lines[end - 1] == "" else end
        lines[at:at] = block
    path.write_text("\n".join(lines), encoding="utf-8")
    return "applied"


def parse_books(text: str) -> list[list[str]]:
    """Split books.toml into blocks: a header line and its lines, up to the blank line."""
    if "\n\n\n" in text or not text.endswith("\n") or text.endswith("\n\n"):
        raise SystemExit("refused: books.toml is not in canonical block form; run corpus-fmt first")
    return [b.split("\n") for b in text[:-1].split("\n\n")]


def apply_books(text: str, removals: dict[str, set[str]]) -> tuple[str, dict[str, int], int]:
    """Drop the node of each (book -> entry ids) removal. Returns the new text, the number of
    nodes dropped per book, and the number of title-only groups dropped because all their
    children went."""
    blocks = parse_books(text)
    book = None
    stack: list[tuple[int, int]] = []
    children: dict[int, list[int]] = defaultdict(list)
    drop: set[int] = set()
    counts: dict[str, int] = defaultdict(int)
    for idx, blk in enumerate(blocks):
        m = HEADER.match(blk[0])
        if not m:
            continue
        if m.group(1) is None:  # [[books]]
            sm = next((re.match(r'^source = "([^"]*)"$', l) for l in blk if l.startswith("source = ")), None)
            book = sm.group(1) if sm else None
            stack = []
            continue
        depth = 1 + m.group(1).count(".children")
        while stack and stack[-1][0] >= depth:
            stack.pop()
        parent = stack[-1][1] if stack else None
        if parent is not None:
            children[parent].append(idx)
        stack.append((depth, idx))
        em = next((re.match(r'^entry = "([^"]*)"$', l) for l in blk if l.startswith("entry = ")), None)
        if em and book in removals and em.group(1) in removals[book]:
            drop.add(idx)
            counts[book] += 1
    for idx in sorted(drop):
        if children.get(idx):
            raise SystemExit(f"refused: a placement of {blocks[idx][0]} in books.toml has children; decide it by hand")
    dropped_groups = 0
    changed = True
    while changed:
        changed = False
        for idx, kids in children.items():
            if idx in drop or not kids or not all(k in drop for k in kids):
                continue
            if any(l.startswith(("entry = ", "anchor = ")) for l in blocks[idx]):
                continue
            drop.add(idx)
            dropped_groups += 1
            changed = True
    kept = ["\n".join(blk) for idx, blk in enumerate(blocks) if idx not in drop]
    return "\n\n".join(kept) + "\n", dict(counts), dropped_groups


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("corpus", type=Path)
    ap.add_argument("--decisions", type=Path, default=Path(__file__).with_name("expansion-credits-459.tsv"))
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    rows = read_decisions(args.decisions)
    root = args.corpus
    tally: dict[str, int] = defaultdict(int)
    removals: dict[str, set[str]] = defaultdict(set)
    for r in rows:
        path = entry_path(root, r["entry"])
        if not path.is_file():
            raise SystemExit(f"refused: no entry file for {r['entry']}")
        if args.dry_run:
            ids = source_ids(path.read_text(encoding="utf-8"), path.name)
            state = "applied" if (r["action"] == "page" or r["book"] in ids) else "already"
        else:
            state = edit_entry(path, r)
        tally[f"{r['action']} {state}"] += 1
        if r["action"] != "page":
            removals[r["book"]].add(r["entry"])

    books_path = root / "books.toml"
    text = books_path.read_text(encoding="utf-8")
    new_text, counts, groups = apply_books(text, removals)
    if not args.dry_run:
        books_path.write_text(new_text, encoding="utf-8")
    for k in sorted(tally):
        print(f"{k}: {tally[k]}")
    print(f"books.toml: placements dropped {sum(counts.values())}, empty title-only groups dropped {groups}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
