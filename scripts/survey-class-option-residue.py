#!/usr/bin/env python3
r"""Count the import residue in the class-option entries (issue phynics/cast-iron-data#88).

A class option is an entry with `kind = "class_option"` (bloodlines, mysteries, patrons,
spirits, domains, arcane schools, mercies, and so on). The retired upstream import left
these defects in them:

  skill-code        a `Gained class skills:` or `Lost class skills:` value that is an
                    upstream skill code ("kd", "stl", "perf|dance") instead of a skill name
  spell-no-level    a `Spells:` row that does not end in its granted level ("(3rd)")
  spell-order       bonus spells out of numeric level order. Without levels the scan needs
                    `--upstream` to see that the rows are in the text-sorted order of the
                    upstream keys (11, 13, ... 19, 3, 5, ...). With levels it compares them.
  key-tilde         a `**Key:** ~` row: the import's line-break marker, no printed content
  misplaced-title   a `Details:` row followed by a `Title:` row; the title is the row's label
  bonus-feats-glue  a bonus-feat `Details:` row whose feat links have no separator
  tilde-in-text     a literal `\~` inside prose: the import's paragraph and list break
                    ("\~\~\~"), left in the text; reported only, never changed here
  import-key        `Id:`, `From:` and `Save: domain` rows: renderer instructions of the
                    upstream, no printed content
  glued-modifier    "Charisma3 modifier times/day": the upstream `useMod` value, printed as
                    "3 + your Charisma modifier"
  power-order       a power whose `At Nth Level:` rows come before its base effect (the
                    import sorted the rows of a power by key)
  numbered-key      `Ability2:` and `Ability3:`; reported only, never changed

Usage (from the corpus root, read-only, no edits):

    python3 scripts/survey-class-option-residue.py [--upstream DIR] [--list DEFECT] [--keys]

Output: the number of occurrences and of files for each defect, then the same count per
family (the directory under `entries/`). `--upstream DIR` is a checkout of the pinned
upstream dataset (`legal.toml` names it); it only lets the scan see text-sorted spell order
in rows that still lack levels. `--list DEFECT` prints `path:line` for each occurrence.
`--keys` prints how often each `**Key:**` label occurs in class options.

The scan counts candidates in the shapes above. The fix script says which candidates it
changes and which stay.
"""

import argparse
import collections
import json
import re
import sys
import tomllib
from pathlib import Path

# Upstream skill codes and the printed skill names.
SKILLS = {
    "acro": "Acrobatics",
    "app": "Appraise",
    "bluff": "Bluff",
    "climb": "Climb",
    "craft": "Craft",
    "dd": "Disable Device",
    "diplo": "Diplomacy",
    "dis": "Disguise",
    "ea": "Escape Artist",
    "fly": "Fly",
    "ha": "Handle Animal",
    "heal": "Heal",
    "intm": "Intimidate",
    "ka": "Knowledge (arcana)",
    "kd": "Knowledge (dungeoneering)",
    "ke": "Knowledge (engineering)",
    "kg": "Knowledge (geography)",
    "kh": "Knowledge (history)",
    "kl": "Knowledge (local)",
    "kna": "Knowledge (nature)",
    "kno": "Knowledge (nobility)",
    "kp": "Knowledge (planes)",
    "kr": "Knowledge (religion)",
    "ling": "Linguistics",
    "per": "Perception",
    "perf": "Perform",
    "prof": "Profession",
    "ride": "Ride",
    "sm": "Sense Motive",
    "soh": "Sleight of Hand",
    "spc": "Spellcraft",
    "stl": "Stealth",
    "sur": "Survival",
    "swim": "Swim",
    "umd": "Use Magic Device",
}
ORDINAL = re.compile(r"\((\d+)(?:st|nd|rd|th)\)\s*$")
ROW = re.compile(r"^\*\*([^*]+?):\*\*(?:\s+(.*))?$", re.S)
HEADING = re.compile(r"^\*\*([^*:]+)\*\*\s*$")
AT_LEVEL = re.compile(r"^At (\d+)(?:st|nd|rd|th) Level$", re.I)
GLUED = re.compile(r"\b([A-Za-z]+)(\d) modifier")
ATTR = re.compile(r'(\w+)=("(?:[^"\\]|\\.)*"|\S+)')

