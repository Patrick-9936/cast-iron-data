#!/usr/bin/env python3
"""Drop the headings and bold paragraphs that repeat the entry title (issue #168).

The page already shows the title as its `h1`. A body that opens with the same words again, alone or
followed by the entry's own classification, repeats it. Seven passes find those repeats; six remove
them and `misc-rule` only queues. Each pass removes only text that the entry states elsewhere, and
queues every entry it cannot decide.

  creature        `**Owlbear**`, the bold paragraph that names a creature (`ref/monster/`,
                  `ref/npc/`). It is the first paragraph, or the second when an italic flavour
                  paragraph precedes it. Dropped when it equals the title, or the title without
                  its trailing disambiguation in parentheses (`Avoral (Agathion)` -> `Avoral`).
  trap-template   the same paragraph of the Pf Data traps and templates (`ref/trap/`,
                  `ref/template/`), where it is the first paragraph.
  feat-heading    `## Power Attack (Combat)`: the first heading of a feat, when it is the title plus
                  a parenthesis whose comma-separated words equal `feat_types`, in any order.
                  The types stay in `[fields] feat_types`; the app shows them in the facts line
                  (phynics/cast-iron#609). Merge that PR first.
  mythic          The PSRD mythic feat bodies (`entries/carried/mythic-adventures/feats/*/mythic.md`)
                  take the Pf Data form of a base feat: the flavour line, plain, then the
                  `**Prerequisites:**`, `**Benefit:**` and `**Special:**` lines as one paragraph
                  with hard breaks. The `Type:` stat block is dropped when its words equal
                  `feat_types`. The `[fields]` text must equal the line it sits beside, so the
                  drift check keeps comparing them. Needs phynics/cast-iron#609 (feat types in the
                  facts line).
                  A Benefit of several paragraphs (#183): `[fields] benefit` is cut to the first
                  paragraph, as in the Pf Data feats, and the other paragraphs follow the
                  converted paragraph as plain paragraphs, then any `###` subsections. A field
                  that holds the whole text is cut at the end of the first paragraph; the words
                  and paragraph breaks of the body must not change (`same_print`).
  deity-haunt     the same bold paragraph of the deities and haunts (`ref/faith/`, `ref/haunt/`; #184),
                  by the creature rule: the first paragraph, or the second after an italic
                  one, equal to the title or to the title without its trailing parenthesis.
  misc-rule       the same bold paragraph of the `ref/misc/` and `ref/rule/` entries (#184). It
                  only queues: in a rule entry that covers several topics the bold paragraph can
                  label the first subsection, so no entry changes until a review row says that it
                  is an echo. A row names the bold text and the start of the block after it.
  trait-type      `**Type:** Regional`: the first paragraph of a trait, when it equals
                  `TraitFields.category` (and `detail`, when present: `Category (Detail)`).
                  The category is in the metadata line (phynics/cast-iron#609). Merge that PR first.

A later heading that repeats the title inside a section stays, as does every other block of a
body. No `id` changes and no file moves.

`scripts/title-echoes-review-168.tsv` lists every entry that a pass found and left as printed,
with the reason. The file always covers all passes.

Usage, from the corpus root:

    python3 -I scripts/title-echoes-168.py                 survey: counts per pass
    python3 -I scripts/title-echoes-168.py --write         apply every pass, write the review file
    python3 -I scripts/title-echoes-168.py --write --pass feat-heading,trait-type
    python3 -I scripts/title-echoes-168.py --check         exit 1 unless a rerun changes nothing
    python3 -I scripts/title-echoes-168.py --self-test

`--pass` limits which entries change; the review file is written in full. After `--write` run
`cargo xtask corpus-fmt <dir>` and `cargo xtask corpus-check <dir>` (phynics/cast-iron).
"""

from __future__ import annotations

import argparse
import re
import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path

