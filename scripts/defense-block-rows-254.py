#!/usr/bin/env python3
"""Rewrite the defense block of creature entries into labeled rows (cast-iron#254).

Today a creature prints the defense block in the order the import sorted it:

    **Armor class:** 16/13/14      **Fort:** +3     **Hit points:** 6 (1d10+1)
    **Mod:** +2 armor, +2 Dex, +1 shield, +1 size     **Ref:** +2     **Will:** -1

The owner decision of 2026-11-20 labels the rows and puts them in print order:

    **Armor class:** 16
    **Touch:** 13
    **Flat-footed:** 14
    **AC modifiers:** +2 armor, +2 Dex, +1 shield, +1 size      (the old `Mod` row; omitted when absent)
    **Hit points:** 6 (1d10+1)
    **Fort:** +3
    **Ref:** +2
    **Will:** -1
    ... every other defense row (Defensive abilities, Dr, Immune, Resist, Sr, Weaknesses, ...),
        in the order it has now

A defense block is the run of `**Label:**` rows that starts at a `**Armor class:**` row and ends
at the first paragraph that is not such a row (the `**Offense**` line). An entry can hold several
blocks (the elementals print one per size); each is handled alone. The typed `[fields]` (`ac`,
`hp`, `fortitude`, ...) are never touched, so they keep agreeing with the body.

Usage:

    python3 scripts/defense-block-rows-254.py [DIR]            survey: counts by shape, writes nothing
    python3 scripts/defense-block-rows-254.py [DIR] --write    apply to every block it can parse
    python3 scripts/defense-block-rows-254.py --self-test      run the built-in tests

`--only a-c` (or `--only a-c,x`) limits a run to entry files whose name starts with one of the
letters or letter ranges, so the rewrite can land in reviewable batches.

`DIR` defaults to the repository root. The survey and `--write` list every block they leave
unchanged, with the reason. A block is left unchanged when it is already in the new form
(`already`, not an error) or when it cannot be parsed: the `**Armor class:**` value is not
`N/N/N`, a core row (`Hit points`, `Fort`, `Ref`, `Will`) is missing or repeated, or a new label
(`Touch`, `Flat-footed`, `AC modifiers`) is already there. The script is idempotent: a second run
finds every block `already` and writes nothing. Each file is written through a temporary file in
its own directory and renamed over the original, after a check that only the defense block
changed.
"""

from __future__ import annotations

import collections
import os
import re
import sys
import tempfile
import unittest
from pathlib import Path

WRAP_WIDTH = 100  # crates/corpus/src/inline.rs WRAP_WIDTH
FRONT_MATTER_END = "\n+++\n"
ROW_START = re.compile(r"\*\*([^*\n]+?):\*\*")
AC_VALUE = re.compile(r"(-?\d+)/(-?\d+)/(-?\d+)")
CORE = ("Hit points", "Fort", "Ref", "Will")
NEW_LABELS = ("Touch", "Flat-footed", "AC modifiers")


def wrap(text: str, width: int = WRAP_WIDTH) -> list[str]:
    """Greedy wrap at spaces, the algorithm of `wrap` in crates/corpus/src/inline.rs."""
    candidates = [i for i, ch in enumerate(text) if ch == " "]
    if not candidates:
        return [text]
    lines: list[str] = []
    start = 0
    best: int | None = None
    for candidate in candidates:
        pushed_whole = False
        while len(text[start:candidate]) > width:
            if best is not None:
                lines.append(text[start:best])
                start = best + 1
                best = None
            else:
                lines.append(text[start:candidate])
                start = candidate + 1
                pushed_whole = True
                break
        if pushed_whole:
            continue
        best = candidate
    while len(text[start:]) > width:
        if best is None:
            break
        lines.append(text[start:best])
        start = best + 1
        best = None
    lines.append(text[start:])
    return lines


class Para:
    """One paragraph: its physical lines, and its `**Label:**` when it is a row."""

    def __init__(self, lines: list[str]):
        self.lines = lines
        m = ROW_START.match(lines[0])
        self.label = m.group(1) if m else None

    def value(self) -> str:
        first = self.lines[0][ROW_START.match(self.lines[0]).end():].strip()
        return " ".join([first] + [ln.strip() for ln in self.lines[1:]]).strip()


