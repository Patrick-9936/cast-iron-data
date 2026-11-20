#!/usr/bin/env python3
"""Replace the metamagic and summon shorthand the upstream import left in spell lists.

The import wrote metamagic and summon entries of monster spell-like ability
lists as ``&`` markers. The books print them as words. This script finds the
markers under ``entries/`` and, with ``--write``, replaces each with the print
wording:

========================  ==============================================
Marker                    Replacement
========================  ==============================================
``&Q spell``              ``quickened spell``
``&EM spell``             ``empowered spell``
``&EX spell``             ``extended spell``
``&S level N; ...``       ``summon (level N, ...)``
``&maximized`` and the    the plain word (``maximized``, ``reach``,
other five prefixes       ``heightened``, ``widened``, ``merciful``,
                          ``scarring``)
========================  ==============================================

How the summon item is placed
-----------------------------

The import wrote the commas that the book prints inside a summon item as
``;``, so that the item stays one comma-separated entry of the list. The book
prints ``summon (level 4, 1d4+1 adhukaits, 45%, or 1 aghasura, 20%)`` and the
corpus has ``&S level 4; 1d4+1 [adhukaits](...); 45%; or 1 aghasura; 20%``.
The script therefore reads the item from the end of the marker up to the first
comma that is not inside ``[]`` or ``()``, or up to the end of the list item
(the item can wrap onto indented continuation lines). Inside the item every
top-level ``;`` becomes ``,``. It puts ``summon (level N,`` in front and ``)``
after the last character of the item, and keeps links, DCs and footnote markers
(``^M^``, ``^D^``) unchanged. A footnote marker at the end of the item stays
after the closing parenthesis.

One entry prints a subject after the verb: the Bestiary 3 entry of the thriae seer
reads ``summon bees (level 5, ...)``, and the import dropped ``bees`` together with the
marker. ``SUMMON_SUBJECTS`` names the entry file and its subject, so the script writes
``summon bees (level 5, ...)`` there. Add an entry to the table only after you checked
the print.

Three header forms occur: ``&S level N;``, ``&S, level N;`` and ``&S CL 3rd;``
(the last one keeps its words: ``summon (CL 3rd, ...)``). A summon that the
import already wrote in parentheses, ``&S (level 3; 4 imps; 35%)``, keeps that
one pair of parentheses.

The script leaves a marker unchanged and lists it as "unplaced" when it cannot
place it with certainty: a marker in the front matter, a summon with no
recognised header, an empty item, unbalanced brackets, a character reference
inside the item, an item that ends with ``;``, or text after a parenthesised
summon.

Usage:

    python3 scripts/fix-spell-list-markers.py [--write] [DIR]
    python3 scripts/fix-spell-list-markers.py --self-test

Without ``--write`` the script only surveys: it prints, per marker, how many
it found, would replace and cannot place, and lists every unplaced case. ``DIR``
defaults to the repository root. The script writes each changed file through a
temporary file and an atomic rename, and it is idempotent: on a corpus without
markers it changes no file. Before it writes a file it checks that the front
matter is unchanged, that exactly the unplaced markers remain, and that a
second pass would change nothing; a file that fails is left unchanged and
listed. The exit code is 0 unless an argument is wrong or a verification fails.
"""

from __future__ import annotations

import argparse
import os
import re
import sys
import tempfile
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

METAMAGIC = {"Q": "quickened", "EM": "empowered", "EX": "extended"}
PLAIN_WORDS = ("maximized", "reach", "heightened", "widened", "merciful", "scarring")

# One pattern finds every marker. A ``&`` after a word character or another ``&`` does
# not start a marker (``AT&T``, the end of a broken entity such as ``&quot&Q``).
MARKER = re.compile(
    r"(?<![\w&])&(?:(?P<meta>Q|EM|EX)(?!\w)|(?P<summon>S)(?!\w)"
    r"|(?P<plain>" + "|".join(PLAIN_WORDS) + r")(?!\w))"
)