DEFECTS = [
    "skill-code",
    "spell-no-level",
    "spell-order",
    "key-tilde",
    "misplaced-title",
    "bonus-feats-glue",
    "tilde-in-text",
    "import-key",
    "glued-modifier",
    "power-order",
    "numbered-key",
]


def ordinal(n: int) -> str:
    if 10 <= n % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


class Entry:
    """One corpus file: front matter, then paragraphs with their first line number."""

    def __init__(self, path: Path):
        self.path = path
        text = path.read_text(encoding="utf-8")
        _, head, body = text.split("+++\n", 2) if text.startswith("+++\n") else ("", "", text)
        self.head_text = head
        self.head = tomllib.loads(head)
        self.body = body
        self.family = path.parent.name
        self.body_first_line = text[: text.index(body)].count("\n") + 1 if body else 1
        self.paras = []  # (first line number, text)
        line = self.body_first_line
        for chunk in re.split(r"(\n\s*\n)", body):
            if chunk.strip():
                self.paras.append((line, chunk))
            line += chunk.count("\n")

    @property
    def is_class_option(self) -> bool:
        return self.head.get("kind") == "class_option"


def entries(root: Path):
    for path in sorted((root / "entries").glob("*/*.md")):
        entry = Entry(path)
        if entry.is_class_option:
            yield entry


def row_of(para: str):
    """Return (key, value) when a paragraph is a `**Key:** value` row."""
    m = ROW.match(para.strip())
    if not m:
        return None
    return m.group(1), " ".join((m.group(2) or "").split())


def value_tilde(para: str) -> bool:
    """A paragraph with a literal `\\~` in prose; a bare `**Key:** \\~` row is `key-tilde`."""
    r = row_of(para)
    if r and r[1] in ("\\~", "~"):
        return False
    return "\\~" in para


def spell_name(value: str) -> str:
    """Normalise a corpus spell row to the bare spell name, for matching."""
    value = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", value)
    value = re.split(r"\\\||\|", value)[0]
    value = re.sub(ORDINAL, "", value)
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def spell_runs(entry: Entry):
    """Runs of consecutive `Spells:` and `Cantrips:` paragraphs: lists of (line, key, value)."""
    runs, cur = [], []
    for line, para in entry.paras:
        r = row_of(para)
        if r and r[0] in ("Spells", "Cantrips"):
            cur.append((line, r[0], r[1]))
        elif cur:
            runs.append(cur)
            cur = []
    if cur:
        runs.append(cur)
    return runs


def row_level(key: str, value: str):
    """The level a row states, 0 for a cantrip row, None when it states none."""
    if key == "Cantrips":
        return 0
    m = ORDINAL.search(value)
    return int(m.group(1)) if m else None


def upstream_attrs(line: str) -> dict:
    return {k: (v[1:-1] if v.startswith('"') else v.rstrip("}")) for k, v in ATTR.findall(line)}


def upstream_record(upstream: Path, entry: Entry, cache: dict):
    prov = (entry.head.get("provenance") or [None])[0]
    if not prov:
        return None
    path = prov["path"]
    if path not in cache:
        cache[path] = json.loads((upstream / path).read_text(encoding="utf-8"))
    return cache[path].get(prov["record"])


def upstream_spell_lines(record: dict):
    """The spell lists of an upstream record: for each `::ab` line, [(level, name), ...]
    in the order the upstream attributes appear."""
    out = []
    for line in record["description"]:
        if not line.startswith("::"):
            continue
        levels = [(int(k[1:]), v) for k, v in upstream_attrs(line).items() if re.fullmatch(r"s\d+", k)]
        if levels:
            out.append(levels)
    return out


def power_blocks(entry: Entry):
    """Yield (heading, [(line, key, value)]) for each run of keyed rows after a power heading."""
    heading, rows = None, []
    for line, para in entry.paras:
        h = HEADING.match(para.strip())
        r = row_of(para)
        if h:
            if heading is not None:
                yield heading, rows
            heading, rows = h.group(1), []
        elif r and heading is not None:
            rows.append((line, r[0], r[1]))
        else:
            if heading is not None:
                yield heading, rows
            heading, rows = None, []
    if heading is not None:
        yield heading, rows