FRONT = re.compile(r"\A\+\+\+\n(.*?)\n\+\+\+\n", re.S)
PASSES = (
    "creature",
    "trap-template",
    "feat-heading",
    "mythic",
    "trait-type",
    "deity-haunt",
    "misc-rule",
)
REVIEW = "scripts/title-echoes-review-168.tsv"
BLOCK = re.compile(r"(.*?)(\n{2,})(.*)\Z", re.S)
BOLD_ONLY = re.compile(r"\*\*([^*\n]+)\*\*")
MYTHIC_PATH = re.compile(r"entries/carried/mythic-adventures/feats/[^/]+/mythic\.md\Z")


@dataclass
class Result:
    """What a pass decided about one entry: a new text, or a reason to leave it."""

    text: str | None = None
    reason: str | None = None


def first_blocks(rest: str) -> list[tuple[str, str]]:
    """The first two blocks of a body as `(block, separator after it)`, last block unseparated."""
    out: list[tuple[str, str]] = []
    for _ in range(2):
        match = BLOCK.match(rest)
        if match is None:
            out.append((rest.rstrip("\n"), ""))
            return out
        out.append((match.group(1), match.group(2)))
        rest = match.group(3)
    return out


def split_body(text: str) -> tuple[str, str, str]:
    """`(front matter, blank lines before the body, body)`."""
    front = FRONT.match(text)
    assert front is not None
    body = text[front.end() :]
    stripped = body.lstrip("\n")
    return text[: front.end()], body[: len(body) - len(stripped)], stripped


def drop_first_line(text: str) -> str | None:
    """`text` without the first line of its body, and the blank lines after it.

    A heading or a `**Type:**` line ends at the line break, so text that follows it without a
    blank line is a block of its own and stays. `None` if nothing is left.
    """
    head, lead, rest = split_body(text)
    _line, _, tail = rest.partition("\n")
    tail = tail.lstrip("\n")
    return head + lead + tail if tail.strip() else None


def drop_blocks(text: str, indexes: tuple[int, ...]) -> str | None:
    """`text` without the blocks at `indexes` (0 or 1) of its body; `None` if nothing is left."""
    head, lead, rest = split_body(text)
    match = BLOCK.match(rest)
    if match is None:
        return None
    first, sep0, tail = match.groups()
    if indexes == (0,):
        return head + lead + tail
    second = BLOCK.match(tail)
    if second is None:
        return None
    return head + lead + first + sep0 + second.group(3)


def without_disambiguation(title: str) -> str:
    return re.sub(r" \([^()]*\)\Z", "", title)


# ---------------------------------------------------------------------------------------------
# the passes
# ---------------------------------------------------------------------------------------------


def bold_title(text: str, data: dict) -> Result | None:
    """creature and trap-template: the bold paragraph that names the entry."""
    _head, _lead, rest = split_body(text)
    blocks = first_blocks(rest)
    index = None
    if BOLD_ONLY.fullmatch(blocks[0][0]):
        index = 0
    elif (
        len(blocks) > 1
        and blocks[0][0].startswith("_")
        and blocks[0][0].endswith("_")
        and BOLD_ONLY.fullmatch(blocks[1][0])
    ):
        index = 1
    if index is None:
        return None
    name = BOLD_ONLY.fullmatch(blocks[index][0]).group(1).strip()
    title = data["title"]
    if name not in (title, without_disambiguation(title)):
        return Result(reason=f"the bold paragraph `{name}` differs from the title `{title}`")
    dropped = drop_blocks(text, (index,))
    if dropped is None:
        return Result(reason="nothing follows the bold paragraph")
    return Result(text=dropped)


def lettered(value: str) -> str:
    """Lowercase letters and digits only: what a bold name and a title share."""
    return re.sub(r"[^a-z0-9]", "", value.lower())


