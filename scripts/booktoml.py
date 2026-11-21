"""A line-level reader and writer for `books.toml`, so a script can edit the tree and leave every
other byte of the file alone (issue phynics/cast-iron#420).

`books.toml` is a flat list of tables: `[[books]]`, then `[[books.chapters]]`, then
`[[books.chapters.children]]` and deeper. A node's depth is its number of `.children` segments
plus one for a chapter. A node's children are the blocks that follow it with a greater depth.

Only single-line `key = "string"` values are read (`title`, `entry`, `anchor`, `source`). Every
other line is carried through untouched. `parse(text)` then `render(books)` reproduces the file
byte for byte, which `selftest` proves.

Historical: this script reads the single `books.toml` of corpus formats 1 and 2, which format 3
removed (phynics/cast-iron#425). Run it on a checkout of commit c8aa0bc33 (tag v0.1.35), the
last format 2 commit.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

HEADER = re.compile(r"^\[\[books((?:\.chapters)?(?:\.children)*)\]\]\s*$")
STRING = re.compile(r'^(title|entry|anchor|source)\s*=\s*"((?:[^"\\]|\\.)*)"\s*$')


@dataclass
class Node:
    """One `[[books.chapters...]]` table and the nodes beneath it."""

    header: str
    lines: list[str]  # the lines after the header, up to the next header (a trailing blank line included)
    children: list["Node"] = field(default_factory=list)

    def get(self, key: str) -> str | None:
        for line in self.lines:
            m = STRING.match(line)
            if m and m.group(1) == key:
                return m.group(2)
        return None

    @property
    def title(self) -> str:
        return self.get("title") or ""

    @property
    def entry(self) -> str | None:
        return self.get("entry")

    def drop_keys(self, *keys: str) -> None:
        self.lines = [l for l in self.lines if not ((m := STRING.match(l)) and m.group(1) in keys)]

    def set_entry(self, entry: str) -> None:
        """Set `entry`, keeping it right after `title` as the writer does."""
        self.drop_keys("entry")
        for i, line in enumerate(self.lines):
            m = STRING.match(line)
            if m and m.group(1) == "title":
                self.lines.insert(i + 1, f'entry = "{entry}"\n')
                return
        raise ValueError("node has no title")

    def walk(self):
        yield self
        for child in self.children:
            yield from child.walk()


@dataclass
class Book:
    node: Node  # the `[[books]]` table; its children are the chapters

    @property
    def source(self) -> str:
        return self.node.get("source") or ""


def parse(text: str) -> list[Book]:
    books: list[Book] = []
    stack: list[tuple[int, Node]] = []  # (depth, node); the `[[books]]` table is depth 0
    for line in text.splitlines(keepends=True):
        m = HEADER.match(line)
        if m:
            suffix = m.group(1)
            depth = 0 if suffix == "" else 1 + suffix.count(".children")
            node = Node(header=line, lines=[])
            while stack and stack[-1][0] >= depth:
                stack.pop()
            if depth == 0:
                books.append(Book(node))
            else:
                stack[-1][1].children.append(node)
            stack.append((depth, node))
        else:
            if not stack:
                raise ValueError(f"line before the first [[books]] table: {line!r}")
            stack[-1][1].lines.append(line)
    return books


def render(books: list[Book]) -> str:
    out: list[str] = []

    def emit(node: Node) -> None:
        out.append(node.header)
        out.extend(node.lines)
        for child in node.children:
            emit(child)

    for book in books:
        emit(book.node)
    return "".join(out)


def fix_headers(books: list[Book]) -> None:
    """Rewrite each node's header to match its depth (after a node moved)."""

    def go(node: Node, depth: int) -> None:
        node.header = "[[books]]\n" if depth == 0 else "[[books.chapters" + ".children" * (depth - 1) + "]]\n"
        for child in node.children:
            go(child, depth + 1)

    for book in books:
        go(book.node, 0)


def ensure_blank_after(node: Node) -> None:
    """Every table but the file's last ends with one blank line."""
    if node.lines and node.lines[-1].strip() != "":
        node.lines.append("\n")


def remove_placements(book: Book, drop: set[str]) -> int:
    """Remove each node whose `entry` is in `drop`.

    A node that still has children keeps its title and children and loses `entry`. A node left with
    nothing (no children) goes. A chapter whose children all went also goes, recursively. Returns
    the number of entry nodes removed.
    """
    removed = 0

    def go(node: Node) -> bool:
        """Return True when the node stays."""
        nonlocal removed
        had_children = bool(node.children)
        node.children = [c for c in node.children if go(c)]
        entry = node.entry
        if entry is not None and entry in drop:
            removed += 1
            if node.children:
                node.drop_keys("entry")
                return True
            return False
        if had_children and not node.children and entry is None:
            return False  # a group whose every child went
        return True

    book.node.children = [c for c in book.node.children if go(c)]
    return removed


def selftest(text: str) -> None:
    assert render(parse(text)) == text, "books.toml does not round-trip"