def split_paragraphs(lines: list[str]) -> list[tuple[int, int, bool]]:
    """Spans (start, end, is_blank_run) over `lines`, end exclusive."""
    spans = []
    i = 0
    while i < len(lines):
        j = i
        blank = lines[i].strip() == ""
        while j < len(lines) and (lines[j].strip() == "") == blank:
            j += 1
        spans.append((i, j, blank))
        i = j
    return spans


def find_blocks(body_lines: list[str]):
    """Yield (first_line, end_line, [Para]) for each defense block of a body.

    A block starts at a paragraph that begins with `**Armor class:**` and runs over the
    following `**Label:**` paragraphs, one blank line between each. Lines inside a fenced code
    block never start a block."""
    spans = split_paragraphs(body_lines)
    paras = [(s, e, body_lines[s:e]) for s, e, blank in spans if not blank]
    fenced = False
    fence_state = []
    for s, e, ls in paras:
        for ln in ls:
            if ln.lstrip().startswith("```"):
                fenced = not fenced
        fence_state.append(fenced)
    k = 0
    while k < len(paras):
        s, e, ls = paras[k]
        if ls[0].startswith("**Armor class:**") and not fence_state[k]:
            rows = [Para(ls)]
            end = e
            m = k + 1
            while m < len(paras):
                ms, me, mls = paras[m]
                p = Para(mls)
                if p.label is None or not _single_blank(body_lines, end, ms):
                    break
                rows.append(p)
                end = me
                m += 1
            yield s, end, rows
            k = m
        else:
            k += 1


def _single_blank(lines: list[str], end: int, start: int) -> bool:
    return start - end == 1 and lines[end].strip() == ""


def classify(rows: list[Para]) -> tuple[str, str]:
    """('rewrite' | 'already' | 'unparsed', reason)."""
    labels = [r.label for r in rows]
    if len(labels) > 1 and labels[1] == "Touch":
        if "Flat-footed" in labels:
            return "already", "labeled rows present"
    present_new = [l for l in NEW_LABELS if l in labels]
    if present_new:
        return "unparsed", "new label already present without the full set: " + ", ".join(present_new)
    for core in CORE:
        n = labels.count(core)
        if n != 1:
            return "unparsed", f"core row `{core}` appears {n} times"
    if labels.count("Mod") > 1:
        return "unparsed", "`Mod` appears more than once"
    if labels.count("Armor class") != 1:
        return "unparsed", "`Armor class` appears more than once"
    if not AC_VALUE.fullmatch(rows[0].value()):
        return "unparsed", "`Armor class` value is not N/N/N: " + rows[0].value()[:40]
    return "rewrite", ""


def rewrite_block(rows: list[Para]) -> list[list[str]]:
    """The new paragraphs (each a list of physical lines), in order."""
    ac, touch, flat = AC_VALUE.fullmatch(rows[0].value()).groups()
    out: list[list[str]] = [
        [f"**Armor class:** {ac}"],
        [f"**Touch:** {touch}"],
        [f"**Flat-footed:** {flat}"],
    ]
    by_label = {r.label: r for r in rows[1:]}
    if "Mod" in by_label:
        out.append(wrap(f"**AC modifiers:** {by_label['Mod'].value()}"))
    for label in CORE:
        out.append(by_label[label].lines)
    used = {"Mod", *CORE}
    for r in rows[1:]:
        if r.label not in used:
            out.append(r.lines)
    return out


def process(text: str):
    """Return (new_text, [(status, reason)]) for one entry file."""
    if not text.startswith("+++\n") or FRONT_MATTER_END not in text:
        return text, []
    cut = text.index(FRONT_MATTER_END, 4) + len(FRONT_MATTER_END)
    head, body = text[:cut], text[cut:]
    lines = body.split("\n")
    results = []
    edits = []
    for first, end, rows in find_blocks(lines):
        status, reason = classify(rows)
        results.append((status, reason))
        if status == "rewrite":
            new = []
            for k, para in enumerate(rewrite_block(rows)):
                if k:
                    new.append("")
                new.extend(para)
            edits.append((first, end, new))
    for first, end, new in reversed(edits):
        lines[first:end] = new
    return head + "\n".join(lines), results