# The header of a summon item after ``&S``: ``level 4;``, ``, level 9;``, ``CL 3rd;``,
# with the import's own opening parenthesis in one case.
SUMMON_HEADER = re.compile(
    r"[ \t]*,?\s*(?P<open>\()?\s*"
    r"(?P<head>level\s+\d+|CL\s+\d+(?:st|nd|rd|th))\s*[;,]\s*"
)

TRAILING_NOTES = re.compile(r"(?:\^[A-Za-z]+\^)+\Z")
ENTITY = re.compile(r"&#?\w+;")

# Entries whose book prints a word between ``summon`` and the parenthesis (checked against
# the print: Bestiary 3, thriae seer). Keys are paths relative to the repository root.
SUMMON_SUBJECTS = {"entries/monster/thriae-thriae-seer.md": "bees"}

KINDS = ("&Q", "&EM", "&EX", "&S", "plain")


def kind_of(m: re.Match[str]) -> str:
    if m.group("meta"):
        return "&" + m.group("meta")
    if m.group("summon"):
        return "&S"
    return "plain"


@dataclass
class Unplaced:
    line: int
    kind: str
    reason: str
    context: str


@dataclass
class Result:
    text: str
    found: Counter
    replaced: Counter
    unplaced: list[Unplaced]


def front_matter_end(text: str) -> int:
    """Offset where the body starts; 0 when the file has no TOML front matter."""
    if not text.startswith("+++\n"):
        return 0
    end = text.find("\n+++\n", 3)
    return 0 if end < 0 else end + len("\n+++\n")


def is_item_end(text: str, i: int) -> bool:
    """A newline ends a list item unless an indented continuation line follows."""
    return text[i] == "\n" and (i + 1 >= len(text) or text[i + 1] != " ")


def scan_item_end(text: str, start: int) -> tuple[int, str | None]:
    """End offset of a summon item that begins at ``start``.

    The item ends at the first top-level comma or at the end of the list item.
    Returns ``(end, None)``, or ``(start, reason)`` when brackets do not balance.
    """
    depth = 0
    i = start
    n = len(text)
    while i < n:
        c = text[i]
        if c == "\\":
            i += 2
            continue
        if c in "[(":
            depth += 1
        elif c in "])":
            depth -= 1
            if depth < 0:
                return start, "unbalanced closing bracket in the item"
        elif c == "," and depth == 0:
            break
        elif is_item_end(text, i):
            break
        i += 1
    i = min(i, n)
    if depth != 0:
        return start, "unbalanced opening bracket in the item"
    return i, None


def convert_semicolons(item: str) -> str:
    """Replace each top-level ``;`` of the item with ``,``."""
    out: list[str] = []
    depth = 0
    i = 0
    while i < len(item):
        c = item[i]
        if c == "\\" and i + 1 < len(item):
            out.append(item[i : i + 2])
            i += 2
            continue
        if c in "[(":
            depth += 1
        elif c in "])":
            depth -= 1
        out.append("," if c == ";" and depth == 0 else c)
        i += 1
    return "".join(out)


def build_summon(head: str, body: str, subject: str) -> tuple[str, str] | str:
    """``(replacement, trailing whitespace)`` for an item body, or a reason."""
    trimmed = body.rstrip()
    trailing = body[len(trimmed) :]
    if not trimmed:
        return "empty summon item"
    if ENTITY.search(trimmed):
        return "character reference inside the item"
    notes = TRAILING_NOTES.search(trimmed)
    foot = ""
    if notes:
        foot = notes.group(0)
        trimmed = trimmed[: notes.start()].rstrip()
        if not trimmed:
            return "empty summon item"
    if trimmed.endswith(";"):
        return "item ends with a semicolon"
    return f"summon{subject} ({head}, {convert_semicolons(trimmed)}){foot}", trailing


