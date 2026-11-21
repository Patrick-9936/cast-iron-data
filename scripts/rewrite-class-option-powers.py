#!/usr/bin/env python3
"""Rewrite class-option powers into the canonical row order (phynics/cast-iron-data#88).

The spec is the decision `2026-11-20-class-option-power-layout` of phynics/cast-iron (sections 1
and 2, "Rewrite and survey algorithm", "Fixtures") and its correction
`2026-11-21-class-option-power-counts`. The app's `cast_iron_schema::power` is the one
classifier and validator; `cargo xtask corpus-check` runs it on this corpus. This script mirrors
it over source text, rewrites what it can without guessing, and queues everything else for print
review with the whole span unchanged.

Usage
-----
    scripts/rewrite-class-option-powers.py --self-test
    scripts/rewrite-class-option-powers.py [CORPUS]            dry run: print the counts
    scripts/rewrite-class-option-powers.py [CORPUS] --write    rewrite the entries, write the queue
    scripts/rewrite-class-option-powers.py [CORPUS] --write-queue   write the queue only
    scripts/rewrite-class-option-powers.py [CORPUS] --check    exit 1 unless a rerun changes nothing

CORPUS defaults to the repository that holds this script. `--families a,b` limits the rewrite
to the entry ids `ref/a/...` and `ref/b/...` (the queue file always covers the whole corpus).
`--write` leaves long lines: run `cargo xtask corpus-fmt <corpus>` after it.

Files
-----
`scripts/class-option-power-queue.tsv`
    One line per power that stays unchanged for hand review: entry id, original name as written
    (with any colon), occurrence among the candidates with that name in the entry, the SHA-256
    of the original span, and the reasons.

`scripts/class-option-power-resolutions.toml`
    The hand-made replacements, one `[[resolution]]` each: `id`, `name`, `occurrence`,
    `span_sha256`, `print` (book and page) and `replacement`: a power that passes validation,
    then any blocks that belong after it (a list that print sets as bullets). A resolution
    applies only when the current span hashes to `span_sha256`. A span that already equals the
    replacement is left alone. Any other span is a stale resolution: reported, and the power is
    queued again.

Span source text (what `span_sha256` hashes)
--------------------------------------------
The span is the name block and the run after it, up to the next boundary or name. Each block is
one logical line: its source lines are stripped and joined by a single space, and a line that ends
in a backslash (a hard break) keeps its break. Blocks are joined by one blank line. The text is
UTF-8 with no trailing newline. The hash does not change when `corpus-fmt` re-wraps a paragraph.

Rules of the rewrite, in short
------------------------------
Candidates, the explicit Action map, allowed crossings, continuation paragraphs, the canonical
order, the upgrade lead `**At Nth level,** <printed sentence>` and the lowercase list follow the
decision. Only identical original `Usage` rows are deduplicated. Anything else the rewrite would
have to guess goes to the queue with its whole span unchanged. The replacement is validated, and
when it fails, the original span is queued. A second pass changes nothing.
"""

from __future__ import annotations

import argparse
import hashlib
import re
import sys
import tomllib
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

EFFECT_LABELS = (
    "Passive", "Ability", "Standard", "Move", "Swift", "Immediate", "Free", "Full-round", "Benefit",
)
ALIAS_LABELS = {"Fullround": "Full-round", "Passive Ability": "Passive", "Standard Action": "Standard"}
ACTION_LABEL = "Action"
# The explicit map of an `Action` value. There is no catch-all.
ACTION_EFFECT = {
    "Ability": "Ability", "ability": "Ability",
    "Passive Ability": "Passive",
    "Standard Action": "Standard", "Standard": "Standard", "Standard.": "Standard",
    "Move Action": "Move",
    "Swift Action": "Swift",
    "Immediate Action": "Immediate",
    "Free Action": "Free",
    "Full-Round Action": "Full-round", "Full-round.": "Full-round",
}
SINGLETONS = ("Gained", "Flavor", "Usage", "Prereq", "Replaces")
# Rows that an `Action` row's effect paragraphs may cross.
CROSSABLE = frozenset(SINGLETONS)
# The first word of an upgrade sentence that the rewrite may lowercase.
LOWERCASE_FIRST = frozenset((
    "You", "Your", "The", "This", "These", "That", "Those", "Its", "It", "A", "An", "Any", "All",
    "Each", "In", "Once", "When", "Whenever", "While", "If", "As", "For", "Add", "By", "She", "He",
    "Her", "His", "They", "Their", "Instead", "Additionally", "Also", "Every", "Allies",
))
ABILITY_TAG = re.compile(r"\s*\((?:Ex|Su|Sp)(?:(?:, | or | and )(?:Ex|Su|Sp))*\)$")

QUEUE_FILE = "scripts/class-option-power-queue.tsv"
RESOLUTIONS_FILE = "scripts/class-option-power-resolutions.toml"
QUEUE_HEADER = "entry_id\toriginal_name\toccurrence\tspan_sha256\treasons"

# Seeded print items: (entry id, original name, occurrence) -> reason. The decision seeds
# Foretell: the corpus says "1 time/day per wizard level", while print gives a number of rounds
# per day equal to the wizard level, not consecutive. A seeded power is queued unless it is
# valid or a resolution applies to it.
PRINT_ITEMS = {
    ("ref/arcaneschool/divination", "Foretell (Su)", 1):
        "seeded print item: Usage says 1 time/day per wizard level; print gives rounds per day",
}


# ---- level grammar ---------------------------------------------------------------------------

def ordinal_suffix(level: int) -> str:
    return {1: "st", 2: "nd", 3: "rd"}.get(level, "th")


