#!/usr/bin/env python3
"""Apply the mechanical fixes of `placement-audit.py` to a COPY of the corpus (issue #420).

    python3 scripts/placement-audit-simulate.py <corpus-copy-dir> <violations.json>

Never run it on a checkout you want to keep: it rewrites `books.toml` and entry files in place.
It exists to prove, with the real compiler, what the fixes do before they are made for real.

  group a: add the book to the entry's `source_ids` (one-line list)
  group b: remove the placement (the node keeps its title and children, and loses `entry`)
  group c: delete the phantom book
  group d: left alone (needs a print decision)
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path


def main() -> int:
    root = Path(sys.argv[1])
    data = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
    violations = data["violations"]
    phantoms = {v["book"] for v in violations if v["group"] == "c"}
    drop = {(v["book"], v["entry"]) for v in violations if v["group"] == "b"}

    out: list[str] = []
    book = None
    skipping = False
    removed = 0
    for line in (root / "books.toml").read_text(encoding="utf-8").splitlines(keepends=True):
        if line.startswith("[[books]]"):
            skipping = False
            book = None
        m = re.match(r'source = "([^"]+)"', line)
        if m and line.startswith("source = ") and not line.startswith("[[") and book is None:
            book = m.group(1)
            if book in phantoms:
                skipping = True
                # remove the `[[books]]` line that was already written
                while out and not out[-1].startswith("[[books]]"):
                    out.pop()
                if out:
                    out.pop()
        if skipping:
            continue
        m = re.match(r'entry = "([^"]+)"', line)
        if m and (book, m.group(1)) in drop:
            removed += 1
            continue
        out.append(line)
    (root / "books.toml").write_text("".join(out), encoding="utf-8")

    added = 0
    for v in violations:
        if v["group"] != "a":
            continue
        path = root / "entries" / (v["entry"].removeprefix("ref/") + ".md")
        text = path.read_text(encoding="utf-8")
        new = re.sub(r"^(source_ids = \[.*?)\]$", lambda m: f'{m.group(1)}, "{v["book"]}"]', text, count=1, flags=re.M)
        assert new != text, path
        path.write_text(new, encoding="utf-8")
        added += 1
    print(f"dropped {len(phantoms)} phantom books, removed {removed} placements, edited {added} source_ids")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