def bold_title_review(text: str, data: dict) -> Result | None:
    """misc-rule: queue a bold first paragraph that equals or resembles the title; change nothing.

    The row names the bold text and the start of the block after it, so a reviewer sees whether
    the paragraph repeats the title or labels what follows.
    """
    _head, _lead, rest = split_body(text)
    blocks = re.split(r"\n{2,}", rest.rstrip("\n"))
    index = None
    if BOLD_ONLY.fullmatch(blocks[0]):
        index = 0
    elif len(blocks) > 1 and unitalic(blocks[0]) is not None and BOLD_ONLY.fullmatch(blocks[1]):
        index = 1
    if index is None:
        return None
    name = BOLD_ONLY.fullmatch(blocks[index]).group(1).strip()
    title = data["title"]
    follow = " ".join(blocks[index + 1].split()) if index + 1 < len(blocks) else ""
    follow = follow.replace("`", "'").replace("\t", " ")
    follow = f"the next block starts `{follow[:60]}{'...' if len(follow) > 60 else ''}`"
    if name in (title, without_disambiguation(title)):
        return Result(
            reason=f"the bold paragraph `{name}` equals the title; echo, or label of the first "
            f"subsection? {follow if follow else 'nothing follows'}"
        )
    plain, other = lettered(name), lettered(title)
    if plain and other and (other.startswith(plain) or plain.startswith(other)):
        return Result(
            reason=f"the bold paragraph `{name}` resembles the title `{title}`; echo, or label "
            f"of the first subsection? {follow if follow else 'nothing follows'}"
        )
    return None


def feat_heading(text: str, data: dict) -> Result | None:
    if data.get("kind") != "feat":
        return None
    _head, _lead, rest = split_body(text)
    first = rest.split("\n", 1)[0]
    title = data["title"]
    if not (first.startswith(f"## {title} (") and first.endswith(")")):
        return None
    inner = first[len(f"## {title} (") : -1]
    types = data.get("fields", {}).get("feat_types", [])
    words = [word.strip() for word in inner.split(",")]
    if not types:
        return Result(reason=f"the heading names `{inner}`, and `feat_types` is empty")
    if sorted(words) != sorted(types):
        return Result(reason=f"the heading names `{inner}`, and `feat_types` is {types}")
    dropped = drop_first_line(text)
    if dropped is None:
        return Result(reason="nothing follows the heading")
    return Result(text=dropped)


def trait_type(text: str, data: dict) -> Result | None:
    if data.get("kind") != "trait":
        return None
    _head, _lead, rest = split_body(text)
    first = rest.split("\n", 1)[0]
    if not first.startswith("**Type:**"):
        return None
    fields = data.get("fields", {})
    printed = first[len("**Type:**") :].strip()
    category, detail = fields.get("category", ""), fields.get("detail")
    expected = [category] + ([f"{category} ({detail})"] if detail else [])
    if not category or printed not in expected:
        return Result(
            reason=f"the Type line `{printed}` differs from category `{category}`"
            + (f" and detail `{detail}`" if detail else "")
        )
    dropped = drop_first_line(text)
    if dropped is None:
        return Result(reason="nothing follows the Type line")
    return Result(text=dropped)


def compare_form(value: str) -> str:
    """Lowercase words without Markdown, link targets or end punctuation: what drift compares."""
    value = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", value)
    value = value.replace("*", "").replace("_", "")
    return " ".join(value.split()).lower().rstrip(".;")


def unitalic(block: str) -> str | None:
    """`_text_` without its markers; `None` unless the whole block is one italic span."""
    if block.startswith("_") and block.endswith("_") and block.count("_") == 2 and "*" not in block:
        return block[1:-1]
    return None


