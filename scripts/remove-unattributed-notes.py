#!/usr/bin/env python3
"""Remove notes that neither Archives of Nethys nor the Paizo PRD carries (phynics/cast-iron-data#114).

    python3 scripts/remove-unattributed-notes.py <corpus-dir>
        [--decisions scripts/unattributed-notes-114.tsv] [--report out.tsv] [--dry-run]
        [--tickets "phynics/cast-iron-data#109, #114"] [--basis "neither Archives of Nethys nor the PRD carries"]

The editorial footnotes audit (phynics/cast-iron docs/research/editorial-footnotes-audit.md,
cast-iron-data#109, follow-up tickets 1, 2 and 5) applies the owner's rule of 2026-11-19: a note
stays when its text is on AoN or in the PRD, and goes when it is on neither. The decision file has
one row per note, made from the audit's two TSV files (`editorial-footnotes.tsv` rows with
`action = remove` and `editorial-notes-outside-footnotes.tsv` rows with `action = remove`; the
`source-citation` rows are left out because #113 converted them). Each row names the entry and the
`text_sha` of the note (the first 16 hex digits of the SHA-256 of the note's text with Markdown
links reduced to their label and backslashes dropped), so only the reviewed text is removed: a row
whose text no longer matches is skipped and reported, never guessed.

Row actions:

  remove              kind `footnote`: delete the footnote heading and its note, and every body
                      marker that points to it: the linked form `^[L](entry#footnote-l)^` and the
                      plain form `word\\#L` (with or without the backslash, in the body and in
                      front matter fields such as `special_qualities`). A plain marker goes only
                      when the entry has no footnote block with that label any more, so the marker
                      of a kept note stays. The pass runs on every run, also for a note that an
                      earlier run removed. kind `paragraph`: delete the
                      paragraph outside a footnote block, and its marker (`body_marker`: the
                      superscript or dagger in the text that pointed to it).
  split               kind `footnote`: the block holds several notes joined by `\\|X~` (an unsplit
                      multi-note `::mfn`). Each note becomes its own footnote block, labelled X, with
                      anchor `footnote-x`. The labels in `drop_labels` are removed, with a record in
                      `exclusions.toml`; the others stay.
  rename-duplicates   kind `anchor`: an entry that repeats a footnote anchor keeps the first and
                      suffixes the rest (`footnote-b-2`, the way repeated headings are suffixed).
                      A linked marker follows the heading that has its label.
  skip                Not applied; listed in the report.

`--tickets` and `--basis` fill the reason of each `exclusions.toml` row. The defaults are the
words of #114. Phynics/cast-iron-data#117 (owner decision of 2026-11-20: a note also stays when the
printed book carries it) runs it with `--decisions scripts/editorial-footnotes-117.tsv --tickets
"phynics/cast-iron-data#109, #117" --basis "neither Archives of Nethys, the PRD nor the printed book carries"`.

For each removed or dropped note the script appends one `[[excluded]]` row to `exclusions.toml` with
`records = 0` (the record ships, only a note on it does not), the record the entry came from,
cast-iron-data#109 and the reason. A row that is already there is not written twice, so a second run
finds nothing to do. It never edits an `id`, never moves a file, and changes no text other than the
removed notes and their markers. Run `cargo xtask corpus-fmt <corpus-dir>` afterwards: a line that lost
a marker is rewrapped to the canonical width.
"""
import argparse
import csv
import hashlib
import re
import sys
import tomllib
from collections import defaultdict
from pathlib import Path

HEADING = re.compile(r"^#{1,6}\s")
FOOTNOTE_HEADING = re.compile(r"^######\s+(.*?)\s*\{#(footnote-[^}]+)\}\s*$")
ANY_ANCHOR = re.compile(r"\{#([^}\s]+)\}")
RESIDUE = re.compile(r"\\?\|([A-Za-z0-9])\\?~")
EXCERPT = 100


def strip_md(text):
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)
    return text.replace("\\", "")