def ordinal(level: int) -> str:
    return f"{level}{ordinal_suffix(level)}"


def well_formed(digits: str, suffix: str) -> int | None:
    """A number from 1 to 20 with no leading zero and its English suffix."""
    if not digits or digits.startswith("0") or not digits.isascii() or not digits.isdigit():
        return None
    level = int(digits)
    return level if 1 <= level <= 20 and suffix == ordinal_suffix(level) else None


LEVEL_HEAD = re.compile(r"At ([0-9]+)(st|nd|rd|th) (level|Level)(.*)", re.S)


@dataclass(frozen=True)
class LevelHead:
    level: int | None
    lowercase: bool
    rest: str


def level_head(text: str) -> LevelHead | None:
    """Detection is broad: `At ` digits suffix space `Level` or `level`. `text` must start so."""
    m = LEVEL_HEAD.fullmatch(text)
    if not m:
        return None
    return LevelHead(well_formed(m.group(1), m.group(2)), m.group(3) == "level", m.group(4))


# ---- blocks ----------------------------------------------------------------------------------

@dataclass(frozen=True)
class Block:
    kind: str                # boundary | lead | row | name | legacy | para
    lines: tuple[str, ...]   # source lines
    start: int               # first source line (index into the body lines)
    text: str                # logical line (see "Span source text")
    label: str = ""          # row label without its colon, or the name
    content: str = ""        # row content, lead sentence, legacy upgrade text
    level: int | None = None
    lowercase: bool = False
    sep: str = ""

    @property
    def end(self) -> int:
        return self.start + len(self.lines)

    @property
    def empty(self) -> bool:
        return self.kind == "row" and not self.content.strip()


def logical(lines) -> str:
    """The lines as one logical line: a hard break (a trailing odd backslash) stays a line break."""
    out = []
    for i, line in enumerate(lines):
        stripped = line.strip(" \t")
        out.append(stripped)
        if i < len(lines) - 1:
            trailing = len(stripped) - len(stripped.rstrip("\\"))
            out.append("\n" if trailing % 2 == 1 else " ")
    return "".join(out)


def split_lines(lines: list[str]) -> list[tuple[int, int]]:
    """The (start, end) line ranges of the body blocks, as `crates/corpus` reads them."""
    out, i, n = [], 0, len(lines)
    while i < n:
        line = lines[i]
        if line.strip(" \t") == "":
            i += 1
            continue
        if line.startswith(":::"):
            j = i + 1
            while j < n and lines[j].strip(" \t") != ":::":
                j += 1
            out.append((i, min(j + 1, n)))
            i = j + 1
            continue
        if re.match(r"^(- |\d+\. )", line):
            j = i + 1
            while j < n:
                if lines[j].strip(" \t") == "":
                    k = j
                    while k < n and lines[k].strip(" \t") == "":
                        k += 1
                    if k < n and lines[k].startswith("  "):
                        j = k
                        continue
                    break
                j += 1
            out.append((i, j))
            i = j
            continue
        if line.startswith((">", "|")):
            j = i
            while j < n and lines[j].startswith(line[0]):
                j += 1
            out.append((i, j))
            i = j
            continue
        j = i
        while j < n and lines[j].strip(" \t") != "":
            j += 1
        out.append((i, j))
        i = j
    return out


STRONG = re.compile(r"\*\*([^*]+)\*\*")


def classify(lines: tuple[str, ...], start: int) -> Block:
    first = lines[0]
    if first.startswith(("#", ":::", ">", "|")) or re.match(r"^(- |\d+\. )", first):
        return Block("boundary", lines, start, "\n".join(lines))
    text = logical(lines)
    strong = STRONG.match(text)
    if strong:
        inner, rest = strong.group(1), text[strong.end():]
        head = level_head(inner)
        if head and head.rest == ",":
            return Block("lead", lines, start, text, label=inner, content=rest.strip(),
                         level=head.level, lowercase=head.lowercase)
        if inner.endswith(":"):
            return Block("row", lines, start, text, label=inner[:-1], content=rest.strip())
        if not rest.strip():
            return Block("name", lines, start, text, label=inner)
    head = level_head(text) if text.startswith("At ") else None
    if head and head.rest[:1] in (":", ","):
        after = head.rest[1:]
        return Block("legacy", lines, start, text, content=after[1:] if after.startswith(" ") else after,
                     level=head.level, lowercase=head.lowercase, sep=head.rest[0])
    return Block("para", lines, start, text)


def parse_blocks(lines: list[str]) -> list[Block]:
    return [classify(tuple(lines[a:b]), a) for a, b in split_lines(lines)]


def row_is_old_upgrade(b: Block) -> LevelHead | None:
    head = level_head(b.label) if b.kind == "row" else None
    return head if head and head.rest == "" else None


def is_numbered_effect_label(label: str) -> bool:
    base = label.rstrip("0123456789")
    return len(base) < len(label) and (
        base in EFFECT_LABELS or base in ALIAS_LABELS or base == ACTION_LABEL)


def is_power_marker(b: Block) -> bool:
    if b.kind in ("lead", "legacy"):
        return True
    if b.kind != "row":
        return False
    return (b.label in ("Gained", ACTION_LABEL) or b.label in EFFECT_LABELS
            or b.label in ALIAS_LABELS or is_numbered_effect_label(b.label)
            or row_is_old_upgrade(b) is not None)


# ---- candidates ------------------------------------------------------------------------------

@dataclass(frozen=True)
class Candidate:
    start: int         # index of the name block
    end: int           # one past the last block
    name: str          # the original name as written (with any colon)
    occurrence: int