MYTHIC_STAT = re.compile(r"::: statblock\nType: ([^\n]*)\n:::\n\n")
MYTHIC_FLAVOUR = re.compile(r"(_[^\n]+(?:\n[^\n]+)*_)\n\n")
MYTHIC_PREREQ = re.compile(
    r"## Prerequisites \{#prerequisites\}\n\n(_[^\n]+(?:\n[^\n]+)*_)\n\n"
)
MYTHIC_LABELLED = {
    "Benefit": re.compile(
        r"## Benefits? \{#benefits?\}\n\n::: paragraph statline\n((?:[^\n]+\n)+):::\n\n?"
    ),
    "Special": re.compile(
        r"## Special \{#special\}\n\n::: paragraph statline\n((?:[^\n]+\n)+):::\n\n?"
    ),
}
MYTHIC_EXTRA = re.compile(r"::: paragraph statline\n((?:[^\n]+\n)+):::\n\n?")
FIELD_LINE = re.compile(r"^benefit = .*$", re.M)


def field_prefix(field: str, first: str) -> str | None:
    """The leading words of `field` that equal the paragraph `first`, as they stand in the field.

    `None` when no run of whole words does. The field keeps its own markup, so the cut is made on
    the field's words and tested with `compare_form`.
    """
    words = field.split()
    wanted = compare_form(first)
    for count in range(1, len(words) + 1):
        if compare_form(" ".join(words[:count])) == wanted:
            return " ".join(words[:count])
    return None


def toml_string(value: str) -> str:
    """`value` as a single-line TOML basic string."""
    out = value.replace("\\", "\\\\").replace('"', '\\"')
    return '"' + out + '"'


def printed_segments(text: str, labels: tuple[str, ...]) -> list[list[str]]:
    """The words of each line or paragraph of a body, markup and `labels` removed.

    A `\\` break and a blank line both end a segment, so a paragraph break that is lost or
    gained shows as a different list. Fences, heading markers and anchors are not printed.
    """
    out: list[list[str]] = []
    current: list[str] = []
    for line in text.split("\n"):
        if line.startswith(":::"):
            line = ""
        line = re.sub(r"\{#[^}]*\}", "", line)
        line = line.lstrip("#")
        broken = line.endswith("\\")
        line = line.rstrip("\\")
        line = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", line).replace("*", "").replace("_", "")
        words = [w for w in line.split() if w not in labels]
        current += words
        if broken or not line.strip():
            if current:
                out.append(current)
            current = []
    if current:
        out.append(current)
    return out


def same_print(before: str, after: str) -> bool:
    """Whether `after` prints the words and paragraph breaks of `before`.

    `before` loses its `Type:` stat block and the Prerequisites, Benefit(s) and Special headings;
    `after` loses the bold labels that replace them.
    """
    stat = re.sub(r"::: statblock\nType: [^\n]*\n:::\n", "", before, count=1)
    stat = re.sub(r"^## (Prerequisites|Benefits?|Special) \{#[a-z]+\}$", "", stat, flags=re.M)
    labels = ("Prerequisites:", "Benefit:", "Special:")
    return printed_segments(stat, ()) == printed_segments(after, labels)


