#!/usr/bin/env python3
"""Remove stray ``p!`` import markers from the entry bodies of a corpus.

The upstream import left a literal ``p!`` where a paragraph or list break had
been. It now reads as text, as in ``At 6th level: p!These bonuses +2.``  This
script removes only those markers; it never rewrites the sentence around one.

A ``p!`` is a marker when nothing word-like precedes it and a capital letter
follows it. That is the shape the import produced: a marker sits at the start
of a sentence or of a block. Real text keeps its ``p!``: the sequence inside a
word, as in ``Help!`` or ``35,150 gp!``, is preceded by a letter, so the script
leaves it alone and lists it in its report.

Usage:

    python3 scripts/strip-p-markers.py [DIR]

``DIR`` defaults to the repository root. The script is idempotent: on a corpus
that holds no marker it changes no file and only prints the real-text triggers.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

# ``p!`` with no word character before it and a capital letter after it. The
# lookbehind also accepts the start of a line, which is a block start.
MARKER = re.compile(r"(?<![\w])p!(?=[A-Z])")
ANY_P = re.compile(r"p!")

FRONT_MATTER_OPEN = "+++\n"


def split_front_matter(text: str) -> tuple[str, str]:
    """Return ``(front_matter, body)``, or ``("", text)`` without front matter."""
    if not text.startswith(FRONT_MATTER_OPEN):
        return "", text
    end = text.find("\n+++\n", len(FRONT_MATTER_OPEN))
    if end < 0:
        return "", text
    end += len("\n+++\n")
    return text[:end], text[end:]


def main(argv: list[str]) -> int:
    root = Path(argv[1]) if len(argv) > 1 else Path(".")
    entries = root / "entries"
    if not entries.is_dir():
        print(f"{entries}: not a directory", file=sys.stderr)
        return 2

    removed_total = 0
    exceptions: list[tuple[Path, int, str]] = []

    for path in sorted(entries.rglob("*.md")):
        text = path.read_text(encoding="utf-8")
        front_matter, body = split_front_matter(text)
        removed = len(MARKER.findall(body))
        if removed:
            body = MARKER.sub("", body)
            path.write_text(front_matter + body, encoding="utf-8")
            removed_total += removed
        offset = front_matter.count("\n")
        for number, line in enumerate(body.splitlines(), offset + 1):
            if ANY_P.search(line):
                exceptions.append((path.relative_to(root), number, line.strip()))

    for file, number, line in exceptions:
        print(f"{file}:{number}: real text, left alone: {line}")
    print(f"removed {removed_total} marker(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