def text_sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def toml_str(s):
    """The canonical form that `cargo xtask corpus-fmt` writes: a basic string; a literal string
    when the text has a double quote and no single quote; a multi-line basic string (`\"\"\"`) when it
    has both and no backslash."""
    if "\n" not in s and '"' in s:
        if "'" not in s:
            return "'" + s + "'"
        if "\\" not in s and '"""' not in s and not s.endswith('"'):
            return '"""' + s + '"""'
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def split_entry(text):
    if not text.startswith("+++\n"):
        raise ValueError("no front matter")
    end = text.index("\n+++\n", 4)
    return text[4:end], text[end + 5 :]


def plain_label(label):
    label = label.strip()
    if label.startswith("^") and label.endswith("^"):
        label = label[1:-1]
    return label


def footnote_blocks(lines):
    """[dict(start, end, label, anchor, paragraph)] for each footnote heading. A block is the
    heading and the one paragraph after it (docs/corpus-format.md, Footnotes), as the audit reads
    it; `end` is the index after the paragraph. `paragraph` is the list of its raw lines."""
    blocks = []
    for i, line in enumerate(lines):
        m = FOOTNOTE_HEADING.match(line)
        if not m:
            continue
        j = i + 1
        para = []
        while j < len(lines):
            l = lines[j]
            if HEADING.match(l) or l.startswith(":::"):
                break
            if not l.strip():
                if para:
                    break
                j += 1
                continue
            para.append(l)
            j += 1
        blocks.append(
            {"start": i, "end": j, "label": plain_label(m.group(1)), "anchor": m.group(2), "paragraph": para}
        )
    return blocks


def paragraphs(lines, mask):
    """[(start, end, raw_text)] for each paragraph outside the footnote blocks (the audit's
    `outside_notes` scan): a run of non-blank lines, ended by a blank line or a heading."""
    out = []
    para, start = [], 0
    for i, line in enumerate(lines + [""]):
        if i in mask or not line.strip() or HEADING.match(line):
            if para:
                out.append((start, i, " ".join(para)))
            para = []
            continue
        if not para:
            start = i
        para.append(line.strip())
    return out


def remove_linked_markers(body, entry_id, anchor):
    """Drop every `^[label](entry#anchor)^` marker; return (body, count)."""
    marker = r"\^\[[^\]]*\]\(" + re.escape(f"{entry_id}#{anchor}") + r"\)\^"
    n = 0
    body, k = re.subn(r"(?m)^[ \t]*" + marker + r"[ \t]*\n", "", body)
    n += k
    body, k = re.subn(r"[ \t]?" + marker, "", body)
    n += k
    return body, n


def plain_marker_re(label):
    """A plain letter marker after a word: `enlarge\\#X` in the body, `(owl or mouse)#C` in a front
    matter string. Not a heading anchor (`{#footnote-x}`), a link target (`(#x)`), or a `#` that
    starts a word of its own (`Pathfinder \\#44`): the marker follows a non-space character."""
    return re.compile(r"(?<=[^\s{(\[\\])\\?#" + re.escape(label) + r"(?![\w-])")


FRONT_KEEP = re.compile(r"^(id|path|record|url|href|source|link)\b")


def remove_plain_markers(front, body, labels):
    """Drop the plain markers of the labels in `labels` (their notes are gone). Return
    (front, body, count)."""
    n = 0
    for label in sorted(labels):
        rx = plain_marker_re(label)
        body, k = rx.subn("", body)
        n += k
        out = []
        for line in front.split("\n"):
            if not FRONT_KEEP.match(line):
                line, k = rx.subn("", line)
                n += k
            out.append(line)
        front = "\n".join(out)
    return front, body, n


def drop_ranges(lines, ranges):
    """Delete [start, end) ranges (and the blank lines after each) from the lines."""
    for start, end in sorted(ranges, reverse=True):
        while end < len(lines) and not lines[end].strip():
            end += 1
        if end >= len(lines):  # at the end of the body: drop the blank lines before it too
            while start > 0 and not lines[start - 1].strip():
                start -= 1
        del lines[start:end]
    return lines


def tidy(body):
    return body.rstrip("\n") + "\n"


def entry_path(corpus, entry_id):
    return corpus / "entries" / (entry_id.removeprefix("ref/") + ".md")