def legacy_name(blocks: list[Block], i: int) -> bool:
    """For the rewrite only: an empty row that is the first block of the body or whose label ends
    in an ability tag is a name written with a colon (the magus arcana)."""
    b = blocks[i]
    return b.empty and (i == 0 or ABILITY_TAG.search(b.label) is not None)


def written_name(b: Block) -> str:
    return b.label if b.kind == "name" else b.label + ":"


def candidates(blocks: list[Block], legacy_names: bool = False) -> list[Candidate]:
    """A name directly followed by a row, a lead or a legacy upgrade, then the run to the next
    boundary or name; the run holds a power marker. `legacy_names` adds the rewrite's names."""
    out: list[Candidate] = []
    count: Counter[str] = Counter()
    i = 0
    while i < len(blocks):
        named = blocks[i].kind == "name" or (legacy_names and legacy_name(blocks, i))
        if named and i + 1 < len(blocks) and blocks[i + 1].kind in ("row", "lead", "legacy"):
            j = i + 1
            while j < len(blocks) and blocks[j].kind not in ("boundary", "name"):
                j += 1
            if any(is_power_marker(b) for b in blocks[i + 1:j]):
                name = written_name(blocks[i])
                count[name] += 1
                out.append(Candidate(i, j, name, count[name]))
                i = j
                continue
        i += 1
    return out


# ---- validation (mirrors cast_iron_schema::power::validate_power) ----------------------------

RANK = {"Gained": 2, "Flavor": 3, "Usage": 6, "Prereq": 8, "Replaces": 9}
RANK_EFFECT, RANK_UPGRADE, RANK_OTHER = 4, 7, 10


def gained_level(content: str) -> int | None:
    head = level_head(content.strip())
    return head.level if head and head.rest == "" and not head.lowercase else None


def validate(run: list[Block]) -> list[str]:
    """The problems of one candidate (the name block, then its run), as slugs. Empty is valid."""
    problems: list[str] = []

    def note(slug: str) -> None:
        if slug not in problems:
            problems.append(slug)

    if run[0].kind != "name":
        note("not-a-name")
    body = run[1:]
    if any(b.kind in ("name", "boundary") for b in body):
        note("block-in-span")
    gained = next((gained_level(b.content) for b in body if b.kind == "row" and b.label == "Gained"), None)
    last_rank, seen, effect_rows, after_effect, last_up = 1, set(), 0, False, None
    for b in body:
        if b.kind == "row":
            label = b.label
            after_effect = False
            if b.empty:
                note("empty-row")
            if label in EFFECT_LABELS or label in ALIAS_LABELS:
                effect_rows += 1
                after_effect = True
                if label in ALIAS_LABELS:
                    note("legacy-label")
                if effect_rows > 1:
                    note("multiple-effect-rows")
                else:
                    if last_rank > RANK_EFFECT:
                        note("out-of-order")
                    last_rank = max(last_rank, RANK_EFFECT)
                continue
            if is_numbered_effect_label(label):
                note("numbered-effect-label")
                continue
            if label == ACTION_LABEL or row_is_old_upgrade(b):
                note("legacy-label")
                continue
            rank = RANK.get(label, RANK_OTHER)
            if rank != RANK_OTHER:
                if label in seen:
                    note("second-singleton-row")
                    continue
                seen.add(label)
            if rank < last_rank:
                note("out-of-order")
            last_rank = max(last_rank, rank)
            if label == "Gained" and gained_level(b.content) is None:
                note("non-canonical-gained")
        elif b.kind == "lead":
            after_effect = False
            if not (b.level is not None and b.lowercase and b.content):
                note("non-canonical-lead")
                continue
            if gained is not None and b.level <= gained:
                note("upgrade-not-above-gained")
            if last_up is not None and b.level == last_up:
                note("upgrade-at-same-level")
            elif last_up is not None and b.level < last_up:
                note("upgrades-not-ascending")
            last_up = b.level
            if last_rank > RANK_UPGRADE:
                note("out-of-order")
            last_rank = max(last_rank, RANK_UPGRADE)
        elif b.kind == "legacy":
            after_effect = False
            note("legacy-upgrade")
        elif b.kind == "para":
            if not after_effect:
                note("stray-paragraph")
    if effect_rows == 0:
        note("no-effect-row")
    return problems


def map_action(content: str):
    """What the value of an `**Action:** value` row becomes: ("effect", label), ("gained", level)
    or ("unmapped", None). The value must be plain text."""
    if re.search(r"[*_\[\]\\`]", content):
        return "unmapped", None
    value = content.strip()
    if value in ACTION_EFFECT:
        return "effect", ACTION_EFFECT[value]
    head = level_head(value)
    if head and head.rest == "" and not head.lowercase and head.level is not None:
        return "gained", head.level
    return "unmapped", None


# ---- the rewrite -----------------------------------------------------------------------------

def lower_first(text: str) -> tuple[str, str | None]:
    """Lowercase the first word of an upgrade sentence when it is on the lowercase list. Returns
    the text and the word that keeps a capital (so the power is queued), or None."""
    m = re.match(r"[A-Za-z]+", text)
    if m:
        word = m.group(0)
        if word in LOWERCASE_FIRST:
            return word.lower() + text[len(word):], None
        return text, word if word[0].isupper() else None
    visible = re.sub(r"^[\[\]*_\\`(]+", "", text)
    return text, (visible.split(" ")[0] if visible[:1].isupper() else None)


@dataclass
class Item:
    kind: str                       # row | action | up | para
    label: str = ""
    content: str = ""
    level: int = 0
    block: Block | None = None
    lines: tuple[str, ...] = ()     # the emitted block, one entry per source line
    canonical_lead: bool = False


