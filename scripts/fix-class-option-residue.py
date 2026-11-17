#!/usr/bin/env python3
r"""Repair the import residue in the class-option entries (issue phynics/cast-iron-data#88).

Run `scripts/survey-class-option-residue.py` first; this script fixes the candidates it
counts and names every one it leaves alone.

    python3 scripts/fix-class-option-residue.py --upstream DIR [--dry-run] [--report FILE]

`--upstream` is a checkout of the pinned upstream dataset (`legal.toml` names the commit).
The script is idempotent: a second run changes nothing. After it, run `cast-iron-corpus fmt`
to wrap the long lines it writes.

Fixes (class-option entries only):

  skills     `Gained class skills: kd` -> the printed names, linked to the skill entries; the
             ten Knowledge skills together -> "all Knowledge skills", as printed.
  spells     Each `Spells:` row gets its granted level, "Feeblemind (11th)", and each run of
             rows goes into numeric level order. The levels come from the upstream record
             (`s3=...`, `s11=...`); the corpus rows are the upstream attributes in the text
             order of their keys (s11, s13, ..., s3, s5), so the match is by position, and
             a run is changed only when every row matches the upstream spell at its place.
             A note after a spell ("Elemental body III\|(water only)") becomes plain text
             after the name; a footnote star stays attached to the name, as printed.
  feats      `Br: ~`, `Details: <feats>`, `Title: Bonus Feats` -> `**Bonus Feats:** A, B, C`.
             The feats are the links of the `Details` row; the upstream `~` separators
             were lost by the import.
  mercy      `Details: <text>`, `Title: <the entry title>` -> the text as a plain paragraph.
  domain     `Id:`, `From:` and `Save: domain` rows are removed. They are renderer
             instructions of the upstream and carry no printed content.
  modifier   `Usage: Charisma3 modifier times/day` -> `3 + Charisma modifier times/day`.
  order      In the sorcerer and bloodrager bloodlines, the `At Nth Level:` rows of a power
             move after its base effect, in numeric order. The import had sorted the rows
             of a power by key. Other families have the same defect (see the survey) and
             stay unchanged.

A run, row group or block that does not match the evidence is left unchanged and listed.
"""

import argparse
import importlib.util
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("survey", HERE / "survey-class-option-residue.py")
survey = importlib.util.module_from_spec(_spec)
sys.modules["survey"] = survey
_spec.loader.exec_module(survey)

SKILL_SLUG = {
    "Acrobatics": "acrobatics",
    "Appraise": "appraise",
    "Bluff": "bluff",
    "Climb": "climb",
    "Craft": "craft-any",
    "Disable Device": "disable-device",
    "Diplomacy": "diplomacy",
    "Disguise": "disguise",
    "Escape Artist": "escape-artist",
    "Fly": "fly",
    "Handle Animal": "handle-animal",
    "Heal": "heal",
    "Intimidate": "intimidate",
    "Linguistics": "linguistics",
    "Perception": "perception",
    "Perform": "perform-any",
    "Profession": "profession-any",
    "Ride": "ride",
    "Sense Motive": "sense-motive",
    "Sleight of Hand": "sleight-of-hand",
    "Spellcraft": "spellcraft",
    "Stealth": "stealth",
    "Survival": "survival",
    "Swim": "swim",
    "Use Magic Device": "use-magic-device",
}
KNOWLEDGE = ["ka", "kd", "ke", "kg", "kh", "kl", "kna", "kno", "kp", "kr"]
ABILITY = {"Wis": "Wisdom", "Int": "Intelligence", "Cha": "Charisma", "Con": "Constitution", "Str": "Strength", "Dex": "Dexterity"}
BLOODLINE_FAMILIES = {"sorcbloodline", "blrgbloodline"}
LINK = re.compile(r"\[[^\]]+\]\(ref/[^)]+\)")


def skill_link(code: str) -> str:
    """The linked printed name for one skill code, `perf|oratory` included."""
    base, _, sub = code.partition("\\|")
    name = survey.SKILLS[base]
    if sub:
        name = f"{name} ({sub})"
    if base.startswith("k") and base in KNOWLEDGE:
        slug = "knowledge-" + name.split("(")[1].rstrip(")")
    else:
        slug = SKILL_SLUG[survey.SKILLS[base]]
    return f"[{name}]({'ref/skill/' + slug})"


def fix_skills(value: str):
    """The linked printed names for a row of skill codes; None when the row has other text."""
    tokens = [t.strip() for t in re.split(r"\s*,\s*", value) if t.strip()]
    if not tokens or not all(t.split("\\|")[0] in survey.SKILLS for t in tokens):
        return None
    out, all_knowledge = [], all(k in tokens for k in KNOWLEDGE)
    for token in tokens:
        if all_knowledge and token in KNOWLEDGE:
            if token == next(t for t in tokens if t in KNOWLEDGE):
                out.append("all [Knowledge](ref/skill/knowledge-all) skills")
        else:
            out.append(skill_link(token))
    return ", ".join(out)


