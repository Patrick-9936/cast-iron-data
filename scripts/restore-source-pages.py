#!/usr/bin/env python3
"""Restore the `[[sources]]` page of every entry that a `Page order` list places without one.

`books.toml` places an entry under a book's `Page order` chapter. The page that put it there
is not in the entry when the `**Sources:**` conversion (`sources-field.py`) kept only the first
citation of the entry: the entry then has no `[[sources]]` row for that book. A page-order book
that is derived from `[[sources]]` (phynics/cast-iron#425) would put such an entry under
`Unpaged`. This script adds the missing row. It never changes an `id`, moves a file, or removes
a `[[sources]]` row or a body citation.

A target is a pair (book B, entry E) with all of:

  * E is placed anywhere under a top-level `Page order` chapter of B in `books.toml`;
  * `B` is in E's `source_ids`;
  * E has no `[[sources]]` row for B (a row without a `page` is not a target);
  * the top of E's `parent` chain among the members of B (E itself when it has none) has no
    page for B. Derivation puts E in the chapter of that entry, so only these entries would
    move from `Page order` to `Unpaged`. An entry nested under a host that has a page keeps its
    chapter; `--include-nested` restores its page too.

The page, in this order:

  1. the entry's own body: a `**source:** Book/N;Other Book/M` line (the raw import form). The
     citation of B is `Book/N`. The line stays in the body: it can name books that are not in
     `source_ids`, which a row cannot hold.
  2. the entry's `provenance` record in the pinned upstream dataset (`pathfinder-data-1-e`).
     Every string of the record is searched, in record order, for `<title of B>/<page>`, where
     the title is any printed title or alias of B (`publications.toml`, `sources-field.py`). The
     first citation of B is the page. A record that points to another with `copyof` is followed.
     A record name of the form `base|section:id` or `file#name|section:id` reads `base` / `name`.

An entry for which neither gives a page is left as it is and is listed. A page is read as
`N` or `N-N`; text after it (`58~`, `, 60`) is dropped.

The same run also repairs a page string that holds a second citation (`39;Pathfinder #46:
Wake of the Watcher/77`, `58~Occult Origins/8`): the first page stays in the row, and each
further citation that maps to a publication of `source_ids` becomes its own row.

The script is rerunnable: once an entry has its row it is no longer a target.

Run from the corpus root, with the pinned upstream dataset extracted in a directory of its own
(`legal.toml` `[[datasets]]` has the commit; the files are not part of the corpus):

    python3 -I scripts/restore-source-pages.py --upstream <pathfinder-data-1-e dir> [--dry-run]
        [--report FILE.tsv]

Then format and check the corpus with the cast-iron tool:

    cargo xtask corpus-fmt --check <dir>
    cargo xtask corpus-check <dir>

Historical: this script reads the single `books.toml` of corpus formats 1 and 2, which format 3
removed (phynics/cast-iron#425). Run it on a checkout of commit c8aa0bc33 (tag v0.1.35), the
last format 2 commit.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import subprocess
import sys
import tomllib
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ENTRIES = ROOT / "entries"
DATASET = "pathfinder-data-1-e"
PAGE_RE = re.compile(r"\s*(\d+(?:\s*[-–]\s*\d+)?)")
BODY_SOURCE_RE = re.compile(r"^\*\*source:\*\*(.*)$", re.IGNORECASE)


def load_sources_field():
    """Reuse the title map of `sources-field.py` (the file name has a hyphen)."""
    spec = importlib.util.spec_from_file_location(
        "sources_field", Path(__file__).resolve().parent / "sources-field.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


SF = load_sources_field()


# ---------------------------------------------------------------- entries


def split_entry(text: str) -> tuple[str, str]:
    """(front matter text, body text) of an entry file."""
    assert text.startswith("+++\n"), "entry must start with +++"
    end = text.index("\n+++\n", 4)
    return text[4:end], text[end + 5 :]


def top_of(entry_id: str, book: str, entries: dict[str, dict]) -> str:
    """The entry whose chapter `entry_id` takes in a derived `book`: the last member on its
    `parent` chain, or the entry itself."""
    top = entry_id
    seen = {entry_id}
    parent = entries[entry_id]["meta"].get("parent")
    while parent and parent in entries and parent not in seen:
        seen.add(parent)
        if book in entries[parent]["meta"].get("source_ids", []):
            top = parent
        parent = entries[parent]["meta"].get("parent")
    return top


def has_page(entry: dict, book: str) -> bool:
    return any(row["publication"] == book and row.get("page") for row in entry["meta"].get("sources", []))


def load_entries() -> dict[str, dict]:
    entries: dict[str, dict] = {}
    for path in sorted(ENTRIES.rglob("*.md")):
        text = path.read_text(encoding="utf-8")
        front, body = split_entry(text)
        meta = tomllib.loads(front)
        entries[meta["id"]] = {"path": path, "meta": meta, "body": body}
    return entries


# ---------------------------------------------------------------- book lists


def page_order_placements(books: dict) -> list[tuple[str, str]]:
    """(book, entry) for every entry under a top-level `Page order` chapter, in book order."""
    out: list[tuple[str, str]] = []

    def walk(node: dict, book: str) -> None:
        if node.get("entry"):
            out.append((book, node["entry"]))
        for child in node.get("children", []):
            walk(child, book)

    for book in books["books"]:
        for chapter in book.get("chapters", []):
            if chapter["title"] == "Page order":
                walk(chapter, book["source"])
    return out


# ---------------------------------------------------------------- citations


class Titles:
    """Printed titles of each publication and a matcher for `<title>/<page>` citations."""

    def __init__(self) -> None:
        publications = SF.load_publications()
        self.title_to_id = SF.title_map(publications)
        by_id: dict[str, list[str]] = defaultdict(list)
        for title, pid in self.title_to_id.items():
            by_id[pid].append(title)
        self.by_id = by_id
        self._matchers: dict[str, re.Pattern[str]] = {}

    def matcher(self, publication: str) -> re.Pattern[str]:
        if publication not in self._matchers:
            alternatives = "|".join(
                re.escape(t) for t in sorted(self.by_id[publication], key=len, reverse=True)
            )
            self._matchers[publication] = re.compile(
                r"(?<![\w'’])(?:" + alternatives + r")/([^;›\"\]}\n]*)", re.IGNORECASE
            )
        return self._matchers[publication]

    def pages(self, text: str, publication: str) -> list[str]:
        """Every page cited for `publication` in `text`, in text order."""
        found = []
        for match in self.matcher(publication).finditer(SF.normalize(text) if "\\" in text else text):
            page = clean_page(match.group(1))
            if page is not None:
                found.append(page)
        return found


def clean_page(raw: str) -> str | None:
    match = PAGE_RE.match(raw)
    if not match:
        return None
    return re.sub(r"\s+", "", match.group(1)).replace("–", "-")


def strings(value):
    """Every string of a JSON value in document order, leaving out `sources` name lists."""
    if isinstance(value, str):
        yield value
    elif isinstance(value, list):
        for item in value:
            yield from strings(item)
    elif isinstance(value, dict):
        for key, item in value.items():
            if key != "sources":
                yield from strings(item)


class Upstream:
    def __init__(self, directory: Path | None) -> None:
        self.directory = directory
        self._files: dict[str, dict] = {}

    def file(self, path: str) -> dict | None:
        if self.directory is None:
            return None
        if path not in self._files:
            target = self.directory / path
            self._files[path] = json.loads(target.read_text(encoding="utf-8")) if target.is_file() else {}
        return self._files[path] or None

    def record_text(self, provenance: dict) -> tuple[str | None, str]:
        """(text of the record and its `copyof` chain, why it is None)."""
        if provenance["dataset"] != DATASET:
            return None, f"dataset {provenance['dataset']} is not supported"
        data = self.file(provenance["path"])
        if data is None:
            return None, f"upstream file {provenance['path']} not found"
        key = provenance["record"].split("|")[0].split("#")[-1]
        parts: list[str] = []
        seen: set[str] = set()
        record = data.get(key)
        if record is None:
            return None, f"record {key} not in {provenance['path']}"
        while record is not None and key not in seen:
            seen.add(key)
            parts.append("\n".join(strings(record)))
            key = record.get("copyof") if isinstance(record, dict) else None
            record = data.get(key) if key else None
        return "\n".join(parts), ""


def body_source_lines(body: str) -> list[str]:
    return [line for line in body.split("\n") if BODY_SOURCE_RE.match(line.strip())]


def resolve(entry: dict, book: str, titles: Titles, upstream: Upstream) -> dict:
    """The page of `entry` in `book` and where it came from, or why there is none."""
    for line in body_source_lines(entry["body"]):
        pages = titles.pages(BODY_SOURCE_RE.match(line.strip()).group(1).strip(), book)
        if pages:
            return {"page": pages[0], "via": "body", "where": "**source:** line", "pages": pages}
    reasons = []
    for provenance in entry["meta"].get("provenance", []):
        text, why = upstream.record_text(provenance)
        if text is None:
            reasons.append(why)
            continue
        pages = titles.pages(text, book)
        where = f"{provenance['path']}#{provenance['record']}"
        if pages:
            return {"page": pages[0], "via": "provenance", "where": where, "pages": pages}
        reasons.append(f"record {where} has no citation of the book")
    return {"page": None, "reason": "; ".join(reasons) or "no provenance and no **source:** line"}


# ---------------------------------------------------------------- editing


def toml_row(publication: str, page: str) -> list[str]:
    return ["[[sources]]", f"publication = {SF.toml_string(publication)}", f"page = {SF.toml_string(page)}"]


def add_rows(front: str, rows: list[tuple[str, str]]) -> str:
    """Append `[[sources]]` rows after the entry's last row, or before `[fields]`."""
    lines = front.split("\n")
    new: list[str] = []
    for publication, page in rows:
        new.extend(toml_row(publication, page))
    starts = [i for i, line in enumerate(lines) if line.strip() == "[[sources]]"]
    if starts:
        at = starts[-1] + 1
        while at < len(lines) and re.match(r"^(publication|page)\s*=", lines[at]):
            at += 1
        lines[at:at] = new
        return "\n".join(lines)
    at = next((i for i, line in enumerate(lines) if line.strip() == "[fields]"), len(lines))
    # The writer puts the first row right after the header keys and one blank line after the rows.
    blank = 1 if at > 0 and lines[at - 1].strip() == "" else 0
    new.append("")
    lines[at - blank : at] = new
    return "\n".join(lines)