def rewrite_run(run: list[Block]) -> tuple[list[tuple[str, ...]] | None, list[str]]:
    """The canonical blocks of a failing candidate, or None and the reasons it is queued. A
    reason is `code` or `code: detail`. The run's blocks are never altered."""
    q: list[str] = []
    name_block = run[0]
    if name_block.kind == "name":
        name_lines = name_block.lines
    else:
        name_lines = (f"**{name_block.label}**",)

    # 1. Deduplicate identical original Usage rows. This is the only deduplication.
    body, seen_usage = [], set()
    for b in run[1:]:
        if b.kind == "row" and b.label == "Usage":
            if b.text in seen_usage:
                continue
            seen_usage.add(b.text)
        body.append(b)

    # 2. Map each block. Items keep their source order.
    items: list[Item] = []
    for b in body:
        if b.kind == "row":
            label = b.label
            if b.empty:
                q.append(f"empty-row: {label}")
                continue
            old = row_is_old_upgrade(b)
            if old is not None:
                if old.level is None:
                    q.append(f"ill-formed-level: {label}")
                else:
                    items.append(Item("up", content=b.content, level=old.level, block=b))
            elif label == ACTION_LABEL:
                kind, value = map_action(b.content)
                if kind == "gained":
                    text = f"**Gained:** At {ordinal(value)} Level"
                    items.append(Item("row", "Gained", f"At {ordinal(value)} Level", block=b, lines=(text,)))
                elif kind == "effect":
                    items.append(Item("action", value, block=b))
                else:
                    q.append(f"unmapped-action: {b.content.strip()}")
            elif is_numbered_effect_label(label):
                q.append(f"numbered-effect-label: {label}")
            elif label in ALIAS_LABELS:
                new = ALIAS_LABELS[label]
                items.append(Item("row", new, b.content, block=b, lines=(f"**{new}:** {b.content}",)))
            else:
                items.append(Item("row", label, b.content, block=b, lines=b.lines))
        elif b.kind == "lead":
            if b.level is None or not b.lowercase or not b.content:
                q.append("non-canonical-lead")
            else:
                items.append(Item("up", content=b.content, level=b.level, block=b, lines=b.lines,
                                  canonical_lead=True))
        elif b.kind == "legacy":
            if b.sep != ":":
                q.append("comma-upgrade")
            elif b.level is None:
                q.append("ill-formed-level")
            elif not b.content.strip():
                q.append("empty-upgrade")
            else:
                items.append(Item("up", content=b.content, level=b.level, block=b))
        else:
            items.append(Item("para", block=b, lines=b.lines))

    for singleton in SINGLETONS:
        if sum(1 for it in items if it.kind == "row" and it.label == singleton) > 1:
            q.append(f"conflicting-rows: {singleton}")
    effects = [k for k, it in enumerate(items)
               if (it.kind == "row" and it.label in EFFECT_LABELS) or it.kind == "action"]
    ups = [it for it in items if it.kind == "up"]
    has_gained = any(it.kind == "row" and it.label == "Gained" for it in items)
    if not effects:
        q.append("no-effect-row" + (": suggest the lowest upgrade as Gained level and base effect"
                                    if ups and not has_gained else ""))
    elif len(effects) > 1:
        q.append("multiple-effect-rows")

    # 3. Paragraph groups: consecutive unlabeled paragraphs.
    groups: list[list[int]] = []
    current: list[int] = []
    for k, it in enumerate(items):
        if it.kind == "para":
            current.append(k)
        elif current:
            groups.append(current)
            current = []
    if current:
        groups.append(current)
    effect_lines: tuple[str, ...] = ()
    continuation: list[tuple[str, ...]] = []
    if len(effects) == 1:
        e = effects[0]
        eff = items[e]
        if eff.kind == "action":
            if len(groups) != 1 or groups[0][0] < e:
                q.append("action-without-one-group")
            elif any(not (items[k].kind == "row" and items[k].label in CROSSABLE)
                     for k in range(e + 1, groups[0][0])):
                q.append("action-group-crosses-row")
            else:
                first = items[groups[0][0]].block
                effect_lines = (f"**{eff.label}:** {first.text}",)
                continuation = [items[k].lines for k in groups[0][1:]]
        else:
            effect_lines = eff.lines
            if len(groups) > 1 or (groups and groups[0][0] != e + 1):
                q.append("unlabeled-paragraphs-not-after-effect")
            elif groups:
                continuation = [items[k].lines for k in groups[0]]

    # 4. Upgrades, ascending, with the printed sentence after the lead.
    gained = next((gained_level(it.content) for it in items
                   if it.kind == "row" and it.label == "Gained"), None)
    levels = [it.level for it in ups]
    if len(set(levels)) != len(levels):
        q.append("two-upgrades-at-one-level")
    up_lines: list[tuple[str, ...]] = []
    for it in sorted(ups, key=lambda it: it.level):
        if gained is not None and it.level <= gained:
            q.append(f"upgrade-not-above-gained: {it.level}")
        if it.canonical_lead:
            up_lines.append(it.lines)
            continue
        text, capital = lower_first(it.content)
        if capital is not None:
            q.append(f"upgrade-keeps-capital: {capital}")
        up_lines.append((f"**At {ordinal(it.level)} level,** {text}",))
    if q:
        return None, q

    # 5. Emit in canonical order. Other rows keep their source order.
    rows = [it for it in items if it.kind == "row"]
    pick = lambda label: [it.lines for it in rows if it.label == label]
    tail = [it.lines for it in rows if it.label not in SINGLETONS and it.label not in EFFECT_LABELS]
    out = ([name_lines] + pick("Gained") + pick("Flavor") + [effect_lines] + continuation
           + pick("Usage") + up_lines + pick("Prereq") + pick("Replaces") + tail)
    problems = validate(parse_blocks(join_blocks(out)))
    if problems:
        return None, ["replacement-fails-validation: " + ", ".join(problems)]
    return out, []