def mythic(text: str, data: dict, path: str) -> Result | None:
    if data.get("kind") != "feat":
        return None
    _head, _lead, rest = split_body(text)
    if not rest.startswith("::: statblock\nType:"):
        return None
    if not MYTHIC_PATH.search(path):
        return Result(reason="a stat block opens the body of a feat that is not a mythic add-on")
    fields = data.get("fields", {})
    types = fields.get("feat_types", [])
    pos = 0
    stat = MYTHIC_STAT.match(rest, pos)
    if stat is None:
        return Result(reason="the Type stat block holds more than the Type row")
    printed_types = [word.strip() for word in stat.group(1).split(",")]
    if sorted(printed_types) != sorted(types):
        return Result(reason=f"the stat block says `{stat.group(1)}`, and `feat_types` is {types}")
    pos = stat.end()
    flavour = MYTHIC_FLAVOUR.match(rest, pos)
    if flavour is None or unitalic(flavour.group(1)) is None:
        return Result(reason="the flavour line is not one italic paragraph")
    pos = flavour.end()
    lines = [unitalic(flavour.group(1))]
    prereq = MYTHIC_PREREQ.match(rest, pos)
    if prereq is not None:
        value = unitalic(prereq.group(1))
        if value is None or compare_form(value) != compare_form(fields.get("prerequisites", "")):
            return Result(reason="the Prerequisites text differs from `[fields] prerequisites`")
        lines.append("**Prerequisites:** " + value)
        pos = prereq.end()
    extra: list[str] = []
    new_benefit: str | None = None
    for label, pattern in MYTHIC_LABELLED.items():
        part = pattern.match(rest, pos)
        if part is None:
            continue
        pos = part.end()
        value = part.group(1).rstrip("\n")
        field = fields.get(label.lower(), "")
        if label == "Benefit":
            while (more := MYTHIC_EXTRA.match(rest, pos)) is not None:
                extra.append(more.group(1).rstrip("\n"))
                pos = more.end()
            tail_text = [
                m.group(1).rstrip("\n")
                for m in re.finditer(
                    r"::: paragraph indented\n((?:[^\n]+\n)+):::", rest[pos:]
                )
            ]
            if extra or rest[pos:].lstrip("\n").startswith("###"):
                cut = field_prefix(field, value)
                joined = " ".join([value, *extra, *tail_text])
                if cut is None or compare_form(field) != compare_form(joined):
                    return Result(
                        reason="the Benefit paragraphs joined differ from `[fields] benefit`"
                    )
                if cut != field:
                    new_benefit = cut
                field = cut
        elif extra:
            return Result(reason="the Special follows several Benefit paragraphs")
        if compare_form(value) != compare_form(field):
            return Result(reason=f"the {label} text differs from `[fields] {label.lower()}`")
        lines.append(f"**{label}:** " + value)
    tail = rest[pos:].strip("\n")
    if (tail and not tail.startswith("###")) or "::: paragraph statline" in tail:
        return Result(reason="the body holds a block that the Pf Data form has no place for")
    if tail.startswith("###") and not any(
        line.startswith("**Benefit:**") for line in lines
    ):
        return Result(reason="subsections follow a body without a Benefit")
    head, lead, _ = split_body(text)
    body = "\\\n".join(lines) + "\n"
    for paragraph in extra:
        body += "\n" + paragraph + "\n"
    if tail:
        body += "\n" + tail + "\n"
    out = head + lead + body
    if new_benefit is not None:
        front, count = FIELD_LINE.subn(lambda _m: "benefit = " + toml_string(new_benefit), head)
        if count != 1:
            return Result(reason="the `benefit` field is not one line of the front matter")
        out = front + lead + body
    if not same_print(rest, body):
        return Result(reason="the converted body would not print the same words and paragraphs")
    return Result(text=out)


def run_pass(name: str, path: str, text: str, data: dict) -> Result | None:
    entry_id = data["id"]
    if name == "creature":
        if data.get("kind") == "creature" and entry_id.split("/")[1] in ("monster", "npc"):
            return bold_title(text, data)
    elif name == "trap-template":
        if entry_id.split("/")[1] in ("trap", "template"):
            return bold_title(text, data)
    elif name == "deity-haunt":
        if entry_id.split("/")[1] in ("faith", "haunt"):
            return bold_title(text, data)
    elif name == "misc-rule":
        if entry_id.split("/")[1] in ("misc", "rule"):
            return bold_title_review(text, data)
    elif name == "feat-heading":
        return feat_heading(text, data)
    elif name == "mythic":
        return mythic(text, data, path)
    elif name == "trait-type":
        return trait_type(text, data)
    return None


# ---------------------------------------------------------------------------------------------
# survey and write
# ---------------------------------------------------------------------------------------------


def entries(root: Path):
    for path in sorted((root / "entries").rglob("*.md")):
        text = path.read_text()
        front = FRONT.match(text)
        if front:
            yield path.relative_to(root).as_posix(), text, tomllib.loads(front.group(1))


def scan(root: Path):
    """Every decision of every pass: `(pass, path, id, text, result)`."""
    for path, text, data in entries(root):
        for name in PASSES:
            result = run_pass(name, path, text, data)
            if result is not None:
                yield name, path, data["id"], text, result