def verify(old: str, new: str) -> None:
    """Raise unless only defense blocks changed and every row survived."""
    oc = old.index(FRONT_MATTER_END, 4)
    nc = new.index(FRONT_MATTER_END, 4)
    if old[:oc] != new[:nc]:
        raise AssertionError("front matter changed")
    ob, nb = old[oc:].split("\n"), new[nc:].split("\n")
    oblocks = list(find_blocks(ob))
    nblocks = list(find_blocks(nb))
    if len(oblocks) != len(nblocks):
        raise AssertionError("block count changed")
    # Outside the blocks the text is identical.
    def outside(lines, blocks):
        keep, pos = [], 0
        for first, end, _ in blocks:
            keep.extend(lines[pos:first])
            keep.append("<<block>>")
            pos = end
        keep.extend(lines[pos:])
        return keep
    if outside(ob, oblocks) != outside(nb, nblocks):
        raise AssertionError("text outside the defense blocks changed")
    for (_, _, orows), (_, _, nrows) in zip(oblocks, nblocks):
        if classify(orows)[0] == "already":
            continue
        # Every old row other than AC and Mod survives verbatim, once.
        keep_old = [r.lines for r in orows if r.label not in ("Armor class", "Mod")]
        keep_new = [r.lines for r in nrows if r.label not in ("Armor class", "Touch", "Flat-footed", "AC modifiers")]
        if sorted(map(tuple, keep_old)) != sorted(map(tuple, keep_new)):
            raise AssertionError("a defense row changed")
        # The three AC numbers still equal the old N/N/N.
        a, t, f = (nrows[0].value(), nrows[1].value(), nrows[2].value())
        if "/".join((a, t, f)) != orows[0].value():
            raise AssertionError("armor class numbers changed")
        mods_old = [r.value() for r in orows if r.label == "Mod"]
        mods_new = [r.value() for r in nrows if r.label == "AC modifiers"]
        if mods_old != mods_new:
            raise AssertionError("AC modifiers differ from Mod")
        labels = [r.label for r in nrows]
        want = ["Armor class", "Touch", "Flat-footed"] + (["AC modifiers"] if mods_old else []) + list(CORE)
        if labels[: len(want)] != want:
            raise AssertionError(f"order is {labels}")


def atomic_write(path: Path, text: str) -> None:
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".defense-", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as f:
            f.write(text)
        os.chmod(tmp, path.stat().st_mode & 0o7777)
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def letters(spec: str) -> set[str]:
    """`a-c,x` -> {a, b, c, x}."""
    out: set[str] = set()
    for part in spec.split(","):
        m = re.fullmatch(r"([a-z0-9])(?:-([a-z0-9]))?", part.strip())
        if not m:
            raise SystemExit(f"--only: cannot read `{part}` (use letters or ranges such as a-c,x)")
        lo, hi = m.group(1), m.group(2) or m.group(1)
        out.update(chr(c) for c in range(ord(lo), ord(hi) + 1))
    return out


def run(root: Path, write: bool, only: set[str] | None = None) -> int:
    entries = root / "entries"
    if not entries.is_dir():
        print(f"{root}: no entries/ directory", file=sys.stderr)
        return 2
    counts: collections.Counter[str] = collections.Counter()
    file_counts: collections.Counter[str] = collections.Counter()
    unparsed: list[str] = []
    other_shapes: collections.Counter[str] = collections.Counter()
    files_with_block = 0
    changed = 0
    for path in sorted(entries.glob("*/*.md")):
        if only is not None and path.name[0] not in only:
            continue
        text = path.read_text(encoding="utf-8")
        if "\n**Armor class:**" not in text:
            continue
        files_with_block += 1
        new, results = process(text)
        for status, reason in results:
            counts[status] += 1
            if status == "unparsed":
                unparsed.append(f"{path.relative_to(root)}: {reason}")
        statuses = {s for s, _ in results}
        file_counts["rewrite" if "rewrite" in statuses else ("unparsed" if "unparsed" in statuses else "already")] += 1
        if new != text:
            verify(text, new)
            changed += 1
            if write:
                atomic_write(path, new)
    print(f"files with a defense block: {files_with_block}")
    print("blocks: " + ", ".join(f"{k} {v}" for k, v in sorted(counts.items())))
    print("files (by the worst block): " + ", ".join(f"{k} {v}" for k, v in sorted(file_counts.items())))
    print(f"files {'written' if write else 'that --write would change'}: {changed}")
    if unparsed:
        print("left unchanged, cannot parse:")
        for line in unparsed:
            print("  " + line)
    return 0


# ---------------------------------------------------------------------------------------------
# Self-test: synthetic entries, no real data.