def spell_text(value: str, level: int | None) -> str:
    """The row text for a spell: its note as plain text, its level last."""
    name, sep, note = value.partition("\\|")
    if sep:
        name = name + (note if note == "\\*" else " " + note)
    return f"{name} ({survey.ordinal(level)})" if level else name


def upstream_rows(record):
    """Per `::ab` spell line, the (level, name) pairs in the text order of the keys."""
    return [sorted(lines, key=lambda x: str(x[0])) for lines in survey.upstream_spell_lines(record)]


def fix_spells(paras, record, notes):
    """Add levels and numeric order to every run of spell rows. Mutates `paras`."""
    lines_up = upstream_rows(record)
    runs = []  # (start index, end index) in paras
    i = 0
    while i < len(paras):
        r = survey.row_of(paras[i])
        if r and r[0] in ("Spells", "Cantrips"):
            j = i
            while j < len(paras) and (survey.row_of(paras[j]) or ("",))[0] in ("Spells", "Cantrips"):
                j += 1
            runs.append((i, j))
            i = j
        else:
            i += 1
    if not runs:
        return False
    rows = [survey.row_of(paras[k]) for a, b in runs for k in range(a, b)]
    if all(survey.row_level(k, v) is not None for k, v in rows if k == "Spells"):
        return False  # already levelled
    flat = [pair for lines in lines_up for pair in lines]
    if len(flat) != len(rows):
        notes.append(f"{len(rows)} spell rows, upstream states {len(flat)}")
        return False
    if [len(lines) for lines in lines_up] != [b - a for a, b in runs]:
        notes.append("spell runs do not line up with the upstream spell lists")
        return False
    for (key, value), (level, name) in zip(rows, flat):
        if survey.spell_name(value) != survey.spell_name(name) or (key == "Cantrips") != (level == 0):
            notes.append(f"row '{value}' does not match upstream '{name}' (s{level})")
            return False
    pos = 0
    for a, b in runs:
        new = []
        for k in range(a, b):
            key, value = survey.row_of(paras[k])
            level = flat[pos][0]
            pos += 1
            new.append((level, f"**{key}:** {spell_text(value, level) if key == 'Spells' else value}"))
        new.sort(key=lambda x: x[0])  # stable: equal levels keep the corpus order
        paras[a:b] = [text for _, text in new]
    return True


def upstream_feat_pieces(record):
    """The `~`-separated pieces of the upstream "Bonus Feats" row."""
    for line in record["description"]:
        m = re.search(r'info="([^"]*)"', line)
        if line.startswith("::row") and 'title="Bonus Feats"' in line and m:
            return m.group(1).split("~")
    return None


def feat_piece(piece: str, links: dict):
    """One upstream piece as corpus text: `‹feat/Name›` becomes the corpus link of that feat."""
    missing = []

    def link(m):
        name = m.group(1)
        if name.lower() not in links:
            missing.append(name)
            return name
        return links[name.lower()]

    text = re.sub(r"‹feat/([^›]+)›", link, piece)
    for code, char in (("&#42&", "\\*"), ("&#91&", "\\["), ("&#93&", "\\]")):
        text = text.replace(code, char)
    prose = LINK.sub("", text)
    if prose.count(")") > prose.count("(") and text.endswith(")"):  # a stray ")" in the upstream
        text = text[:-1]
    if "‹" not in text and "[" not in text.replace("\\[", ""):  # plain feat name: link it
        base = re.split(r"\s*\(", text)[0].strip()
        if base.lower() in links:
            text = links[base.lower()] + text[len(base):]
    return text, missing


def fix_feats(paras, record, notes):
    changed = False
    i = 0
    while i + 2 < len(paras):
        br, det, ttl = (survey.row_of(paras[i + k]) for k in range(3))
        if br and det and ttl and br[0] == "Br" and br[1] in ("\\~", "~") and det[0] == "Details" and ttl[0] == "Title":
            pieces = upstream_feat_pieces(record) if record else None
            links = {}
            for m in LINK.finditer(det[1]):
                links.setdefault(re.match(r"\[([^\]]+)\]", m.group(0)).group(1).lower(), m.group(0))
            if pieces is None:
                notes.append("bonus feats: no upstream row")
                i += 1
                continue
            texts, missing = zip(*(feat_piece(pc, links) for pc in pieces))
            missing = [n for ms in missing for n in ms]
            used = len(LINK.findall(det[1]))
            upstream_links = sum(pc.count("‹feat/") for pc in pieces)
            if missing or used != upstream_links:
                notes.append(f"bonus feats: {used} corpus links, {upstream_links} upstream, missing {missing}")
                i += 1
                continue
            paras[i : i + 3] = [f"**{ttl[1]}:** " + ", ".join(" ".join(t.split()) for t in texts)]
            changed = True
        i += 1
    return changed


