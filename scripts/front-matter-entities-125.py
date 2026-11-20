#!/usr/bin/env python3
"""Replace HTML entity references in front-matter values (cast-iron-data#125).

The upstream import left well-formed references such as ``&mdash;``, ``&times;``
and ``&dagger;`` in TOML front-matter strings. The typed field then holds the
literal six characters ``&mdash;``. This script rewrites them under ``entries/``:

* a ``weight`` that is exactly ``&mdash;`` means "no weight". The script deletes
  the line, so the compiled typed field is empty;
* every other reference becomes the plain Unicode character the entity names
  (``&times;`` -> ``×``, ``&dagger;`` -> ``†``, ``&mdash;`` -> ``—``). A ``"`` or
  ``\\`` result is written escaped, as TOML needs.

Only the front matter (from the opening ``+++`` to the closing ``+++``) changes.
The body is never read for entities. The ``id`` line is never changed. A name the
script does not know, or a reference to a control character, is listed and left.

Usage, from the root of the corpus:

    python3 scripts/front-matter-entities-125.py           # survey, writes nothing
    python3 scripts/front-matter-entities-125.py --write   # apply

The script is idempotent: a second ``--write`` finds nothing.
"""
import collections
import html
import pathlib
import re
import sys

ENTITY = re.compile(r"&(#[0-9]+|#[xX][0-9a-fA-F]+|[A-Za-z][A-Za-z0-9]*);")
# Fields where an entity that is the whole value means "none": the key is dropped.
NONE_FIELDS = {"weight": {"&mdash;"}}
KEY = re.compile(r"^([a-z_]+) = ")


def toml_char(ch):
    if ch == '"':
        return '\\"'
    if ch == "\\":
        return "\\\\"
    return ch


def process(path, counts, unknown):
    text = path.read_text(encoding="utf-8")
    if not text.startswith("+++\n"):
        return None
    end = text.find("\n+++\n", 4)
    if end < 0:
        return None
    head, rest = text[:end], text[end:]
    out = []
    changed = False
    for line in head.split("\n"):
        key = KEY.match(line)
        name = key.group(1) if key else "(inline table)"
        if key and key.group(1) == "id":
            out.append(line)
            continue
        if not ENTITY.search(line):
            out.append(line)
            continue
        if key:
            value = line[key.end():]
            if value.startswith('"') and value.endswith('"') and value[1:-1] in NONE_FIELDS.get(name, ()):
                counts[(name, value[1:-1], "removed (no value)")] += 1
                changed = True
                continue

        def sub(m):
            ref = m.group(0)
            ch = html.unescape(ref)
            if ch == ref or (len(ch) == 1 and (ord(ch) < 32 or ord(ch) == 127)):
                unknown.append((str(path), ref))
                return ref
            counts[(name, ref, "replaced by " + ch)] += 1
            return "".join(toml_char(c) for c in ch)

        new = ENTITY.sub(sub, line)
        changed = changed or new != line
        out.append(new)
    return ("\n".join(out) + rest) if changed else None


def main():
    write = "--write" in sys.argv[1:]
    counts = collections.Counter()
    unknown = []
    files = 0
    for path in sorted(pathlib.Path("entries").rglob("*.md")):
        new = process(path, counts, unknown)
        if new is not None:
            files += 1
            if write:
                path.write_text(new, encoding="utf-8")
    verb = "changed" if write else "would change"
    print(f"{verb} {files} files")
    for (field, ref, what), n in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0])):
        print(f"{n:5d}  {field:16s} {ref:10s} {what}")
    print(f"{sum(counts.values()):5d}  total")
    for path, ref in unknown:
        print(f"unknown  {path}  {ref}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