def place_summon(text: str, start: int, subject: str) -> tuple[int, str] | str:
    """Replacement for the summon whose marker ended at ``start``.

    Returns ``(end_offset, replacement_text)`` or a reason string.
    """
    header = SUMMON_HEADER.match(text, start)
    if not header:
        return "no recognised `level N;` header after the marker"
    head = re.sub(r"\s+", " ", header.group("head"))
    body_start = header.end()
    if header.group("open"):
        # The import already parenthesised the item: find its closing parenthesis.
        depth = 1
        i = body_start
        while i < len(text) and depth:
            c = text[i]
            if c == "\\":
                i += 2
                continue
            if c in "[(":
                depth += 1
            elif c in "])":
                depth -= 1
            elif is_item_end(text, i):
                break
            i += 1
        if depth:
            return "parenthesis opened after the marker is never closed"
        if i < len(text) and text[i] not in ",\n ":
            return "text directly after a parenthesised summon"
        built = build_summon(head, text[body_start : i - 1], subject)
        if isinstance(built, str):
            return built
        return i, built[0]
    item_end, reason = scan_item_end(text, body_start)
    if reason:
        return reason
    built = build_summon(head, text[body_start:item_end], subject)
    if isinstance(built, str):
        return built
    replacement, trailing = built
    return item_end, replacement + trailing


def process(text: str, subject: str = "") -> Result:
    """Replace the markers in a file's text; leave what cannot be placed."""
    found: Counter = Counter()
    replaced: Counter = Counter()
    unplaced: list[Unplaced] = []
    body_start = front_matter_end(text)
    pieces: list[str] = []
    pos = 0

    def line_of(offset: int) -> int:
        return text.count("\n", 0, offset) + 1

    def context(offset: int) -> str:
        s = text.rfind("\n", 0, offset) + 1
        e = text.find("\n", offset)
        e = len(text) if e < 0 else e
        return text[s:e].strip()[:160]

    for m in MARKER.finditer(text):
        if m.start() < pos:
            continue  # inside a summon item that was already placed
        kind = kind_of(m)
        found[kind] += 1
        if m.start() < body_start:
            unplaced.append(Unplaced(line_of(m.start()), kind, "marker in the front matter", context(m.start())))
            continue
        if kind == "&S":
            result = place_summon(text, m.end(), subject)
            if isinstance(result, str):
                unplaced.append(Unplaced(line_of(m.start()), kind, result, context(m.start())))
                continue
            end, replacement = result
            pieces.append(text[pos : m.start()])
            pieces.append(replacement)
            pos = end
        else:
            word = m.group("plain") or METAMAGIC[m.group("meta")]
            pieces.append(text[pos : m.start()])
            pieces.append(word)
            pos = m.end()
        replaced[kind] += 1
    pieces.append(text[pos:])
    return Result("".join(pieces), found, replaced, unplaced)


def verify(old: str, new: str, res: Result, subject: str = "") -> str | None:
    """Check a rewritten file; return a reason when it must not be written."""
    start = front_matter_end(old)
    if front_matter_end(new) != start or old[:start] != new[:start]:
        return "front matter changed"
    # Every marker that was not placed is still there, and no other marker is.
    left = len(MARKER.findall(new))
    if left != len(res.unplaced):
        return f"{left} markers left, {len(res.unplaced)} expected"
    if process(new, subject).text != new:
        return "a second pass changes the text"
    return None