def join_blocks(blocks) -> list[str]:
    """Source lines of blocks, separated by one blank line."""
    lines: list[str] = []
    for k, b in enumerate(blocks):
        if k:
            lines.append("")
        lines.extend(b)
    return lines


def span_text(run: list[Block]) -> str:
    return "\n\n".join(b.text for b in run)


def span_sha(run: list[Block]) -> str:
    return hashlib.sha256(span_text(run).encode()).hexdigest()


# ---- resolutions -----------------------------------------------------------------------------

@dataclass(frozen=True)
class Resolution:
    id: str
    name: str
    occurrence: int
    span_sha256: str
    print: str
    replacement: str


def load_resolutions(path: Path) -> dict[tuple[str, str, int], Resolution]:
    if not path.exists():
        return {}
    data = tomllib.loads(path.read_text())
    out: dict[tuple[str, str, int], Resolution] = {}
    for r in data.get("resolution", []):
        res = Resolution(r["id"], r["name"], r["occurrence"], r["span_sha256"], r["print"], r["replacement"])
        key = (res.id, res.name, res.occurrence)
        if key in out:
            raise SystemExit(f"{path}: two resolutions for {key}")
        out[key] = res
    return out


def resolution_blocks(res: Resolution) -> list[Block]:
    return parse_blocks(res.replacement.strip("\n").split("\n"))


def check_resolution(res: Resolution) -> list[str]:
    """A replacement starts with a candidate, and every candidate in it passes validation. Blocks
    after the last candidate's boundary are free: a power that print sets as a bulleted list keeps
    the list after the power (Utility Shot)."""
    blocks = resolution_blocks(res)
    cands = candidates(blocks)
    if not cands or cands[0].start != 0:
        return ["the replacement does not start with a power"]
    out = []
    for c in cands:
        problems = validate(blocks[c.start:c.end])
        if problems:
            out.append(f"{blocks[c.start].label}: {', '.join(problems)}")
    return out


# ---- one entry -------------------------------------------------------------------------------

@dataclass
class Outcome:
    entry_id: str
    name: str
    occurrence: int
    status: str            # valid | rewritten | queued | resolved | resolution-noop | stale
    reasons: list[str]
    sha: str


def process_body(entry_id: str, lines: list[str], resolutions) -> tuple[list[str], list[Outcome]]:
    blocks = parse_blocks(lines)
    outcomes: list[Outcome] = []
    out: list[str] = []
    cursor = 0   # the next source line not yet copied
    for c in candidates(blocks, legacy_names=True):
        run = blocks[c.start:c.end]
        sha = span_sha(run)
        key = (entry_id, c.name, c.occurrence)
        replacement: list[tuple[str, ...]] | None = None
        status, reasons = "valid", []
        res = resolutions.get(key)
        if res and res.span_sha256 == sha:
            replacement = [tuple(b.lines) for b in resolution_blocks(res)]
            status = "resolved"
        elif res and span_text(run) == span_text(resolution_blocks(res)):
            status = "resolution-noop"
        else:
            if res:
                outcomes.append(Outcome(entry_id, c.name, c.occurrence, "stale", ["stale-resolution"], sha))
            if not validate(run):
                status = "valid"
            elif key in PRINT_ITEMS:
                status, reasons = "queued", ["print-review: " + PRINT_ITEMS[key]]
            else:
                new, reasons = rewrite_run(run)
                if reasons:
                    status = "queued"
                else:
                    status, replacement = "rewritten", new
        outcomes.append(Outcome(entry_id, c.name, c.occurrence, status, reasons, sha))
        if replacement is not None:
            out.extend(lines[cursor:run[0].start])
            out.extend(join_blocks(replacement))
            cursor = run[-1].end
    out.extend(lines[cursor:])
    return out, outcomes


# ---- the corpus ------------------------------------------------------------------------------

def class_option_entries(corpus: Path):
    """(entry id, path, text) of every class-option entry, in id order."""
    found = []
    for path in sorted((corpus / "entries").rglob("*.md")):
        text = path.read_text()
        if 'kind = "class_option"' not in text:
            continue
        parts = text.split("+++\n", 2)
        if len(parts) != 3:
            continue
        front = tomllib.loads(parts[1])
        if front.get("kind") == "class_option":
            found.append((front["id"], path, parts))
    found.sort(key=lambda e: e[0])
    return found


def run_corpus(corpus: Path, resolutions, families=None, write=False):
    outcomes: list[Outcome] = []
    changed: list[Path] = []
    for entry_id, path, parts in class_option_entries(corpus):
        body = parts[2].split("\n")
        new, found = process_body(entry_id, body, resolutions)
        outcomes.extend(found)
        family = entry_id.split("/")[1]
        if new != body and (families is None or family in families):
            changed.append(path)
            if write:
                path.write_text(parts[0] + "+++\n" + parts[1] + "+++\n" + "\n".join(new))
    return outcomes, changed


def queue_text(outcomes: list[Outcome]) -> str:
    rows = [QUEUE_HEADER]
    for o in outcomes:
        if o.status == "queued":
            reasons = re.sub(r"\s+", " ", "; ".join(o.reasons))
            rows.append("\t".join((o.entry_id, o.name, str(o.occurrence), o.sha, reasons)))
    return "\n".join(rows) + "\n"


