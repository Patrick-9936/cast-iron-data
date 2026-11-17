#!/usr/bin/env python3
"""Apply the reviewed removals of phynics/cast-iron#461 to a corpus.

    python3 scripts/membership-apply.py <corpus-dir> [--queue scripts/membership-queue-461.tsv]
        [--dry-run] [--only-kind racial_trait]

It reads the queue written by `scripts/membership-screen.py` and acts only on the rows whose
`verdict` column is `remove` (the print check is recorded there: `print_page`, `evidence`). Rows
marked `keep` or `expands` and rows without a verdict are never touched. For each removal it

  1. takes the book out of the entry's `source_ids` (order of the rest is kept),
  2. drops the entry's placement in that book from `books.toml`. The compiler requires every
     placement to be in `source_ids` (docs/corpus-format.md, "corpus-check"). A title-only group
     (no `entry`, no `anchor`) whose children are all removed is dropped as well.

It never deletes a page citation silently. A `[[sources]]` row must name a book in `source_ids`,
and a raw `**source:** Book/N` or `**Sources:** Book pg N` line in the body is the only page
citation for many entries, so a removal that would leave either one behind is refused: the whole
run stops before it writes anything. A `[[sources]]` row may go only when the audit file
(`scripts/membership-citation-audit-461.tsv`, `--audit`) has a row for that (entry, book) with
the same `cited_page` and one of these classes:

  wrong-credit the cited page was read and the book does not print the entry there or anywhere
               (the page prints another entry, usually a sibling variant). The rejected page
               stays in the audit file (`invalidated`).
  family-ref   the cited page prints a related entry (`family`). The script checks that it
               exists, lists the book, cites `related_cite` there (within one page of this
               entry's citation), and that a `variant`, `addon`, `part` or `revision` relation
               joins the two entries (either direction). The page then survives on the related
               entry.

  mention      the book only mentions the entry (owner decision 2026-11-17: a mention is not a
               printing; the membership goes). The row carries `invalidated`, `mention_pages` and
               `mention_kind` (in the maintainer's words, no book text). A queue row with evidence
               `passing-mention-recorded` needs such a row.

The columns and class names follow `scripts/expansion-credits-459.tsv` (#459).

A body source line is never deleted by this script: convert it first (to an `expanded_in`
credit once #458 lands, or by keeping the membership if the book prints the entry).

It refuses a row that
  * has a `[[sources]]` row that the audit file does not release, or a body source line, that
    names the book (see above),
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
import tomllib
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


SOURCE_LINE = re.compile(r"\*\*[Ss]ources?:?\*\*")


def fold(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", s.replace("\u2019", "'").replace("'", "").lower()).strip()


def citation_blocking(text: str, book: str, title: str) -> str | None:
    """What page citation of `book` the entry holds, if any: a `[[sources]]` row or a body
    source line that names the book's title. Such a citation must not be deleted."""
    lines = text.split("\n")
    for i, line in enumerate(lines):
        if line == "[[sources]]" and f'publication = "{book}"' in lines[i + 1:i + 3]:
            return "a [[sources]] row"
    body = text.split("+++", 2)[2] if text.startswith("+++") else text
    ft = fold(title)
    for line in body.split("\n"):
        if SOURCE_LINE.search(line) and ft and re.search(r"(?<![a-z0-9])" + re.escape(ft) + r"(?![a-z0-9])", fold(line)):
            return "a body source line"
    return None


def drop_sources_row(text: str, book: str) -> str:
    """Delete the `[[sources]]` block of `book` (its header line and the lines up to the next
    blank line or table header)."""
    lines = text.split("\n")
    for i, line in enumerate(lines):
        if line == "[[sources]]" and f'publication = "{book}"' in lines[i + 1:i + 3]:
            j = i + 1
            while j < len(lines) and lines[j] and not lines[j].startswith("["):
                j += 1
            return "\n".join(lines[:i] + lines[j:])
    return text


def sources_page(text: str, book: str) -> str:
    lines = text.split("\n")
    for i, line in enumerate(lines):
        if line == "[[sources]]" and f'publication = "{book}"' in lines[i + 1:i + 3]:
            for l in lines[i + 1:i + 4]:
                m = re.match(r'^page = "([^"]*)"$', l)
                if m:
                    return m.group(1)
    return ""


def spans(page: str) -> list[tuple[int, int]]:
    out = []
    for part in re.split(r"\s*,\s*", page):
        m = re.fullmatch(r"(\d+)(?:\s*[-\u2013]\s*(\d+))?", part.strip())
        if m:
            a = int(m.group(1))
            out.append((a, int(m.group(2) or a)))
    return out


def overlap(p1: str, p2: str) -> bool:
    return any(a <= z2 and a2 <= z for a, z in spans(p1) for a2, z2 in spans(p2))


def read_audit(path: Path | None) -> dict[tuple[str, str], dict]:
    if path is None or not path.is_file():
        return {}
    with open(path, encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f, delimiter="\t"))
    out = {}
    for r in rows:
        if r["class"] not in ("wrong-credit", "family-ref", "mention"):
            raise SystemExit(f"refused: audit row {r['entry']} has unknown class {r['class']!r}")
        if not r["print_page"] or not r["evidence"] or not r["read"]:
            raise SystemExit(f"refused: audit row {r['entry']} in {r['book']} has no print_page/read/evidence")
        if r["class"] in ("wrong-credit", "mention") and not r["invalidated"]:
            raise SystemExit(f"refused: audit row {r['entry']} in {r['book']} has no invalidated citation")
        if r["class"] == "mention" and not (r["mention_pages"] and r["mention_kind"]):
            raise SystemExit(f"refused: audit row {r['entry']} in {r['book']} is a mention without mention_pages and mention_kind")
        if r["class"] == "family-ref" and not (r["family"] and r["related_cite"]):
            raise SystemExit(f"refused: audit row {r['entry']} in {r['book']} is a family-ref without family and related_cite")
        out[(r["entry"], r["book"])] = r
    return out