def set_row_page(front: str, publication: str, old: str, new: str) -> str:
    """Change the `page` of the row for `publication` from `old` to `new`."""
    needle = f"page = {SF.toml_string(old)}"
    lines = front.split("\n")
    for i, line in enumerate(lines):
        if line == needle and any(
            lines[j] == f"publication = {SF.toml_string(publication)}" for j in range(max(0, i - 1), i)
        ):
            lines[i] = f"page = {SF.toml_string(new)}"
            return "\n".join(lines)
    raise ValueError(f"row {publication} {old!r} not found")


# ---------------------------------------------------------------- polluted pages


def repair_polluted(entry: dict, titles: Titles) -> tuple[list[tuple[str, str, str]], list[tuple[str, str]]]:
    """Rows whose page is not a page: [(publication, old page, clean page)], extra rows to add."""
    fixes, extra = [], []
    source_ids = set(entry["meta"].get("source_ids", []))
    have = {row["publication"] for row in entry["meta"].get("sources", [])}
    for row in entry["meta"].get("sources", []):
        page = row.get("page")
        if not page or re.fullmatch(r"\d+(-\d+)?(, \d+(-\d+)?)*|inside cover", page):
            continue
        head = re.split(r"[;~]", page, maxsplit=1)
        clean = clean_page(head[0])
        if clean is None or len(head) == 1:
            continue
        fixes.append((row["publication"], page, clean))
        for publication in titles.title_to_id.values():
            if publication in source_ids and publication not in have and publication != row["publication"]:
                pages = titles.pages(head[1], publication)
                if pages:
                    extra.append((publication, pages[0]))
                    have.add(publication)
    return fixes, extra