FM = '+++\nid = "ref/monster/test"\nkind = "creature"\ntitle = "Test"\n\n[fields]\nkind = "creature"\nac = "16/13/14"\n+++\n\n'
GOBLIN = (
    "_Flavor._\n\n**Test**\n\n**Armor class:** 16/13/14\n\n**Fort:** +3\n\n**Hit points:** 6 (1d10+1)\n\n"
    "**Mod:** +2 armor, +2 Dex, +1 shield, +1 size\n\n**Ref:** +2\n\n**Will:** -1\n\n**Offense**\n\n"
    "**Speed:** 30 ft.\n"
)
GOBLIN_NEW = (
    "_Flavor._\n\n**Test**\n\n**Armor class:** 16\n\n**Touch:** 13\n\n**Flat-footed:** 14\n\n"
    "**AC modifiers:** +2 armor, +2 Dex, +1 shield, +1 size\n\n**Hit points:** 6 (1d10+1)\n\n**Fort:** +3\n\n"
    "**Ref:** +2\n\n**Will:** -1\n\n**Offense**\n\n**Speed:** 30 ft.\n"
)


class SelfTest(unittest.TestCase):
    def test_goblin(self):
        new, res = process(FM + GOBLIN)
        self.assertEqual(new, FM + GOBLIN_NEW)
        self.assertEqual(res, [("rewrite", "")])
        verify(FM + GOBLIN, new)

    def test_idempotent(self):
        new, _ = process(FM + GOBLIN)
        again, res = process(new)
        self.assertEqual(again, new)
        self.assertEqual([s for s, _ in res], ["already"])

    def test_other_rows_keep_their_order_after_the_saves(self):
        body = (
            "**Armor class:** 20/10/19\n\n**Defensive abilities:** a, b\n\n**Dr:** 5/magic\n\n**Fort:** +1\n\n"
            "**Hit points:** 3 (1d8)\n\n**Immune:** fire\n\n**Mod:** +1 Dex\n\n**Ref:** +2\n\n**Sr:** 11\n\n"
            "**Will:** +3\n\n**Offense**\n"
        )
        new, _ = process(FM + body)
        labels = [p.label for _, _, rows in find_blocks(new.split("\n")) for p in rows]
        self.assertEqual(
            labels,
            ["Armor class", "Touch", "Flat-footed", "AC modifiers", "Hit points", "Fort", "Ref", "Will",
             "Defensive abilities", "Dr", "Immune", "Sr"],
        )

    def test_wrapped_value_row_moves_whole(self):
        body = (
            "**Armor class:** 1/2/3\n\n**Fort:** +1\n\n**Hit points:** 3 (1d8)\n\n**Immune:** ability damage,\n"
            "charm, fire\n\n**Ref:** +2\n\n**Will:** +3\n\n**Offense**\n"
        )
        new, _ = process(FM + body)
        self.assertIn("**Will:** +3\n\n**Immune:** ability damage,\ncharm, fire\n\n**Offense**", new)

    def test_no_mod_row(self):
        body = "**Armor class:** 10/10/10\n\n**Fort:** +1\n\n**Hit points:** 3 (1d8)\n\n**Ref:** +2\n\n**Will:** +3\n\n**Offense**\n"
        new, res = process(FM + body)
        self.assertNotIn("AC modifiers", new)
        self.assertEqual(res, [("rewrite", "")])
        verify(FM + body, new)

    def test_negative_touch(self):
        body = "**Armor class:** 27/-1/27\n\n**Fort:** +1\n\n**Hit points:** 3 (1d8)\n\n**Ref:** +2\n\n**Will:** +3\n\n**Offense**\n"
        new, _ = process(FM + body)
        self.assertIn("**Touch:** -1\n\n**Flat-footed:** 27", new)

    def test_long_mod_wraps_like_the_formatter(self):
        mod = ", ".join(f"+{n} {w}" for n, w in [(13, "armor"), (5, "deflection"), (5, "Dex"), (11, "insight"),
                                                  (7, "natural"), (6, "shield"), (4, "profane"), (3, "luck")])
        body = (
            "**Armor class:** 40/20/35\n\n**Fort:** +1\n\n**Hit points:** 3 (1d8)\n\n"
            f"**Mod:** {mod}\n\n**Ref:** +2\n\n**Will:** +3\n\n**Offense**\n"
        )
        new, _ = process(FM + body)
        for line in new.split("\n"):
            self.assertLessEqual(len(line), WRAP_WIDTH, line)
        paras = [p for _, _, rows in find_blocks(new.split("\n")) for p in rows]
        got = [p for p in paras if p.label == "AC modifiers"][0]
        self.assertGreater(len(got.lines), 1)
        self.assertEqual(got.value(), mod)

    def test_unparsable_blocks_stay_unchanged(self):
        cases = {
            "not N/N/N": "**Armor class:** 16, touch 13\n\n**Fort:** +1\n\n**Hit points:** 3 (1d8)\n\n**Ref:** +2\n\n**Will:** +3\n\n**Offense**\n",
            "missing Will": "**Armor class:** 1/2/3\n\n**Fort:** +1\n\n**Hit points:** 3 (1d8)\n\n**Ref:** +2\n\n**Offense**\n",
            "duplicate Fort": "**Armor class:** 1/2/3\n\n**Fort:** +1\n\n**Fort:** +1\n\n**Hit points:** 3\n\n**Ref:** +2\n\n**Will:** +3\n\n**Offense**\n",
            "partial new label": "**Armor class:** 1/2/3\n\n**Touch:** 2\n\n**Fort:** +1\n\n**Hit points:** 3\n\n**Ref:** +2\n\n**Will:** +3\n\n**Offense**\n",
        }
        for name, body in cases.items():
            with self.subTest(name):
                new, res = process(FM + body)
                self.assertEqual(new, FM + body)
                self.assertEqual([s for s, _ in res], ["unparsed"])

    def test_several_blocks_and_front_matter_untouched(self):
        text = FM + GOBLIN + "\n### Large\n\n" + GOBLIN.split("**Test**\n\n", 1)[1]
        new, res = process(text)
        self.assertEqual([s for s, _ in res], ["rewrite", "rewrite"])
        self.assertTrue(new.startswith(FM))
        self.assertEqual(new.count("**Touch:** 13"), 2)
        verify(text, new)

    def test_text_without_a_block_is_returned_as_is(self):
        text = FM + "Plain **Armor class:** inside a sentence.\n"
        self.assertEqual(process(text), (text, []))

    def test_only_limits_the_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "entries/monster").mkdir(parents=True)
            for name in ("alpha.md", "zulu.md"):
                (root / "entries/monster" / name).write_text(FM + GOBLIN, encoding="utf-8")
            self.assertEqual(run(root, write=True, only=letters("a-c")), 0)
            self.assertEqual((root / "entries/monster/alpha.md").read_text(), FM + GOBLIN_NEW)
            self.assertEqual((root / "entries/monster/zulu.md").read_text(), FM + GOBLIN)
        self.assertEqual(letters("a-c,x"), {"a", "b", "c", "x"})

    def test_end_to_end_on_disk(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "entries/monster").mkdir(parents=True)
            path = root / "entries/monster/test.md"
            path.write_text(FM + GOBLIN, encoding="utf-8")
            path.chmod(0o640)
            self.assertEqual(run(root, write=False), 0)
            self.assertEqual(path.read_text(encoding="utf-8"), FM + GOBLIN)
            self.assertEqual(run(root, write=True), 0)
            self.assertEqual(path.read_text(encoding="utf-8"), FM + GOBLIN_NEW)
            self.assertEqual(path.stat().st_mode & 0o777, 0o640)
            self.assertEqual([p.name for p in path.parent.iterdir()], ["test.md"])
            self.assertEqual(run(root, write=True), 0)
            self.assertEqual(path.read_text(encoding="utf-8"), FM + GOBLIN_NEW)


def main(argv: list[str]) -> int:
    args = argv[1:]
    if "--self-test" in args:
        suite = unittest.defaultTestLoader.loadTestsFromTestCase(SelfTest)
        result = unittest.TextTestRunner(verbosity=1).run(suite)
        return 0 if result.wasSuccessful() else 1
    only = None
    if "--only" in args:
        at = args.index("--only")
        if at + 1 >= len(args):
            print("--only needs a value such as a-c", file=sys.stderr)
            return 2
        only = letters(args[at + 1])
        del args[at : at + 2]
    write = "--write" in args
    rest = [a for a in args if not a.startswith("--")]
    unknown = [a for a in args if a.startswith("--") and a not in ("--write",)]
    if unknown or len(rest) > 1:
        print(__doc__.split("Usage:")[1].split("`DIR`")[0], file=sys.stderr)
        return 2
    root = Path(rest[0]) if rest else Path(__file__).resolve().parent.parent
    return run(root, write, only)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