EDGE_KINDS = ("variant", "addon", "part", "revision")


def has_edge(root: Path, a: str, b: str) -> bool:
    for x, y in ((a, b), (b, a)):
        t = entry_path(root, x).read_text(encoding="utf-8")
        fm = t.split("+++", 2)[1]
        for m in re.finditer(r'\{ kind = "([a-z-]+)", target = "([^"]+)"', fm):
            if m.group(1) in EDGE_KINDS and m.group(2) == y:
                return True
    return False


def release_citation(root: Path, entry: str, book: str, text: str, audit: dict) -> None:
    """Refuse unless the audit file releases the entry's `[[sources]]` row for `book`."""
    row = audit.get((entry, book))
    if row is None:
        raise SystemExit(f"refused: {entry} holds a [[sources]] row for {book} and the audit file has no row for it; convert it, never delete it")
    page = sources_page(text, book)
    if row["cited_page"] != page:
        raise SystemExit(f"refused: {entry} audit cited_page {row['cited_page']!r} is not the row's page {page!r}")
    if row["class"] == "family-ref":
        rel = row["family"]
        rp = entry_path(root, rel)
        if not rp.is_file():
            raise SystemExit(f"refused: {entry} audit names no existing related entry")
        rt = rp.read_text(encoding="utf-8")
        ids = re.findall(r'"([^"]*)"', (SOURCE_IDS.search(rt) or [None, ""])[1])
        rpage = sources_page(rt, book)
        if book not in ids or rpage != row["related_cite"] or not overlap(page, rpage):
            raise SystemExit(f"refused: related {rel} does not list {book} at p. {row['related_cite']}")
        if not has_edge(root, entry, rel):
            raise SystemExit(f"refused: no variant/addon/part/revision relation between {entry} and {rel}; add it first")


def edit_entry(path: Path, book: str, title: str, write: bool = True,
               entry: str = "", root: Path | None = None, audit: dict | None = None) -> str:
    """Remove `book` from `source_ids` of one entry file. Returns 'removed' or 'absent'; refuses
    the last book and any page citation of the book. Nothing but the `source_ids` line changes."""
    text = path.read_text(encoding="utf-8")
    m = SOURCE_IDS.search(text)
    if not m:
        raise SystemExit(f"refused: {path.name} has no single-line source_ids")
    ids = re.findall(r'"([^"]*)"', m.group(1))
    if book not in ids:
        return "absent"
    if len(ids) == 1:
        raise SystemExit(f"refused: {book} is the last book of {path}")
    held = citation_blocking(text, book, title)
    drop_row = False
    if held == "a [[sources]] row":
        release_citation(root, entry, book, text, audit or {})
        drop_row = True
    elif held:
        raise SystemExit(f"refused: {path.name} holds {held} for {book}; convert it, never delete it")
    ids.remove(book)
    new_line = "source_ids = [" + ", ".join(f'"{i}"' for i in ids) + "]"
    if write:
        new = text[:m.start()] + new_line + text[m.end():]
        if drop_row:
            new = drop_sources_row(new, book)
        path.write_text(new, encoding="utf-8")
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
    ap.add_argument("--audit", type=Path, default=Path(__file__).with_name("membership-citation-audit-461.tsv"),
                    help="rows that release a [[sources]] row (class invalidated or reference)")
    ap.add_argument("--only-kind", default=None, help="act on one entry kind only, for example racial_trait")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    rows = read_queue(args.queue, args.only_kind)
    root = args.corpus
    audit = read_audit(args.audit)
    titles = {p["id"]: p["title"] for p in tomllib.loads((root / "publications.toml").read_text(encoding="utf-8"))["publication"]}
    removals: dict[str, set[str]] = defaultdict(set)
    seen = set()
    todo = []
    for r in rows:
        key = (r["book"], r["entry"])
        if key in seen:
            raise SystemExit(f"refused: duplicate row {r['entry']} in {r['book']}")
        seen.add(key)
        if r["book"] not in titles:
            raise SystemExit(f"refused: unknown book {r['book']}")
        path = entry_path(root, r["entry"])
        if not path.is_file():
            raise SystemExit(f"refused: no entry file for {r['entry']}")
        if r["evidence"] == "passing-mention-recorded" and audit.get((r["entry"], r["book"]), {}).get("class") != "mention":
            raise SystemExit(f"refused: {r['entry']} in {r['book']} is a passing mention with no `mention` audit row")
        todo.append((path, r))
    # Check every row first (a refusal stops the run before anything is written), then write.
    for path, r in todo:
        edit_entry(path, r["book"], titles[r["book"]], write=False, entry=r["entry"], root=root, audit=audit)
    removed = absent = 0
    for path, r in todo:
        state = edit_entry(path, r["book"], titles[r["book"]], write=not args.dry_run, entry=r["entry"], root=root, audit=audit)
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