def review_text(rows: list[tuple[str, str, str, str]]) -> str:
    lines = ["pass\tentry_id\tfile\treason"]
    lines += ["\t".join(row) for row in sorted(rows)]
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--write", action="store_true", help="apply the passes")
    parser.add_argument("--check", action="store_true", help="exit 1 unless a rerun changes nothing")
    parser.add_argument("--pass", dest="passes", help="comma-separated passes to apply")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        return self_test()
    chosen = tuple(args.passes.split(",")) if args.passes else PASSES
    for name in chosen:
        if name not in PASSES:
            sys.exit(f"unknown pass {name!r}; passes: {', '.join(PASSES)}")
    root = Path(".")
    droppable = {name: 0 for name in PASSES}
    queued = {name: 0 for name in PASSES}
    rows: list[tuple[str, str, str, str]] = []
    changes: list[tuple[str, str]] = []
    for name, path, entry_id, text, result in scan(root):
        if result.text is not None:
            droppable[name] += 1
            if name in chosen:
                changes.append((path, result.text))
        else:
            queued[name] += 1
            rows.append((name, entry_id, path, result.reason or ""))
    print("pass            found  to change  queued")
    for name in PASSES:
        marker = "" if name in chosen else "  (not selected)"
        found = droppable[name] + queued[name]
        print(f"{name:14} {found:6} {droppable[name]:10} {queued[name]:7}{marker}")
    review = review_text(rows)
    review_path = root / REVIEW
    review_stale = not review_path.exists() or review_path.read_text() != review
    if args.check:
        pending = len(changes) + review_stale
        print(f"{len(changes)} entries would change; review file {'stale' if review_stale else 'current'}")
        return 1 if pending else 0
    if args.write:
        for path, text in changes:
            (root / path).write_text(text)
        review_path.write_text(review)
        print(f"{len(changes)} entries changed; {len(rows)} rows in {REVIEW}")
        return 0
    print(f"{len(changes)} entries would change; {len(rows)} entries are queued")
    return 0


# ---------------------------------------------------------------------------------------------
# self test
# ---------------------------------------------------------------------------------------------


def entry(front: str, body: str) -> tuple[str, dict]:
    text = f"+++\n{front}\n+++\n\n{body}"
    return text, tomllib.loads(FRONT.match(text).group(1))


