#!/usr/bin/env python3
"""Replace the broken HTML-entity fragments the upstream import left in entries.

The import cut the ``;`` off character references, or turned it into ``&``. So
``&quot;help.&quot;`` reads ``&quot&help.&quot&`` and ``&times;2`` reads
``&times&2``. A client shows these as text. This script finds them under
``entries/`` and, with ``--write``, replaces each with the intended character.

A fragment is ``&name`` or ``&name&`` where ``name`` is a known HTML entity name
or a numeric reference (``&#39``). A well-formed ``&name;`` is not a fragment:
the script counts it in the survey and never changes it.

The script keeps these things unchanged:

* a bare ``&`` in prose, such as ``Swords & Sorcery`` (no entity name follows);
* a ``&`` followed by a name that is not a known entity (``&Q``, ``&Next1&``);
  the survey lists these under "unknown";
* anything inside a fenced code block, an inline code span, a link target or a
  bare URL;
* ``id``, ``aliases`` and ``source`` lines of the front matter, and body rows
  that start with ``**source:**``;
* a fragment that could be read two ways: ``&quot&times&`` (the closing ``&``
  could start the next entity). The script lists it as ambiguous.

Quotes become plain ASCII quotes, because that is the corpus convention
(457,000 ASCII ``"`` against 155 curly ones, all in verbatim ``carried/``
text). Other characters use the Unicode character the corpus already uses
(``×``, ``—``, ``†``, ``°``).

Inside the TOML front matter a replaced ``"`` is written ``\\"``. Before it
writes a file, the script parses the old and the new front matter and checks
that every string differs by exactly the replacements it made. A file that
fails the check is left unchanged and listed.

Usage:

    python3 scripts/fix-entity-fragments.py [--write] [--skip-list FILE] [DIR]

Without ``--write`` the script only surveys. ``DIR`` defaults to the repository
root. ``--skip-list`` names a file with one repository-relative path per line;
the script leaves those files alone and lists them. The script is idempotent:
on a corpus without fragments it changes no file. The exit code is 0 unless an
argument is wrong or a verification fails.
"""

from __future__ import annotations

import argparse
import re
import sys
import tomllib
from collections import Counter
from pathlib import Path

# Replacement for each known entity name. Quotes are plain ASCII.
ENTITIES: dict[str, str] = {
    "quot": '"', "amp": "&", "lt": "<", "gt": ">", "apos": "'",
    "nbsp": " ",
    "lsquo": "'", "rsquo": "'", "sbquo": "'",
    "ldquo": '"', "rdquo": '"', "bdquo": '"',
    "ndash": "–", "mdash": "—", "hellip": "…",
    "times": "×", "divide": "÷", "plusmn": "±",
    "dagger": "†", "Dagger": "‡", "deg": "°",
    "frac12": "½", "frac14": "¼", "frac34": "¾",
    "middot": "·", "bull": "•", "sect": "§", "para": "¶",
    "copy": "©", "reg": "®", "trade": "™",
    "cent": "¢", "pound": "£", "euro": "€",
    "laquo": "«", "raquo": "»",
    "eacute": "é", "Eacute": "É", "egrave": "è",
    "ecirc": "ê", "euml": "ë",
    "aacute": "á", "agrave": "à", "acirc": "â",
    "auml": "ä", "aring": "å", "aelig": "æ", "AElig": "Æ",
    "iacute": "í", "icirc": "î", "iuml": "ï",
    "oacute": "ó", "ocirc": "ô", "ouml": "ö", "oslash": "ø",
    "uacute": "ú", "ucirc": "û", "uuml": "ü", "Uuml": "Ü",
    "ntilde": "ñ", "ccedil": "ç", "szlig": "ß",
}

# Numeric references that name a typographic quote map to the ASCII quote.
NUMERIC_QUOTES = {
    0x2018: "'", 0x2019: "'", 0x201A: "'", 0x201C: '"', 0x201D: '"', 0x201E: '"',
}

# ``&name`` or ``&name&`` or ``&name;``. The name is greedy, so ``&quotes``
# never matches ``&quot``.
REF = re.compile(r"&(?P<name>#[xX][0-9A-Fa-f]+|#[0-9]+|[A-Za-z][A-Za-z0-9]*)(?P<end>[&;]?)")

# Ranges to leave alone inside one line.
CODE_SPAN = re.compile(r"(`+)(.+?)\1")
LINK_TARGET = re.compile(r"\]\([^)]*\)")
BARE_URL = re.compile(r"https?://[^\s)>\]\"']+")