def summarize(outcomes: list[Outcome], changed: list[Path]) -> str:
    status = Counter(o.status for o in outcomes)
    reasons: Counter[str] = Counter()
    for o in outcomes:
        if o.status == "queued":
            for code in {r.split(":")[0] for r in o.reasons}:
                reasons[code] += 1
    lines = [f"candidates (rewrite discovery): {sum(v for k, v in status.items() if k != 'stale')}"]
    for key in ("valid", "rewritten", "queued", "resolved", "resolution-noop", "stale"):
        lines.append(f"  {key}: {status.get(key, 0)}")
    lines.append(f"entries changed: {len(changed)}")
    lines.append("queued by reason (a power can have several):")
    lines.extend(f"  {code}: {n}" for code, n in sorted(reasons.items(), key=lambda kv: (-kv[1], kv[0])))
    return "\n".join(lines)


# ---- self-test: the fixtures of the decision ---------------------------------------------------
# Each body has the structure of the named corpus entry (same rows, same order, same defect) with
# short placeholder wording, so the test does not depend on the corpus, which the rewrite changes.
# The occurrence is the position among the candidates with the same name in the entry.

HAUNT = (
    "**Haunt Channeler (Su)**\n\n**Gained:** At 1st Level\n\n**Ability:** You channel a haunt.\n\n"
    "**Haunt Channeler (Su)**\n\n**Ability:** You channel.\n\n**Ability2:** You channel more.\n\n"
    "**Standard:** You channel a third way.\n")

# (entry id, original name, occurrence, expected, reason code, body). `valid` is the decision's
# `canonical`: the span already passes validation and stays unchanged.
FIXTURES = [
    ("ref/discovery/elixir-of-life", "Elixir of Life", 1, "valid", None,
     "**Elixir of Life**\n\n**Ability:** First paragraph.\n\nOne continuation paragraph.\n\n"
     "**Prereq:** Level 11\n"),
    ("ref/arcaneschool/abjuration", "Resistance (Ex)", 1, "rewritten", None,
     "**Resistance (Ex)**\n\n**At 11th Level:** This resistance increases to 10.\n\n"
     "**At 20th Level:** This resistance changes to immunity.\n\n**Gained:** At 1st Level\n\n"
     "**Passive:** You gain resistance 5.\n"),
    ("ref/arcaneschool/abjuration", "Counterspell Mastery", 1, "queued", "multiple-effect-rows",
     "**Counterspell Mastery**\n\n**Gained:** At 8th Level\n\n**Ability:** You can counter.\n\n"
     "**Immediate:** You counter a spell.\n"),
    ("ref/aspect/giant-wasp", "Minor Form", 1, "rewritten", None,
     "**Minor Form**\n\n**Passive:** You gain a sting.\n\nAt 8th level: The sting grows.\n\n"
     "At 12th level: The sting grows again.\n"),
    ("ref/deed/utility-shot", "Utility Shot (Ex)", 1, "queued", "empty-row",
     "**Utility Shot (Ex)**\n\n**Ability:** You choose one shot.\n\n**Blast Lock:**\n\n"
     "**Scoot Unattended Object:**\n\n**Stop Bleeding:**\n"),
    ("ref/blrgbloodline/fey", "One with Nature (Su)", 1, "queued", "unmapped-action",
     "**One with Nature (Su)**\n\n**Action:** Move-Equivalent Action\n\nYou become one with nature.\n"),
    ("ref/hex/coven", "Coven (Ex)", 1, "queued", "numbered-effect-label",
     "**Coven (Ex)**\n\n**Ability:** One effect.\n\n**Ability2:** Another effect.\n"),
    ("ref/mystery/flame", "Firestorm (Su)", 1, "rewritten", None,
     "**Firestorm (Su)**\n\n**Gained:** At 15th Level\n\n**Usage:** 1/day\n\n"
     "**Prereq:** 15th-level oracle\n\n**Standard:** You call fire.\n\n**Usage:** 1/day\n"),
    ("ref/mystery/reaper", "Haunt Channeler (Su)", 1, "valid", None, HAUNT),
    ("ref/mystery/reaper", "Haunt Channeler (Su)", 2, "queued", "numbered-effect-label", HAUNT),
    ("ref/arcaneschool/divination", "Foretell (Su)", 1, "queued", "print-review",
     "**Foretell (Su)**\n\n**Action:** Standard Action\n\n**Gained:** At 8th Level\n\n"
     "**Usage:** 1 time/day per wizard level\n\nYou foretell.\n"),
    ("ref/arcaneschool/divination", "Forewarned (Su)", 1, "queued", "upgrade-keeps-capital",
     "**Forewarned (Su)**\n\n**At 20th Level:** Anytime you roll initiative, you act.\n\n"
     "**Gained:** At 1st Level\n\n**Passive:** You are forewarned.\n"),
    ("ref/ragepower/auspicious-mark", "Auspicious Mark (Su)", 1, "rewritten", None,
     "**Auspicious Mark (Su)**\n\n**Flavor:** The mark glows.\n\n**Usage:** Once per rage\n\n"
     "**Swift:** You mark a foe.\n\n**Special:** Stacks.\n\n**Usage:** Once per rage\n"),
    ("ref/hex/evil-eye", "Evil Eye (Su)", 1, "rewritten", None,
     "**Evil Eye (Su)**\n\n**Ability:** You curse a foe.\n\n**Flavor:** Your gaze is cold.\n\n"
     "At 8th level: The penalty grows.\n"),
    ("ref/hex/flight", "Flight (Su)", 1, "queued", "no-effect-row",
     "**Flight (Su)**\n\n**At 1st Level:** You fly.\n\n**At 5th Level:** You fly faster.\n"),
    ("ref/domain/fire", "Fire Resistance (Ex)", 1, "queued", "no-effect-row",
     "**Fire Resistance (Ex)**\n\n**At 6th Level:** You gain fire resistance 10.\n"),
    ("ref/hex/blight", "Blight (Su)", 1, "queued", "action-group-crosses-row",
     "**Blight (Su)**\n\n**Action:** Standard Action\n\n**Special:** A limit.\n\nYou blight a plant.\n"),
    ("ref/arcana/accurate-strike", "Accurate Strike (Ex):", 1, "rewritten", None,
     "**Accurate Strike (Ex):**\n\n**Ability:** You strike accurately.\n"),
    ("ref/talent/black-market-connections", "Black Market Connection (Ex)", 1, "rewritten", None,
     "**Black Market Connection (Ex)**\n\n**Action:** Ability\n\nYou know a dealer.\n"),
    ("S1", "Twin Strike (Ex)", 1, "queued", "multiple-effect-rows",
     "**Twin Strike (Ex)**\n\n**Fullround:** You strike twice.\n\n**Full-round:** You strike twice.\n"),
    ("S2", "Quiet Step (Ex)", 1, "queued", "empty-row",
     "**Quiet Step (Ex)**\n\n**Ability:** You move silently.\n\n**Usage:**\n"),
    ("S3", "Resistance (Ex)", 1, "valid", None,
     "**Resistance (Ex)**\n\n**Gained:** At 1st Level\n\n**Passive:** You gain resistance 5.\n\n"
     "**At 11th level,** this resistance increases to 10.\n"),
]