def write_atomic(path: Path, text: str) -> None:
    mode = path.stat().st_mode & 0o7777
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=path.name + ".", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as f:
            f.write(text)
        os.chmod(tmp, mode)
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def run(root: Path, write: bool) -> int:
    entries = root / "entries"
    if not entries.is_dir():
        print(f"error: {entries} is not a directory", file=sys.stderr)
        return 2
    found: Counter = Counter()
    replaced: Counter = Counter()
    unplaced: list[tuple[str, Unplaced]] = []
    changed: list[Path] = []
    failures: list[str] = []
    for path in sorted(entries.rglob("*.md")):
        old = path.read_bytes().decode("utf-8")
        if "&" not in old:
            continue
        rel = path.relative_to(root).as_posix()
        subject = " " + SUMMON_SUBJECTS[rel] if rel in SUMMON_SUBJECTS else ""
        res = process(old, subject)
        found += res.found
        unplaced += [(rel, u) for u in res.unplaced]
        if res.text == old:
            continue
        reason = verify(old, res.text, res, subject)
        if reason:
            failures.append(f"{rel}: {reason}")
            continue
        replaced += res.replaced
        changed.append(path)
        if write:
            write_atomic(path, res.text)
    verb = "replaced" if write else "would replace"
    print(f"{'kind':8} {'found':>6} {verb:>14} {'unplaced':>9}")
    for kind in KINDS:
        n_unplaced = sum(1 for _, u in unplaced if u.kind == kind)
        print(f"{kind:8} {found[kind]:>6} {replaced[kind]:>14} {n_unplaced:>9}")
    print(f"{'total':8} {sum(found.values()):>6} {sum(replaced.values()):>14} {len(unplaced):>9}")
    print(f"files {'changed' if write else 'to change'}: {len(changed)}")
    if unplaced:
        print("\nunplaced (left unchanged):")
        for rel, u in unplaced:
            print(f"  {rel}:{u.line}: {u.kind}: {u.reason}\n      {u.context}")
    if failures:
        print("\nverification failures (files left unchanged):", file=sys.stderr)
        for f in failures:
            print(f"  {f}", file=sys.stderr)
        return 1
    return 0


PREFIX = '+++\nid = "ref/monster/x"\n+++\n\n**Spell-Like Abilities**\n'