FENCE = re.compile(r"^\s*(```|~~~)")
FRONT_MATTER_FENCE = "+++"
PROTECTED_KEYS = {"id", "aliases", "source", "sources", "path", "url"}
# Front matter lines whose value is an identifier or a citation.
PROTECTED_KEY = re.compile(r"^\s*(" + "|".join(sorted(PROTECTED_KEYS)) + r")\s*=")
PROTECTED_BODY_ROW = re.compile(r"^\*\*source:\*\*")


def decode(name: str) -> str | None:
    """Return the replacement character for an entity name, or ``None``."""
    if name.startswith("#"):
        digits = name[1:]
        code = int(digits[1:], 16) if digits[:1] in ("x", "X") else int(digits)
        if code == 0xA0:
            return " "
        if code in NUMERIC_QUOTES:
            return NUMERIC_QUOTES[code]
        if code in (0x22, 0x27) or (0xA0 < code < 0x2FFF and chr(code).isprintable()):
            return chr(code)
        return None
    return ENTITIES.get(name)


def masked_ranges(line: str) -> list[tuple[int, int]]:
    ranges: list[tuple[int, int]] = []
    for pattern in (CODE_SPAN, LINK_TARGET, BARE_URL):
        ranges.extend(m.span() for m in pattern.finditer(line))
    return ranges


def closing_amp_opens_next(line: str, match: re.Match) -> bool:
    """True when the closing ``&`` of ``&a&`` could open a second entity ``&b&``."""
    follow = REF.match(line, match.end() - 1)
    return bool(follow and follow.group("end") == "&" and decode(follow.group("name")) is not None)


class Hit:
    """One reference found in a line."""

    __slots__ = ("start", "end", "kind", "status", "new")

    def __init__(self, start: int, end: int, kind: str, status: str, new: str):
        self.start = start
        self.end = end
        self.kind = kind      # e.g. "&quot&" or "&quot"
        self.status = status  # "fix", "ambiguous", "unknown", "wellformed"
        self.new = new


def scan_line(line: str, in_front_matter: bool) -> list[Hit]:
    hits: list[Hit] = []
    ranges = masked_ranges(line)
    for m in REF.finditer(line):
        if any(a <= m.start() < b for a, b in ranges):
            continue
        name, end = m.group("name"), m.group("end")
        kind = f"&{name}{end}"
        if end == ";":
            hits.append(Hit(m.start(), m.end(), kind, "wellformed", ""))
            continue
        replacement = decode(name)
        if replacement is None:
            hits.append(Hit(m.start(), m.end(), kind, "unknown", ""))
            continue
        if end == "&" and closing_amp_opens_next(line, m):
            hits.append(Hit(m.start(), m.end(), kind, "ambiguous", ""))
            continue
        if in_front_matter and replacement == '"':
            replacement = '\\"'
        hits.append(Hit(m.start(), m.end(), kind, "fix", replacement))
    return hits


def split_file(text: str) -> tuple[list[str], int]:
    """Return the lines (with endings) and the index of the first body line."""
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].rstrip("\r\n") != FRONT_MATTER_FENCE:
        return lines, 0
    for i in range(1, len(lines)):
        if lines[i].rstrip("\r\n") == FRONT_MATTER_FENCE:
            return lines, i + 1
    return lines, 0


def process(text: str) -> tuple[str, list[tuple[int, Hit]]]:
    """Return the fixed text and every hit with its line number (1-based)."""
    lines, body_start = split_file(text)
    out: list[str] = []
    found: list[tuple[int, Hit]] = []
    fenced = False
    for index, line in enumerate(lines):
        in_front = index < body_start
        if in_front:
            protected = bool(PROTECTED_KEY.match(line))
        else:
            if FENCE.match(line):
                fenced = not fenced
                out.append(line)
                continue
            protected = fenced or bool(PROTECTED_BODY_ROW.match(line))
        if protected or "&" not in line:
            out.append(line)
            continue
        hits = scan_line(line, in_front)
        found.extend((index + 1, hit) for hit in hits)
        pieces: list[str] = []
        cursor = 0
        for hit in hits:
            if hit.status != "fix":
                continue
            pieces.append(line[cursor:hit.start])
            pieces.append(hit.new)
            cursor = hit.end
        pieces.append(line[cursor:])
        out.append("".join(pieces))
    return "".join(out), found


def replace_strings(value, fn):
    """Return ``value`` with ``fn`` applied to every string inside it."""
    if isinstance(value, str):
        return fn(value)
    if isinstance(value, list):
        return [replace_strings(v, fn) for v in value]
    if isinstance(value, dict):
        return {k: replace_strings(v, fn) for k, v in value.items()}
    return value


def front_matter_text(text: str) -> str | None:
    lines, body_start = split_file(text)
    if body_start == 0:
        return None
    return "".join(lines[1:body_start - 1])