def self_test() -> int:
    def decide(name: str, path: str, front: str, body: str) -> Result | None:
        text, data = entry(front, body)
        return run_pass(name, path, text, data)

    feat = 'id = "ref/feat/power-attack"\nkind = "feat"\ntitle = "Power Attack"\n[fields]\nfeat_types = ["Combat"]'
    out = decide("feat-heading", "x.md", feat, "## Power Attack (Combat)\n\nFlavour.\\\n**Benefit:** B.\n")
    assert out and out.text == f"+++\n{feat}\n+++\n\nFlavour.\\\n**Benefit:** B.\n", out
    two = feat.replace('["Combat"]', '["Teamwork", "Combat"]')
    assert decide("feat-heading", "x.md", two, "## Power Attack (Combat, Teamwork)\n\nA.\n").text
    assert decide("feat-heading", "x.md", feat, "## Power Attack (Teamwork)\n\nA.\n").reason
    assert decide("feat-heading", "x.md", feat, "## Power Attack\n\nA.\n") is None
    assert decide("feat-heading", "x.md", feat, "## Power Attack (Combat)\n").reason

    creature = 'id = "ref/monster/avoral"\nkind = "creature"\ntitle = "Avoral (Agathion)"'
    out = decide("creature", "x.md", creature, "_Flavour._\n\n**Avoral**\n\n**CR** 9\n")
    assert out and out.text.endswith("_Flavour._\n\n**CR** 9\n"), out
    out = decide("creature", "x.md", creature, "**Avoral**\n\n**CR** 9\n")
    assert out and out.text.endswith("+++\n\n**CR** 9\n"), out
    assert decide("creature", "x.md", creature, "_F._\n\n**Small Avoral**\n\nx\n").reason
    assert decide("creature", "x.md", creature, "_F._\n\nPlain.\n") is None
    trap = 'id = "ref/trap/bear-trap"\nkind = "rule"\ntitle = "Bear Trap"'
    assert decide("trap-template", "x.md", trap, "**Bear Trap**\n\n**Type:** Mechanical\n").text
    assert decide("creature", "x.md", trap, "**Bear Trap**\n\nx\n") is None

    trait = 'id = "ref/trait/a"\nkind = "trait"\ntitle = "A"\n[fields]\ncategory = "Regional"'
    out = decide("trait-type", "x.md", trait, "**Type:** Regional\n\n**Region:** R\n")
    assert out and out.text.endswith("+++\n\n**Region:** R\n"), out
    assert decide("trait-type", "x.md", trait, "**Type:** Combat\n\nx\n").reason
    assert decide("trait-type", "x.md", trait, "You grew up.\n") is None
    detail = trait + '\ndetail = "Half-Elf"'
    assert decide("trait-type", "x.md", detail, "**Type:** Regional (Half-Elf)\n\nx\n").text

    mythic_front = (
        'id = "ref/carried/mythic-adventures/feats/power-attack/mythic"\nkind = "feat"\n'
        'title = "Power Attack, Mythic"\n[fields]\nfeat_types = ["Mythic"]\n'
        'prerequisites = "Power Attack."\nbenefit = "You gain +3."'
    )
    path = "entries/carried/mythic-adventures/feats/power-attack/mythic.md"
    body = (
        "::: statblock\nType: Mythic\n:::\n\n_Devastating._\n\n"
        "## Prerequisites {#prerequisites}\n\n_Power Attack._\n\n"
        "## Benefits {#benefits}\n\n::: paragraph statline\nYou gain +3.\n:::\n"
    )
    out = decide("mythic", path, mythic_front, body)
    want = "Devastating.\\\n**Prerequisites:** Power Attack.\\\n**Benefit:** You gain +3.\n"
    assert out and out.text.endswith("+++\n\n" + want), out
    twice = body + "\n::: paragraph statline\nMore.\n:::\n"
    whole = mythic_front.replace('"You gain +3."', '"You gain +3. More."')
    out = decide("mythic", path, whole, twice)
    assert out and 'benefit = "You gain +3."\n' in out.text, out
    assert out.text.endswith("+++\n\n" + want + "\nMore.\n"), out
    assert "joined differ" in decide("mythic", path, mythic_front, twice).reason
    italic = mythic_front.replace('"You gain +3."', '"Cast slow, again."')
    mark = body.replace("You gain +3.", "Cast _slow_, again.")
    assert decide("mythic", path, italic, mark).text
    sub = body + "\n### Claws {#claws}\n\n::: paragraph indented\nSharp.\n:::\n"
    kept = mythic_front.replace('"You gain +3."', '"You gain +3. Sharp."')
    out = decide("mythic", path, kept, sub)
    assert out and 'benefit = "You gain +3."\n' in out.text and out.text.endswith("Sharp.\n:::\n"), out
    wrong = mythic_front.replace('["Mythic"]', '["General"]')
    assert "feat_types" in decide("mythic", path, wrong, body).reason
    assert "not a mythic" in decide("mythic", "entries/x.md", mythic_front, body).reason
    # a heading or Type line ends at its line break: text right behind it stays
    out = decide("feat-heading", "x.md", feat, "## Power Attack (Combat)\nKept.\n\nMore.\n")
    assert out and out.text.endswith("+++\n\nKept.\n\nMore.\n"), out
    out = decide("trait-type", "x.md", trait, "**Type:** Regional\nKept.\n")
    assert out and out.text.endswith("+++\n\nKept.\n"), out
    print("self-test ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