def power_order_defect(rows) -> bool:
    seen_at = False
    for _, key, _ in rows:
        if AT_LEVEL.match(key):
            seen_at = True
        elif seen_at:
            return True
    return False


def scan(root: Path, upstream: Path | None):
    """Return {defect: [(entry, line)]}."""
    found = {d: [] for d in DEFECTS}
    cache: dict = {}
    for entry in entries(root):
        paras = entry.paras
        for i, (line, para) in enumerate(paras):
            r = row_of(para)
            if not r:
                continue
            key, value = r
            if key in ("Gained class skills", "Lost class skills"):
                tokens = [t.strip() for t in re.split(r"\s*,\s*", value) if t.strip()]
                if any(t.split("\\|")[0] in SKILLS for t in tokens):
                    found["skill-code"].append((entry, line))
            if key == "Spells" and row_level(key, value) is None:
                found["spell-no-level"].append((entry, line))
            if value in ("\\~", "~"):
                found["key-tilde"].append((entry, line))
            if key == "Title" and i > 0 and (row_of(paras[i - 1][1]) or ("",))[0] == "Details":
                found["misplaced-title"].append((entry, line))
            nxt = (row_of(paras[i + 1][1]) or ("",))[0] if i + 1 < len(paras) else ""
            if key == "Details" and nxt == "Title" and (re.search(r"\)\[", value) or "\\~" in value):
                found["bonus-feats-glue"].append((entry, line))
            if key in ("Id", "From") or (key == "Save" and value == "domain"):
                found["import-key"].append((entry, line))
            if key == "Usage" and GLUED.search(value):
                found["glued-modifier"].append((entry, line))
            if re.fullmatch(r"Ability\d", key):
                found["numbered-key"].append((entry, line))
        for line, para in paras:
            if value_tilde(para):
                found["tilde-in-text"].append((entry, line))
        for heading, rows in power_blocks(entry):
            if power_order_defect(rows):
                found["power-order"].append((entry, rows[0][0] - 2))
        for run in spell_runs(entry):
            levels = [row_level(k, v) for _, k, v in run]
            if all(lv is not None for lv in levels):
                if levels != sorted(levels):
                    found["spell-order"].append((entry, run[0][0]))
        if upstream is not None and spell_runs(entry):
            record = upstream_record(upstream, entry, cache)
            rows = [row for run in spell_runs(entry) for row in run]
            if record and any(row_level(k, v) is None for _, k, v in rows):
                text_sorted, numeric = [], []
                for lines in upstream_spell_lines(record):
                    text_sorted += [n for lv, n in sorted(lines, key=lambda x: str(x[0])) if lv]
                    numeric += [n for lv, n in sorted(lines) if lv]
                corpus = [spell_name(v) for _, k, v in rows if k == "Spells"]
                if corpus == [spell_name(n) for n in text_sorted] and corpus != [spell_name(n) for n in numeric]:
                    found["spell-order"].append((entry, rows[0][0]))
    return found


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", default=".", help="corpus root (default: the current directory)")
    ap.add_argument("--upstream", help="checkout of the pinned upstream dataset")
    ap.add_argument("--list", metavar="DEFECT", help="print path:line for each occurrence")
    ap.add_argument("--keys", action="store_true", help="print the census of `**Key:**` labels")
    args = ap.parse_args()
    root = Path(args.root)
    upstream = Path(args.upstream) if args.upstream else None

    if args.keys:
        census = collections.Counter()
        for entry in entries(root):
            for _, para in entry.paras:
                r = row_of(para)
                if r:
                    census[r[0]] += 1
        for key, n in census.most_common():
            print(f"{n}\t{key}")
        return 0

    found = scan(root, upstream)
    if args.list:
        for entry, line in sorted(found[args.list], key=lambda x: (str(x[0].path), x[1])):
            print(f"{entry.path.relative_to(root)}:{line}")
        return 0

    print(f"{'defect':<18}{'rows':>7}{'files':>7}")
    for d in DEFECTS:
        files = {str(e.path) for e, _ in found[d]}
        print(f"{d:<18}{len(found[d]):>7}{len(files):>7}")
    print()
    for d in DEFECTS:
        by_family = collections.Counter(e.family for e, _ in found[d])
        if by_family:
            fam = ", ".join(f"{f} {n}" for f, n in by_family.most_common())
            print(f"{d}: {fam}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