def record_path(fm):
    prov = fm["provenance"][0]
    return f"{prov['path']}#{prov['record']}"


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("corpus")
    ap.add_argument("--decisions", default=str(Path(__file__).with_name("unattributed-notes-114.tsv")))
    ap.add_argument("--tickets", default="phynics/cast-iron-data#109, #114", help="issues named in each exclusions.toml reason")
    ap.add_argument("--basis", default="neither Archives of Nethys nor the PRD carries", help="why the note goes")
    ap.add_argument("--report")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    corpus = Path(args.corpus)
    tickets = args.tickets

    rows = defaultdict(list)  # entry id -> rows
    with open(args.decisions, newline="") as f:
        for row in csv.DictReader(f, delimiter="\t"):
            if row["action"] not in ("remove", "split", "rename-duplicates", "skip"):
                sys.exit(f"bad action {row['action']!r} for {row['entry_id']}")
            rows[row["entry_id"]].append(row)

    exclusions_path = corpus / "exclusions.toml"
    exclusions_text = exclusions_path.read_text()
    with open(exclusions_path, "rb") as f:
        known = {(r.get("path"), r.get("reason")) for r in tomllib.load(f).get("excluded", [])}
    new_exclusions = []
    report = []
    stats = defaultdict(int)
    errors = []

    def done_before(entry_id, r):
        """True when exclusions.toml already has the row that a removal of this note wrote."""
        probe = f"Entry {entry_id}"
        excerpt = strip_md(r["text"])[:40]
        return any(probe in reason and excerpt in reason for _, reason in known)

    def add_exclusion(entry_id, fm, what, cls, label_text, why):
        path = record_path(fm)
        reason = (
            f"{what} that {args.basis}, removed "
            f"({tickets}). Kind: {cls}. Entry {entry_id}{why}. "
            f"Text: \"{label_text}\". No record is left out."
        )
        return (path, reason)

    # Links into an anchor that the script renames, from other entries.
    link_re = re.compile(r"\]\((ref/[^)#\s]+)#(footnote-[^)\s]+)\)")

    for entry_id in sorted(rows):
        path = entry_path(corpus, entry_id)
        text = path.read_text()
        front, body = split_entry(text)
        fm = tomllib.loads(front)
        if fm["id"] != entry_id:
            errors.append(f"{path}: id is {fm['id']!r}, not {entry_id!r}")
            continue
        lines = body.split("\n")
        blocks = footnote_blocks(lines)
        mask = set()
        for b in blocks:
            mask.update(range(b["start"], b["end"]))
        paras = paragraphs(lines, mask)
        todo = [r for r in rows[entry_id] if r["action"] != "skip"]
        for r in rows[entry_id]:
            if r["action"] == "skip":
                report.append((entry_id, r["kind"], "skip", r["text"], r["note"]))
                stats["skipped (left for review)"] += 1

        gone_labels = set()  # labels of the notes of this entry that the decision file removes
        for r in todo:
            if r["kind"] == "footnote" and r["action"] == "remove" and re.fullmatch(r"[A-Za-z]", r["marker"]):
                gone_labels.add(r["marker"])
            elif r["kind"] == "footnote" and r["action"] == "split":
                gone_labels.update(d for d in r["drop_labels"].split(",") if re.fullmatch(r"[A-Za-z]", d))

        delete = []  # (start, end) line ranges
        replaced = {}  # block start -> new heading + paragraph lines (split)
        removed_anchors = []
        body_markers = []
        new_rows = []
        used = set()

        for r in todo:
            if r["kind"] == "footnote" and r["action"] in ("remove", "split"):
                hit = [
                    b
                    for b in blocks
                    if b["anchor"] == r["anchor"]
                    and b["label"] == r["marker"]
                    and id(b) not in used
                    and text_sha(strip_md(" ".join(l.strip() for l in b["paragraph"]))) == r["text_sha"]
                ]
                if not hit:
                    done = (not RESIDUE.search(body)) if r["action"] == "split" else done_before(entry_id, r)
                    stats[f"{r['kind']} rows {'already done' if done else 'with no match (text changed)'}"] += 1
                    report.append((entry_id, r["kind"], "already-done" if done else "no-match", r["text"], r["anchor"]))
                    continue
                b = hit[0]
                used.add(id(b))
                flat = strip_md(" ".join(l.strip() for l in b["paragraph"]))
                if r["action"] == "remove":
                    delete.append((b["start"], b["end"]))
                    removed_anchors.append((r["anchor"], b["label"]))
                    new_rows.append(
                        add_exclusion(
                            entry_id, fm, "1 footnote", r["class"], flat[:EXCERPT].replace("\n", " "),
                            f", marker {b['label']}, anchor {r['anchor']}",
                        )
                    )
                    stats["footnote blocks removed"] += 1
                    report.append((entry_id, "footnote", "removed", r["text"], r["anchor"]))
                else:
                    raw = " ".join(l.strip() for l in b["paragraph"])
                    pieces = RESIDUE.split(raw)  # [text0, X1, text1, X2, text2, ...]
                    notes = [(b["label"], pieces[0].strip())]
                    for k in range(1, len(pieces), 2):
                        notes.append((pieces[k], pieces[k + 1].strip()))
                    drop = [d for d in r["drop_labels"].split(",") if d]
                    out = []
                    taken = {a for a in ANY_ANCHOR.findall(body)}
                    taken.discard(r["anchor"])
                    for n, (label, ntext) in enumerate(notes):
                        if label in drop:
                            new_rows.append(
                                add_exclusion(
                                    entry_id, fm, "1 footnote", "commentary",
                                    strip_md(ntext)[:EXCERPT],
                                    f", marker {label}, joined to the {b['label']} note by \\|{label}~ residue",
                                )
                            )
                            stats["residue notes dropped"] += 1
                            continue
                        anchor = r["anchor"] if n == 0 else f"footnote-{label.lower()}"
                        while n and anchor in taken:
                            anchor += "-2"
                        taken.add(anchor)
                        heading = lines[b["start"]] if n == 0 else f"###### {label} {{#{anchor}}}"
                        out += [heading, "", ntext, ""]
                    stats["residue blocks split"] += 1
                    replaced[b["start"]] = (b["end"], out[:-1])
                    report.append((entry_id, "footnote", "split", r["text"], r["anchor"]))
            elif r["kind"] == "paragraph" and r["action"] == "remove":
                hit = [p for p in paras if text_sha(strip_md(p[2])) == r["text_sha"] and p[0] not in used]
                if not hit:
                    done = done_before(entry_id, r)
                    stats[f"paragraph rows {'already done' if done else 'with no match (text changed)'}"] += 1
                    report.append((entry_id, "paragraph", "already-done" if done else "no-match", r["text"], ""))
                    continue
                s, e, raw = hit[0]
                used.add(s)
                delete.append((s, e))
                if r["body_marker"]:
                    body_markers.append(r["body_marker"])
                what = "1 inline note" if r["body_marker"] else "1 paragraph"
                new_rows.append(
                    add_exclusion(
                        entry_id, fm, what, r["class"],
                        strip_md(raw)[:EXCERPT], f", line {s + 1}",
                    )
                )
                stats["paragraphs removed"] += 1
                report.append((entry_id, "paragraph", "removed", r["text"], r["body_marker"]))

        # apply the edits to the body
        for start, (end, new) in sorted(replaced.items(), reverse=True):
            lines[start:end] = new
            # block lines inside `delete` must not overlap replaced ones; shift later ranges
        if replaced:
            # the replaced blocks changed line numbers; recompute delete ranges by re-finding is
            # unsafe, so require that an entry mixes `split` with other edits only after them.
            if delete:
                errors.append(f"{entry_id}: a split row and a removal in one entry; apply them in two runs")
                continue
        if delete:
            drop_ranges(lines, delete)
        new_body = "\n".join(lines)
        for anchor, label in removed_anchors:
            still = [b for b in footnote_blocks(new_body.split("\n")) if b["anchor"] == anchor]
            if still:
                continue  # another block still has the anchor: its links stay
            new_body, n = remove_linked_markers(new_body, entry_id, anchor)
            stats["linked markers removed"] += n
            # a `[^K]` reference that the import left in a front matter field (`prerequisites`,
            # `aura`) names the removed note by its anchor letter
            key = re.escape(anchor.removeprefix("footnote-"))
            front, n = re.subn(r"(?im)^(\w+ = .*?) ?\[\^" + key + r"\]", r"\1", front)
            stats["front matter references removed"] += n
        for marker in dict.fromkeys(body_markers):
            n = new_body.count(marker)
            if n == 0:  # the note had no marker in the text (an orphan note)
                stats["notes without a body marker"] += 1
                report.append((entry_id, "paragraph", "no-body-marker", marker, ""))
            new_body = new_body.replace(marker, "")
            stats["body markers removed"] += n

        # duplicate anchors
        for r in [r for r in todo if r["action"] == "rename-duplicates"]:
            bl = footnote_blocks(new_body.split("\n"))
            same = [b for b in bl if b["anchor"] == r["anchor"]]
            if len(same) <= 1:
                stats["duplicate-anchor rows with nothing to rename"] += 1
                continue
            lns = new_body.split("\n")
            taken = set(ANY_ANCHOR.findall(new_body))
            renames = {}  # label -> new anchor (for linked markers)
            for b in same[1:]:
                n = 2
                while f"{r['anchor']}-{n}" in taken:
                    n += 1
                new = f"{r['anchor']}-{n}"
                taken.add(new)
                lns[b["start"]] = lns[b["start"]].replace("{#" + r["anchor"] + "}", "{#" + new + "}")
                renames[b["label"]] = new
                stats["duplicate anchors renamed"] += 1
                report.append((entry_id, "anchor", "renamed", b["label"], f"{r['anchor']} -> {new}"))
            new_body = "\n".join(lns)
            first = same[0]["label"]
            for m in re.finditer(r"\^\[([^\]]*)\]\(" + re.escape(f"{entry_id}#{r['anchor']}") + r"\)\^", new_body):
                if m.group(1) != first:
                    label = m.group(1)
                    if label in renames:
                        new_body = new_body.replace(m.group(0), m.group(0).replace(r["anchor"], renames[label]))
                        stats["linked markers updated"] += 1
                    else:
                        errors.append(f"{entry_id}: marker {m.group(0)} cannot be matched to a heading")

        # plain markers (`word\\#X`) of the removed notes, once no block with that label is left
        kept = {b["label"] for b in footnote_blocks(new_body.split("\n"))}
        front, new_body, n = remove_plain_markers(front, new_body, gone_labels - kept)
        stats["plain markers removed"] += n

        new_body = tidy(new_body)
        for row in new_rows:
            if row not in known:
                known.add(row)
                new_exclusions.append(row)
        new_text = "+++\n" + front + "\n+++\n" + new_body
        if new_text != text:
            stats["entries changed"] += 1
            if not args.dry_run:
                path.write_text(new_text)

    # links from other entries to a renamed or removed anchor
    removed_targets = set()
    for p in sorted((corpus / "entries").rglob("*.md")):
        fm_text, b = split_entry(p.read_text())
        eid = tomllib.loads(fm_text)["id"]
        seen = defaultdict(int)
        for a in re.findall(r"\{#(footnote-[^}]+)\}", b):
            seen[a] += 1
            if seen[a] == 2:
                errors.append(f"{eid}: footnote anchor {a} still occurs twice")
        for t_id, anchor in link_re.findall(b):
            tp = entry_path(corpus, t_id)
            if tp.exists() and f"{{#{anchor}}}" not in tp.read_text():
                errors.append(f"{eid}: link to {t_id}#{anchor}, which no heading has")

    if errors:
        for e in errors:
            print("error:", e, file=sys.stderr)
        sys.exit(1)

    if new_exclusions and not args.dry_run:
        # one row per removal; a row's path and reason must be unique
        out = [
            f"[[excluded]]\npath = {toml_str(path)}\nrecords = 0\nreason = {toml_str(reason)}\n"
            for path, reason in new_exclusions
        ]
        with open(exclusions_path, "a") as f:
            f.write("\n" + "\n".join(out))
    stats["exclusion rows appended"] = len(new_exclusions)
    if args.report:
        with open(args.report, "w", newline="") as f:
            w = csv.writer(f, delimiter="\t", lineterminator="\n")
            w.writerow(["entry_id", "kind", "result", "text", "detail"])
            w.writerows(report)
    for k in sorted(stats):
        print(f"{k}: {stats[k]}")


if __name__ == "__main__":
    main()
