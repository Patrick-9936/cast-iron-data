#!/usr/bin/env python3
"""Apply the reviewed removals of phynics/cast-iron#461 to a corpus.

    python3 scripts/membership-apply.py <corpus-dir> [--queue scripts/membership-queue-461.tsv]
        [--dry-run] [--only-kind racial_trait]

It reads the queue written by `scripts/membership-screen.py` and acts only on the rows whose
`verdict` column is `remove` (the print check is recorded there: `print_page`, `evidence`). Rows
marked `keep` or `expands` and rows without a verdict are never touched. For each removal it

  1. takes the book out of the entry's `source_ids` (order of the rest is kept),
  2. drops the entry's `[[sources]]` row for that book, if there is one,
  3. drops the entry's placement in that book from `books.toml`. The compiler requires every
     placement to be in `source_ids` (docs/corpus-format.md, "corpus-check"). A title-only group
     (no `entry`, no `anchor`) whose children are all removed is dropped as well.

It refuses a row that
  * has `gate = primary` (removing the first book changes the entry's primary book: those rows
    need their own decision) or tag `hub-keep`,
  * would leave `source_ids` empty (the last book of an entry is never removed),
  * names a book that is not in the entry's `source_ids`, or an entry that does not exist.
It never edits an `id` and never moves a file. The edit is textual and keeps the canonical form;
run `cargo xtask corpus-fmt --check <dir>` and `cargo xtask corpus-check <dir>` afterwards.

Applying twice is safe: a row whose book is already out of `source_ids` and `books.toml` is
reported as already applied. Output has ids and book ids only.
"""
from __future__ import annotations

import argparse
import csv
import re
import sys
from collections import defaultdict
from pathlib import Path


def read_queue(path: Path, only_kind: str | None) -> list[dict]:
    with open(path, encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f, delimiter="\t"))
    out = []
    for r in rows:
        if r["verdict"] != "remove":
            continue
        if only_kind and r["kind"] != only_kind:
            continue
        if r["gate"] or r["tag"] == "hub-keep":
            raise SystemExit(f"refused: {r['entry']} in {r['book']} is gated or a hub (gate={r['gate']!r}, tag={r['tag']})")
        if not r["print_page"] or not r["evidence"]:
            raise SystemExit(f"refused: {r['entry']} in {r['book']} has no print_page/evidence recorded")
        out.append(r)
    return out


def entry_path(root: Path, eid: str) -> Path:
    if not eid.startswith("ref/"):
        raise SystemExit(f"refused: unexpected entry id {eid}")
    return root / "entries" / (eid[len("ref/"):] + ".md")


SOURCE_IDS = re.compile(r"^source_ids = \[(.*)\]$", re.M)


def edit_entry(path: Path, book: str) -> str:
    """Remove `book` from one entry file. Returns 'removed' or 'absent'; raises on the last book."""
    text = path.read_text(encoding="utf-8")
    m = SOURCE_IDS.search(text)
    if not m:
        raise SystemExit(f"refused: {path.name} has no single-line source_ids")
    ids = re.findall(r'"([^"]*)"', m.group(1))
    if book not in ids:
        return "absent"
    if len(ids) == 1:
        raise SystemExit(f"refused: {book} is the last book of {path}")
    ids.remove(book)
    new_line = "source_ids = [" + ", ".join(f'"{i}"' for i in ids) + "]"
    text = text[:m.start()] + new_line + text[m.end():]
    # Drop the [[sources]] block of this book (header, `publication`, optional `page`).
    lines = text.split("\n")
    out, i = [], 0
    while i < len(lines):
        if lines[i] == "[[sources]]":
            j = i + 1
            while j < len(lines) and lines[j] and not lines[j].startswith("["):
                j += 1
            block = lines[i:j]
            if f'publication = "{book}"' in block:
                i = j
                continue
        out.append(lines[i])
        i += 1
    path.write_text("\n".join(out), encoding="utf-8")
    return "removed"


# --------------------------------------------------------------------------------- books.toml


HEADER = re.compile(r"^\[\[books((?:\.chapters)(?:\.children)*)?\]\]$")


def parse_books(text: str) -> list[list[str]]:
    """Split books.toml into blocks: a header line and its lines, up to the blank line.

    The file is canonical, so blocks are separated by exactly one blank line."""
    if "\n\n\n" in text or not text.endswith("\n") or text.endswith("\n\n"):
        raise SystemExit("refused: books.toml is not in canonical block form; run corpus-fmt first")
    return [b.split("\n") for b in text[:-1].split("\n\n")]


def apply_books(text: str, removals: dict[str, set[str]]) -> tuple[str, dict[str, int], int]:
    """Drop the node of each (book -> entry ids) removal. Returns the new text, counts per book,
    and the number of title-only groups dropped because their children all went."""
    blocks = parse_books(text)
    # Walk blocks in order, tracking the current book and a stack of (depth, block index).
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
    # A title-only group (no `entry`, no `anchor`) whose children all went is dropped as well.
    dropped_groups = 0
    changed = True
    while changed:
        changed = False
        for idx, kids in children.items():
            if idx in drop or not kids or not all(k in drop for k in kids):
                continue
            blk = blocks[idx]
            if any(l.startswith(("entry = ", "anchor = ")) for l in blk):
                continue
            drop.add(idx)
            dropped_groups += 1
            changed = True
    kept = ["\n".join(blk) for idx, blk in enumerate(blocks) if idx not in drop]
    return "\n\n".join(kept) + "\n", dict(counts), dropped_groups


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("corpus", type=Path)
    ap.add_argument("--queue", type=Path, default=Path(__file__).with_name("membership-queue-461.tsv"))
    ap.add_argument("--only-kind", default=None, help="act on one entry kind only, for example racial_trait")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    rows = read_queue(args.queue, args.only_kind)
    root = args.corpus
    removed = absent = 0
    removals: dict[str, set[str]] = defaultdict(set)
    seen = set()
    for r in rows:
        key = (r["book"], r["entry"])
        if key in seen:
            raise SystemExit(f"refused: duplicate row {r['entry']} in {r['book']}")
        seen.add(key)
        path = entry_path(root, r["entry"])
        if not path.is_file():
            raise SystemExit(f"refused: no entry file for {r['entry']}")
        if args.dry_run:
            text = path.read_text(encoding="utf-8")
            ids = re.findall(r'"([^"]*)"', SOURCE_IDS.search(text).group(1))
            if r["book"] in ids and len(ids) == 1:
                raise SystemExit(f"refused: {r['book']} is the last book of {r['entry']}")
            state = "removed" if r["book"] in ids else "absent"
        else:
            state = edit_entry(path, r["book"])
        removed += state == "removed"
        absent += state == "absent"
        removals[r["book"]].add(r["entry"])

    books_path = root / "books.toml"
    text = books_path.read_text(encoding="utf-8")
    new_text, counts, groups = apply_books(text, removals)
    if not args.dry_run:
        books_path.write_text(new_text, encoding="utf-8")
    placed = sum(counts.values())
    print(f"rows with verdict remove: {len(rows)}")
    print(f"source_ids: removed {removed}, already out {absent}")
    print(f"books.toml: placements dropped {placed}, empty title-only groups dropped {groups}")
    if args.dry_run:
        print("dry run: nothing written")
    return 0


if __name__ == "__main__":
    sys.exit(main())