def expected_string(s: str) -> str:
    """The string after the same replacements, with plain (unescaped) quotes."""
    def sub(m: re.Match) -> str:
        name, end = m.group("name"), m.group("end")
        replacement = decode(name)
        if end == ";" or replacement is None:
            return m.group(0)
        if end == "&" and closing_amp_opens_next(s, m):
            return m.group(0)
        return replacement
    return REF.sub(sub, s)


def verify_front_matter(old: str, new: str) -> str | None:
    """Return an error text, or ``None`` when the new front matter is right.

    The new front matter must parse, and each of its strings must equal the old
    string after the same replacements.
    """
    old_fm, new_fm = front_matter_text(old), front_matter_text(new)
    if old_fm is None or new_fm is None:
        return None if old_fm == new_fm else "front matter appeared or vanished"
    try:
        old_data = tomllib.loads(old_fm)
        new_data = tomllib.loads(new_fm)
    except tomllib.TOMLDecodeError as err:
        return f"front matter does not parse: {err}"
    expected = {
        k: (v if k in PROTECTED_KEYS else replace_strings(v, expected_string))
        for k, v in old_data.items()
    }
    if expected != new_data:
        return "front matter strings differ from the expected replacements"
    return None


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="Replace broken HTML-entity fragments in corpus entries.")
    ap.add_argument("dir", nargs="?", default=".", help="corpus root (default: .)")
    ap.add_argument("--write", action="store_true", help="rewrite the files (default: survey only)")
    ap.add_argument("--skip-list", help="file with one repository-relative path per line to leave alone")
    args = ap.parse_args(argv)

    root = Path(args.dir)
    entries = root / "entries"
    if not entries.is_dir():
        print(f"{entries}: not a directory", file=sys.stderr)
        return 2
    skipped: set[str] = set()
    if args.skip_list:
        skipped = {ln.strip() for ln in Path(args.skip_list).read_text().splitlines() if ln.strip()}

    fix_kinds: Counter[str] = Counter()
    other: dict[str, Counter[str]] = {"wellformed": Counter(), "unknown": Counter(), "ambiguous": Counter()}
    files_with_fix: set[str] = set()
    skipped_with_fix: list[tuple[str, int]] = []
    ambiguous_cases: list[tuple[str, int, str]] = []
    failed: list[tuple[str, str]] = []
    changed: list[str] = []

    for path in sorted(entries.rglob("*.md")):
        rel = path.relative_to(root).as_posix()
        with open(path, encoding="utf-8", newline="") as fh:
            text = fh.read()
        if "&" not in text:
            continue
        new_text, found = process(text)
        source_lines = text.splitlines()
        for line_no, hit in found:
            if hit.status == "ambiguous":
                ambiguous_cases.append((rel, line_no, source_lines[line_no - 1].strip()[:140]))
            if hit.status != "fix":
                other[hit.status][hit.kind] += 1
        fixes = [h for _, h in found if h.status == "fix"]
        if not fixes:
            continue
        if rel in skipped:
            skipped_with_fix.append((rel, len(fixes)))
            continue
        err = verify_front_matter(text, new_text)
        if err:
            failed.append((rel, err))
            continue
        for h in fixes:
            fix_kinds[h.kind] += 1
        files_with_fix.add(rel)
        if args.write and new_text != text:
            with open(path, "w", encoding="utf-8", newline="") as fh:
                fh.write(new_text)
            changed.append(rel)

    print(f"{'Fragment kind':<22} {'count':>5}   replacement")
    for kind, count in sorted(fix_kinds.items(), key=lambda kv: (-kv[1], kv[0])):
        shown = decode(kind.strip("&"))
        print(f"{kind:<22} {count:>5}   {shown!r}")
    print(f"{'total':<22} {sum(fix_kinds.values()):>5}   in {len(files_with_fix)} files")

    for title, key in (
        ("Well-formed references (not changed)", "wellformed"),
        ("Unknown & names (not changed)", "unknown"),
        ("Ambiguous (not changed)", "ambiguous"),
    ):
        if other[key]:
            print(f"\n{title}:")
            for kind, count in sorted(other[key].items(), key=lambda kv: (-kv[1], kv[0])):
                print(f"  {kind:<22} {count:>5}")
    for rel, line_no, snippet in ambiguous_cases:
        print(f"  ambiguous: {rel}:{line_no}: {snippet}")
    if skipped_with_fix:
        print("\nSkipped files with fragments (--skip-list):")
        for rel, count in skipped_with_fix:
            print(f"  {rel}: {count}")
    if failed:
        print("\nVerification failed, files left unchanged:")
        for rel, err in failed:
            print(f"  {rel}: {err}")
    if args.write:
        print(f"\nRewrote {len(changed)} files.")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