# The exact text of the rewritten fixtures: (entry id, name, expected lines).
EXACT = {
    ("ref/arcaneschool/abjuration", "Resistance (Ex)"): (
        "**Resistance (Ex)**\n\n**Gained:** At 1st Level\n\n**Passive:** You gain resistance 5.\n\n"
        "**At 11th level,** this resistance increases to 10.\n\n"
        "**At 20th level,** this resistance changes to immunity.\n"),
    ("ref/aspect/giant-wasp", "Minor Form"): (
        "**Minor Form**\n\n**Passive:** You gain a sting.\n\n**At 8th level,** the sting grows.\n\n"
        "**At 12th level,** the sting grows again.\n"),
    ("ref/mystery/flame", "Firestorm (Su)"): (
        "**Firestorm (Su)**\n\n**Gained:** At 15th Level\n\n**Standard:** You call fire.\n\n"
        "**Usage:** 1/day\n\n**Prereq:** 15th-level oracle\n"),
    ("ref/ragepower/auspicious-mark", "Auspicious Mark (Su)"): (
        "**Auspicious Mark (Su)**\n\n**Flavor:** The mark glows.\n\n**Swift:** You mark a foe.\n\n"
        "**Usage:** Once per rage\n\n**Special:** Stacks.\n"),
    ("ref/hex/evil-eye", "Evil Eye (Su)"): (
        "**Evil Eye (Su)**\n\n**Flavor:** Your gaze is cold.\n\n**Ability:** You curse a foe.\n\n"
        "**At 8th level,** the penalty grows.\n"),
    ("ref/arcana/accurate-strike", "Accurate Strike (Ex):"): (
        "**Accurate Strike (Ex)**\n\n**Ability:** You strike accurately.\n"),
    ("ref/talent/black-market-connections", "Black Market Connection (Ex)"): (
        "**Black Market Connection (Ex)**\n\n**Ability:** You know a dealer.\n"),
}


def run_fixture(entry_id, name, occurrence, body):
    """(outcome, new body, index of the candidate), for one fixture."""
    lines = body.split("\n")
    new, outcomes = process_body(entry_id, lines, {})
    found = [o for o in outcomes if o.status != "stale"]
    for index, o in enumerate(found):
        if o.name == name and o.occurrence == occurrence:
            return o, new, index
    raise AssertionError(f"{name} #{occurrence} is not a candidate")