# ---------------------------------------------------------------- main


def check_dataset_pin(directory: Path) -> str:
    """Compare the upstream checkout with the pin in `legal.toml` when it is a git checkout."""
    legal = tomllib.loads((ROOT / "legal.toml").read_text(encoding="utf-8"))
    pin = next(d["commit"] for d in legal["datasets"] if d["id"] == DATASET)
    if (directory / ".git").exists():
        head = subprocess.run(
            ["git", "-C", str(directory), "rev-parse", "HEAD"], capture_output=True, text=True, check=True
        ).stdout.strip()
        if head != pin:
            raise SystemExit(f"upstream checkout is at {head}, legal.toml pins {pin}")
        return f"upstream checkout at the pin {pin[:12]}"
    return f"upstream directory is not a git checkout; the pin is {pin[:12]} (not verified)"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--upstream", type=Path, help="the pinned pathfinder-data-1-e directory")
    parser.add_argument("--dry-run", action="store_true", help="report without writing files")
    parser.add_argument(
        "--include-nested",
        action="store_true",
        help="also restore the page of an entry nested under a host that has a page",
    )
    parser.add_argument("--report", type=Path, help="write one TSV row per target to this file")
    options = parser.parse_args()

    if options.upstream is not None:
        print(check_dataset_pin(options.upstream))
    titles = Titles()
    upstream = Upstream(options.upstream)
    entries = load_entries()
    books = tomllib.loads((ROOT / "books.toml").read_text(encoding="utf-8"))

    targets: list[tuple[str, str]] = []
    for book, entry_id in page_order_placements(books):
        entry = entries[entry_id]
        meta = entry["meta"]
        if book not in meta.get("source_ids", []):
            continue
        if any(row["publication"] == book for row in meta.get("sources", [])):
            continue
        if not options.include_nested and has_page(entries[top_of(entry_id, book, entries)], book):
            continue
        targets.append((book, entry_id))

    results = []
    new_rows: dict[str, list[tuple[str, str]]] = defaultdict(list)
    for book, entry_id in targets:
        result = resolve(entries[entry_id], book, titles, upstream)
        result.update(book=book, entry=entry_id)
        results.append(result)
        if result["page"] is not None:
            new_rows[entry_id].append((book, result["page"]))

    repaired = []
    for entry_id, entry in entries.items():
        fixes, extra = repair_polluted(entry, titles)
        # A publication that the restore already gives a row is not added a second time.
        taken = {publication for publication, _ in new_rows.get(entry_id, [])}
        extra = [row for row in extra if row[0] not in taken]
        if fixes:
            repaired.append((entry_id, fixes, extra))

    if not options.dry_run:
        edits: dict[str, tuple[list, list]] = defaultdict(lambda: ([], []))
        for entry_id, rows in new_rows.items():
            edits[entry_id][1].extend(rows)
        for entry_id, fixes, extra in repaired:
            edits[entry_id][0].extend(fixes)
            edits[entry_id][1].extend(extra)
        for entry_id, (fixes, rows) in sorted(edits.items()):
            path = entries[entry_id]["path"]
            text = path.read_text(encoding="utf-8")
            front, body = split_entry(text)
            for publication, old, clean in fixes:
                front = set_row_page(front, publication, old, clean)
            front = add_rows(front, rows)
            path.write_text("+++\n" + front + "\n+++\n" + body, encoding="utf-8")

    found = [r for r in results if r["page"] is not None]
    missing = [r for r in results if r["page"] is None]
    print(f"targets (placed under Page order, no [[sources]] row, would move to Unpaged): {len(results)}")
    print(f"  page found: {len(found)}")
    print(f"    from the entry's **source:** line: {sum(r['via'] == 'body' for r in found)}")
    print(f"    from the provenance record: {sum(r['via'] == 'provenance' for r in found)}")
    multi = [r for r in found if len(set(r["pages"])) > 1]
    print(f"    record cites the book on more than one page (first taken): {len(multi)}")
    print(f"  no page found (left as they are): {len(missing)}")
    print(f"books: {len({r['book'] for r in results})}; books with a page restored: {len({r['book'] for r in found})}")
    for r in missing:
        print(f"  unresolved: {r['book']}  {r['entry']}  ({r['reason']})")
    print(f"polluted page strings repaired: {sum(len(f) for _, f, _ in repaired)} "
          f"(rows added from them: {sum(len(x) for _, _, x in repaired)})")
    for entry_id, fixes, extra in repaired:
        print(f"  {entry_id}: {fixes} + rows {extra}")
    if options.report:
        with options.report.open("w", encoding="utf-8") as out:
            out.write("book\tentry\tpage\tvia\twhere\tpages cited\n")
            for r in results:
                out.write(
                    "\t".join(
                        [
                            r["book"],
                            r["entry"],
                            r["page"] or "",
                            r.get("via", "none"),
                            r.get("where", r.get("reason", "")),
                            ",".join(dict.fromkeys(r.get("pages", []))),
                        ]
                    )
                    + "\n"
                )
    return 0


if __name__ == "__main__":
    sys.exit(main())