def fix_mercy(paras, title, notes):
    changed = False
    i = 0
    while i + 1 < len(paras):
        det, ttl = survey.row_of(paras[i]), survey.row_of(paras[i + 1])
        if det and ttl and det[0] == "Details" and ttl[0] == "Title":
            if ttl[1] == title:
                paras[i : i + 2] = [det[1]]
                changed = True
            else:
                notes.append(f"title '{ttl[1]}' differs from the entry title")
        i += 1
    return changed


def fix_import_keys(paras):
    keep = []
    for p in paras:
        r = survey.row_of(p)
        if r and (r[0] in ("Id", "From") or (r[0] == "Save" and r[1] == "domain")):
            continue
        keep.append(p)
    changed = len(keep) != len(paras)
    paras[:] = keep
    return changed


def fix_modifier(paras):
    changed = False
    for i, p in enumerate(paras):
        r = survey.row_of(p)
        if r and r[0] == "Usage" and survey.GLUED.search(r[1]):
            new = survey.GLUED.sub(
                lambda m: f"{m.group(2)} + {ABILITY.get(m.group(1), m.group(1))} modifier", r[1]
            )
            paras[i] = f"**Usage:** {new}"
            changed = True
    return changed


def fix_order(paras, notes):
    """Move the `At Nth Level` rows of each power after its base rows, in numeric order."""
    changed = False
    i = 0
    while i < len(paras):
        if survey.HEADING.match(paras[i].strip()):
            j = i + 1
            while j < len(paras) and survey.row_of(paras[j]) and not survey.HEADING.match(paras[j].strip()):
                j += 1
            rows = [(survey.row_of(p)[0], p) for p in paras[i + 1 : j]]
            if rows and survey.power_order_defect([(0, k, v) for k, v in rows]):
                base = [p for k, p in rows if not survey.AT_LEVEL.match(k)]
                at = sorted(
                    ((int(survey.AT_LEVEL.match(k).group(1)), p) for k, p in rows if survey.AT_LEVEL.match(k)),
                    key=lambda x: x[0],
                )
                if base:
                    paras[i + 1 : j] = base + [p for _, p in at]
                    changed = True
                else:
                    notes.append(f"power '{paras[i].strip()}' has only At-level rows")
            i = j
        else:
            i += 1
    return changed


def fix_entry(entry, upstream, cache):
    """Return (new text or None, [changes], [notes])."""
    text = entry.path.read_text(encoding="utf-8")
    marker = text.index("\n+++\n", 4) + 5
    head, body = text[:marker], text[marker:]
    lead = body[: len(body) - len(body.lstrip("\n"))]
    trail = body[len(body.rstrip("\n")) :]
    paras = [p for p in re.split(r"\n[ \t]*\n", body.strip("\n")) if p.strip()]
    changes, notes = [], []
    record = survey.upstream_record(upstream, entry, cache) if upstream else None

    for i, p in enumerate(paras):
        r = survey.row_of(p)
        if r and r[0] in ("Gained class skills", "Lost class skills"):
            new = fix_skills(r[1])
            if new:
                paras[i] = f"**{r[0]}:** {new}"
                changes.append("skills")
            elif any(t.split("\\|")[0] in survey.SKILLS for t in re.split(r"\s*,\s*", r[1])):
                notes.append(f"class skills row mixes codes and names: {r[1]}")
    if any(survey.row_of(p) and survey.row_of(p)[0] in ("Spells", "Cantrips") for p in paras):
        if record is None:
            notes.append("no upstream record for the spell rows")
        elif fix_spells(paras, record, notes):
            changes.append("spells")
    if fix_feats(paras, record, notes):
        changes.append("feats")
    if entry.family == "mercy" and fix_mercy(paras, entry.head["title"], notes):
        changes.append("mercy")
    if fix_import_keys(paras):
        changes.append("domain")
    if fix_modifier(paras):
        changes.append("modifier")
    if entry.family in BLOODLINE_FAMILIES and fix_order(paras, notes):
        changes.append("order")
    if not changes:
        return None, changes, notes
    return head + lead + "\n\n".join(paras) + trail, changes, notes


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", default=".")
    ap.add_argument("--upstream", required=True)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--report", help="write the list of left-unchanged cases here")
    args = ap.parse_args()
    root, upstream = Path(args.root), Path(args.upstream)
    cache: dict = {}
    counts: dict = {}
    left = []
    for entry in survey.entries(root):
        new, changes, notes = fix_entry(entry, upstream, cache)
        for c in changes:
            counts[c] = counts.get(c, 0) + 1
        for n in notes:
            left.append(f"{entry.path.relative_to(root)}: {n}")
        if new is not None and not args.dry_run:
            entry.path.write_text(new, encoding="utf-8")
    print("entries changed per fix:", json.dumps(counts, sort_keys=True))
    print(f"left unchanged: {len(left)}")
    for line in left:
        print("  " + line)
    if args.report:
        Path(args.report).write_text("\n".join(left) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