def self_test() -> int:
    cases = [
        # metamagic
        ("- 3/day: &Q holy smite (DC 20)", "- 3/day: quickened holy smite (DC 20)"),
        ("- &EM magic missile, &EX good hope", "- empowered magic missile, extended good hope"),
        ("- 3/day: &Q blade barrier^M^ (DC 27)", "- 3/day: quickened blade barrier^M^ (DC 27)"),
        ("- &Q [holy smite](ref/spell/holy-smite)", "- quickened [holy smite](ref/spell/holy-smite)"),
        ("- &maximized cone of cold, &reach ghoul touch", "- maximized cone of cold, reach ghoul touch"),
        ("- &heightened a, &widened b, &merciful c, &scarring d", "- heightened a, widened b, merciful c, scarring d"),
        # summon: simple, linked, trailing spell, wrap, header forms
        ("- 1/day: &S level 4; 1 [silvanshee](ref/monster/s) 35%",
         "- 1/day: summon (level 4, 1 [silvanshee](ref/monster/s) 35%)"),
        ("- &S level 4; 2 [p](ref/monster/p) 50%, symbol of pain (DC 24)",
         "- summon (level 4, 2 [p](ref/monster/p) 50%), symbol of pain (DC 24)"),
        ("- a, &S level 6; 1d3\n  [upasundas](ref/monster/u) 50%\n\nnext",
         "- a, summon (level 6, 1d3\n  [upasundas](ref/monster/u) 50%)\n\nnext"),
        ("- a, &S level 9; see\n  below, wish", "- a, summon (level 9, see\n  below), wish"),
        ("- &S level 4; 1d4+1 [a](ref/monster/a); 45%; or 1 aghasura; 20%\n- next",
         "- summon (level 4, 1d4+1 [a](ref/monster/a), 45%, or 1 aghasura, 20%)\n- next"),
        ("- x, &S, level 9; 2d4 wendigos 100%", "- x, summon (level 9, 2d4 wendigos 100%)"),
        ("- 1/day: &S CL 3rd; 1 magaav 40%", "- 1/day: summon (CL 3rd, 1 magaav 40%)"),
        ("- x, &S level 3, 1 [shadow demon](ref/monster/d) 50%", "- x, summon (level 3, 1 [shadow demon](ref/monster/d) 50%)"),
        ("- x, &S (level 3; 4 [imps](ref/monster/i); 35%)", "- x, summon (level 3, 4 [imps](ref/monster/i), 35%)"),
        ("- x, &S level\n  4; 1 hezrou 35%", "- x, summon (level 4, 1 hezrou 35%)"),
        ("- x, &S level 9; 1 balor 100%^M^, wish", "- x, summon (level 9, 1 balor 100%)^M^, wish"),
        ("- x, &S level 5; 1d3 bat swarms \\[use the same stats\\]; 1d2 snakes; or 1 wolf",
         "- x, summon (level 5, 1d3 bat swarms \\[use the same stats\\], 1d2 snakes, or 1 wolf)"),
    ]
    failed = 0
    for src, want in cases:
        got = process(PREFIX + src)
        if got.text != PREFIX + want or got.unplaced:
            failed += 1
            print(f"FAIL\n  in:   {src!r}\n  want: {want!r}\n  got:  {got.text[len(PREFIX):]!r}\n  unplaced: {got.unplaced}")
            continue
        again = process(got.text)
        if again.text != got.text or again.found:
            failed += 1
            print(f"FAIL (second run changes the text or finds markers): {src!r}")
    # The subject some books print after the verb.
    got = process(PREFIX + "- x, &S level 5; 1d3 giant queen bees 100%, y", " bees")
    if got.text != PREFIX + "- x, summon bees (level 5, 1d3 giant queen bees 100%), y":
        failed += 1
        print(f"FAIL (subject): {got.text[len(PREFIX):]!r}")
    # Cases that must stay unchanged and be listed.
    unchanged = [
        "- x, &S level; 1 balor 100%",          # no level number
        "- x, &S level 4;",                      # empty item
        "- x, &S level 4; 1 [a](ref/x 50%",      # unbalanced
        "- x, &S level 4; 1 a &mdash; 50%",      # character reference
        "- x, &S level 4; 1 a 50%;",             # ends with a semicolon
        "- x, &S (level 3; 4 imps; 35%)tail",    # text after a parenthesised summon
        "- x, &S see below",                     # no header
    ]
    for src in unchanged:
        got = process(PREFIX + src)
        if got.text != PREFIX + src or len(got.unplaced) != 1:
            failed += 1
            print(f"FAIL (must stay unchanged and be listed): {src!r} -> {got.text[len(PREFIX):]!r} {got.unplaced}")
    # A marker in the front matter is listed and never touched.
    fm = '+++\nid = "ref/monster/x"\ntitle = "&Q odd"\n+++\n\n- &Q holy smite\n'
    got = process(fm)
    if 'title = "&Q odd"' not in got.text or "quickened holy smite" not in got.text or len(got.unplaced) != 1:
        failed += 1
        print("FAIL (front matter)")
    # Words that only contain a marker are not markers.
    keep = "- AT&T, R&Q, &Quick, &reaches, &Sword, &EMBER, &quot&Q x\n"
    got = process(PREFIX + keep)
    if got.text != PREFIX + keep or got.found:
        failed += 1
        print(f"FAIL (not markers): {got.found}")
    total = len(cases) + len(unchanged) + 3
    print("self-test:", "FAILED" if failed else "ok", f"({total} cases)")
    return 1 if failed else 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("dir", nargs="?", help="repository root (default: the parent of scripts/)")
    ap.add_argument("--write", action="store_true", help="apply the replacements")
    ap.add_argument("--self-test", action="store_true", help="run the built-in tests and exit")
    args = ap.parse_args()
    if args.self_test:
        return self_test()
    root = Path(args.dir) if args.dir else Path(__file__).resolve().parent.parent
    return run(root, args.write)


if __name__ == "__main__":
    sys.exit(main())