def self_test() -> int:
    failures: list[str] = []

    def expect(ok: bool, message: str) -> None:
        if not ok:
            failures.append(message)

    for entry_id, name, occ, expected, code, body in FIXTURES:
        label = f"{entry_id} {name} #{occ}"
        o, new, index = run_fixture(entry_id, name, occ, body)
        expect(o.status == expected, f"{label}: expected {expected}, got {o.status} {o.reasons}")
        if code:
            expect(any(r.split(":")[0] == code for r in o.reasons),
                   f"{label}: expected reason {code}, got {o.reasons}")
        blocks = parse_blocks(new)
        cands = candidates(blocks, legacy_names=True)
        span = blocks[cands[index].start:cands[index].end]
        if expected == "queued":
            # The whole span stays unchanged: here, the whole body.
            expect(new == body.split("\n"), f"{label}: a queued body must stay unchanged")
        else:
            expect(not validate(span), f"{label}: the result must validate: {validate(span)}")
        if expected == "valid":
            expect(new == body.split("\n"), f"{label}: a valid body must stay unchanged")
        if (entry_id, name) in EXACT:
            expect("\n".join(new) == EXACT[(entry_id, name)],
                   f"{label}: wrong output:\n" + "\n".join(new))
        if expected in ("valid", "rewritten"):
            again, outs = process_body(entry_id, new, {})
            expect(again == new, f"{label}: a second pass changed the text")
            expect(outs[index].status == "valid", f"{label}: the second pass must find it valid")

    # The lowercase list: a listed first word is lowercased, `Anytime` is not listed (Forewarned).
    new, _ = process_body("x", "**P (Su)**\n\n**Passive:** Text.\n\nAt 5th level: You gain a bonus.\n".split("\n"), {})
    expect("**At 5th level,** you gain a bonus." in new, f"lowercase list: {new}")
    o, _, _ = run_fixture("x", "P (Su)", 1, "**P (Su)**\n\n**Passive:** Text.\n\nAt 5th level: Anytime you gain.\n")
    expect(o.status == "queued" and o.reasons == ["upgrade-keeps-capital: Anytime"], f"Anytime: {o}")
    # The comma form and an ill-formed ordinal are queued.
    o, _, _ = run_fixture("x", "P (Su)", 1, "**P (Su)**\n\n**Passive:** Text.\n\nAt 5th level, you gain.\n")
    expect(o.status == "queued" and o.reasons == ["comma-upgrade"], f"comma form: {o}")
    o, _, _ = run_fixture("x", "P (Su)", 1, "**P (Su)**\n\n**Passive:** Text.\n\n**At 5st Level:** you gain.\n")
    expect(o.status == "queued" and o.reasons[0].startswith("ill-formed-level"), f"ordinal: {o}")

    # Resolutions: the Foretell seed holds until a resolution matches the exact span hash; an applied
    # resolution is a no-op; a changed span is a stale resolution, queued again.
    foretell = FIXTURES[10][5]
    body = foretell.split("\n")
    blocks = parse_blocks(body)
    c = candidates(blocks, True)[0]
    text = ("**Foretell (Su)**\n\n**Gained:** At 8th Level\n\n**Standard:** You foretell.\n\n"
            "**Usage:** Rounds per day equal to your level\n")
    res = Resolution("ref/arcaneschool/divination", "Foretell (Su)", 1, span_sha(blocks[c.start:c.end]),
                     "a book and page", text)
    resolutions = {(res.id, res.name, 1): res}
    expect(not check_resolution(res), f"the resolution must validate: {check_resolution(res)}")
    new, outs = process_body(res.id, body, resolutions)
    expect(outs[0].status == "resolved" and "\n".join(new) == text, f"a matching resolution applies: {outs}")
    again, outs = process_body(res.id, new, resolutions)
    expect(again == new and [o.status for o in outs] == ["resolution-noop"],
           f"an applied resolution is a no-op: {outs}")
    changed = [line.replace("1 time/day", "2 times/day") for line in body]
    again, outs = process_body(res.id, changed, resolutions)
    expect(again == changed and [o.status for o in outs][0] == "stale", f"a changed span is stale: {outs}")
    expect(outs[1].status == "queued", f"a stale resolution is queued again: {outs}")
    bad = Resolution(res.id, res.name, 1, res.span_sha256, "x", "**Foretell (Su)**\n\n**Gained:** At 8th Level\n")
    expect(check_resolution(bad) != [], "a replacement that fails validation is refused")
    listed = Resolution(res.id, res.name, 1, res.span_sha256, "x", text + "\n- **Option:** A bullet of print.\n")
    expect(check_resolution(listed) == [], "a valid power followed by a list is accepted")
    bare = Resolution(res.id, res.name, 1, res.span_sha256, "x", "A paragraph.\n\n" + text)
    expect(check_resolution(bare) != [], "a replacement must start with a power")

    # Hash: it does not depend on how a paragraph is wrapped.
    wrapped = parse_blocks("**N (Su)**\n\n**Passive:** one two\nthree four\n".split("\n"))
    flat = parse_blocks("**N (Su)**\n\n**Passive:** one two three four\n".split("\n"))
    expect(span_sha(wrapped[:2]) == span_sha(flat[:2]), "the span hash must not depend on wrapping")

    for message in failures:
        print("FAIL", message)
    print(f"self-test: {len(FIXTURES)} fixtures, {len(failures)} failures")
    return 1 if failures else 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("corpus", nargs="?", default=str(Path(__file__).resolve().parent.parent))
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--write", action="store_true", help="rewrite the entries and write the queue file")
    ap.add_argument("--write-queue", action="store_true", help="write the queue file only")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--families", help="comma-separated families to rewrite, e.g. mystery,oraclecurse")
    args = ap.parse_args()
    if args.self_test:
        return self_test()
    corpus = Path(args.corpus)
    families = set(args.families.split(",")) if args.families else None
    resolutions = load_resolutions(corpus / RESOLUTIONS_FILE)
    bad = [f"{r.id} {r.name} #{r.occurrence}: {m}" for r in resolutions.values() for m in check_resolution(r)]
    if bad:
        print("\n".join("invalid resolution: " + b for b in bad))
        return 1
    outcomes, changed = run_corpus(corpus, resolutions, families, write=args.write)
    print(summarize(outcomes, changed))
    stale = [o for o in outcomes if o.status == "stale"]
    for o in stale:
        print(f"stale resolution: {o.entry_id} {o.name} #{o.occurrence}")
    queue = corpus / QUEUE_FILE
    if args.write or args.write_queue:
        queue.write_text(queue_text(outcomes))
        return 1 if stale else 0
    if args.check:
        current = queue.read_text() if queue.exists() else ""
        problems = []
        if changed:
            problems.append(f"{len(changed)} entries would change")
        if current != queue_text(outcomes):
            problems.append(f"{QUEUE_FILE} is out of date")
        if stale:
            problems.append(f"{len(stale)} stale resolutions")
        for p in problems:
            print("check:", p)
        return 1 if problems else 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
