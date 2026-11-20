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

A value is decoded to a fixed point, so a double-escaped ``&amp;times;`` ends as
``×`` in the first run. The script is idempotent: a second ``--write`` finds
nothing. ``--self-test`` checks that on a few values.
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

        # Decode to a fixed point, so `&amp;times;` ends as `×` in one run, not two.
        new = line
        while True:
            step = ENTITY.sub(sub, new)
            if step == new:
                break
            new = step
        changed = changed or new != line
        out.append(new)
    return ("\n".join(out) + rest) if changed else None


def self_test():
    """A value converges in one run: a second run changes nothing."""
    import tempfile

    cases = {
        'benefit = "Deal &amp;times;2 damage."': 'benefit = "Deal ×2 damage."',
        'benefit = "a &amp;amp;mdash; b"': 'benefit = "a — b"',
        'benefit = "Swords & Sorcery &quot;x&quot;"': 'benefit = "Swords & Sorcery \\"x\\""',
        'benefit = "&Zzzz; stays"': 'benefit = "&Zzzz; stays"',
        'weight = "&mdash;"': None,
    }
    with tempfile.TemporaryDirectory() as tmp:
        path = pathlib.Path(tmp) / "e.md"
        for before, after in cases.items():
            path.write_text(f'+++\nid = "ref/x"\n{before}\n+++\nbody &mdash;\n', encoding="utf-8")
            first = process(path, collections.Counter(), [])
            expect = f'+++\nid = "ref/x"\n{after}\n+++\nbody &mdash;\n' if after else '+++\nid = "ref/x"\n+++\nbody &mdash;\n'
            if after == before:
                assert first is None, (before, first)
                continue
            assert first == expect, (before, first, expect)
            path.write_text(first, encoding="utf-8")
            assert process(path, collections.Counter(), []) is None, ("not idempotent", before)
    print("self-test ok")


def main():
    if "--self-test" in sys.argv[1:]:
        self_test()
        return 0
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
    for path, ref in sorted(set(unknown)):
        print(f"unknown  {path}  {ref}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
