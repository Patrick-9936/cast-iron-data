#!/usr/bin/env python3
"""Restore the markers of kept footnotes (phynics/cast-iron-data#116).

    python3 scripts/restore-kept-footnote-markers.py <corpus-dir>
        [--decisions scripts/kept-footnote-markers-116.tsv] [--report out.tsv] [--dry-run]

The editorial footnotes audit (phynics/cast-iron docs/research/editorial-footnotes-audit.md,
cast-iron-data#109, follow-up ticket 4) found footnote blocks that no marker in the entry body
points to (the orphans that `cargo xtask corpus-check` warns about). The decision file has one row
per orphan block of the corpus at v0.1.30 (after #113 and #115), made from the audit script's
output. Each row names the entry, the anchor and the `text_sha` of the note (the first 16 hex digits
of the SHA-256 of the note's text with Markdown links reduced to their label and backslashes
dropped), so only the reviewed note is touched: a row whose text no longer matches is reported,
never guessed.

Row actions:

  restore-inline   The importer rewrote the printed superscript `^D^` or `^M^` of a spell list as
                   the text "(domain spell)" or "(mythic spell)" (`inline`) and still emitted the
                   note. Every such text in the entry body becomes the superscript of the row's
                   label, attached to the spell name as the printed page and Archives of Nethys
                   show it: `dictum (mythic spell) (DC 30)` becomes `dictum^M^ (DC 30)`. A text
                   that the line wrap split across two lines is joined. The note stays.
  restore-plain    The importer left the printed marker as the escaped text `\\#S` (`inline`).
                   Every such text in the entry body becomes `^S^`. The note stays.
  drop-copy        The note was copied from a shared record whose marker sits in another entry
                   (the table of detect evil, major creation), or repeats another note of the
                   entry. The heading and its paragraph are deleted, with one `[[excluded]]` row
                   in `exclusions.toml` (`records = 0`: the record ships, only a note on it does
                   not) that names the record, cast-iron-data#109 and #116.
  drop-duplicate   The note repeats another note of the same entry. Handled like drop-copy; the
                   exclusion row says so.
  skip             Not applied; listed in the report.

Safe to interrupt and rerun. Every file is written to a temp file in its directory, fsynced and
replaced over the original, so none is ever truncated. The `[[excluded]]` rows are written first,
then the entry files. A run that stops between the two leaves rows whose notes are still
there; the rerun finds the notes, skips the rows it already has, and deletes the notes. A note that
is gone with no exclusion row, a drop row whose note text changed, and an anchor that occurs twice
in the entry are errors: the script changes nothing and exits 1.

A second run changes nothing: the restored text is gone, a dropped note has its exclusion row. The
script never edits an `id` and never moves a file. Run `cargo xtask corpus-fmt <corpus-dir>`
afterwards: a line that gained or lost text is rewrapped to the canonical width.
"""
import argparse
import csv
import importlib.util
import os
import re
import sys
import tomllib
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("remove_unattributed_notes", HERE / "remove-unattributed-notes.py")
base = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(base)

ACTIONS = ("restore-inline", "restore-plain", "drop-copy", "drop-duplicate", "skip")
EXCERPT = 100


def write_atomic(path, text):
    """Write `text` to a temp file in the same directory, flush and fsync it, then replace `path`
    with it, so an interruption leaves the old file or the new one, never a truncated one."""
    tmp = path.with_name(path.name + ".tmp")
    with open(tmp, "w", encoding="utf-8", newline="") as f:
        f.write(text)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def inline_regex(inline):
    """The text `(domain spell)` as a regex: the words may be split by a line wrap, and the text
    takes the space or line break before it. It must follow a non-space character (the spell
    name); a text at the start of a line of its own is an error to look at."""
    words = re.escape(inline).replace(r"\ ", r"\s+")
    return re.compile(r"(?<=\S)[ \t]*(?:\n[ \t]*)?" + words)


def plain_regex(inline):
    """The escaped marker `\\#S` after a word, as `base.plain_marker_re` reads it."""
    label = inline.lstrip("\\#")
    return base.plain_marker_re(label)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("corpus")
    ap.add_argument("--decisions", default=str(HERE / "kept-footnote-markers-116.tsv"))
    ap.add_argument("--report")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    corpus = Path(args.corpus)

    rows = defaultdict(list)
    seen = set()
    with open(args.decisions, newline="") as f:
        for row in csv.DictReader(f, delimiter="\t"):
            if row["action"] not in ACTIONS:
                sys.exit(f"bad action {row['action']!r} for {row['entry_id']}")
            key = (row["entry_id"], row["anchor"])
            if key in seen:
                sys.exit(f"error: the decision file has two rows for {row['entry_id']} {row['anchor']}")
            seen.add(key)
            rows[row["entry_id"]].append(row)

    exclusions_path = corpus / "exclusions.toml"
    with open(exclusions_path, "rb") as f:
        known = {(r.get("path"), r.get("reason")) for r in tomllib.load(f).get("excluded", [])}
    new_exclusions = []
    report = []
    stats = defaultdict(int)
    errors = []
    writes = []  # nothing is written until every entry has passed

    for entry_id in sorted(rows):
        path = base.entry_path(corpus, entry_id)
        text = path.read_text()
        front, body = base.split_entry(text)
        fm = tomllib.loads(front)
        if fm["id"] != entry_id:
            errors.append(f"{path}: id is {fm['id']!r}, not {entry_id!r}")
            continue
        lines = body.split("\n")
        blocks = base.footnote_blocks(lines)
        delete = []  # anchors of the dropped notes
        edits = []  # (row, regex, replacement) over the body text outside the notes
        new_rows = []

        for r in rows[entry_id]:
            act = r["action"]
            if act == "skip":
                report.append((entry_id, r["anchor"], "skip", r["text"], r["note"]))
                stats["skipped (left for review)"] += 1
                continue
            hit = [
                b
                for b in blocks
                if b["anchor"] == r["anchor"]
                and b["label"] == r["marker"]
                and base.text_sha(base.strip_md(" ".join(l.strip() for l in b["paragraph"]))) == r["text_sha"]
            ]
            if act in ("drop-copy", "drop-duplicate"):
                probe = f"Entry {entry_id}, marker {r['marker']}, anchor {r['anchor']}:"
                recorded = any(probe in reason for _, reason in known)
                same_anchor = [b for b in blocks if b["anchor"] == r["anchor"]]
                if not hit:
                    if same_anchor:
                        errors.append(f"{entry_id}: the note under {r['anchor']} is not the reviewed text; row not applied")
                    elif not recorded:
                        errors.append(
                            f"{entry_id}: the note under {r['anchor']} is gone and exclusions.toml has no row for it; "
                            "restore the entry file from git and run again"
                        )
                    else:
                        stats["drop rows already done"] += 1
                        report.append((entry_id, r["anchor"], "already-done", r["text"], ""))
                    continue
                if len(same_anchor) != 1:
                    errors.append(f"{entry_id}: anchor {r['anchor']} occurs {len(same_anchor)} times; row not applied")
                    continue
                b = hit[0]
                delete.append((b["anchor"], b["label"], r["text_sha"]))
                flat = base.strip_md(" ".join(l.strip() for l in b["paragraph"]))
                prov = fm["provenance"][0]
                what = (
                    "1 footnote that repeats another note of the same entry"
                    if act == "drop-duplicate"
                    else "1 footnote that is a copy of a note that belongs to another record"
                )
                reason = (
                    f"{what}, removed "
                    f"(phynics/cast-iron-data#109, #116). Entry {entry_id}, marker {b['label']}, "
                    f"anchor {r['anchor']}: {r['note']}. Text: \"{flat[:EXCERPT]}\". No record is left out."
                )
                if not recorded:
                    new_rows.append((f"{prov['path']}#{prov['record']}", reason))
                stats["notes dropped"] += 1
                report.append((entry_id, r["anchor"], "dropped", r["text"], r["note"]))
            else:
                if not hit:
                    stats["restore rows with no match (text changed)"] += 1
                    report.append((entry_id, r["anchor"], "no-match", r["text"], ""))
                    continue
                if act == "restore-inline":
                    rx = inline_regex(r["inline"])
                else:
                    rx = plain_regex(r["inline"])
                edits.append((r, rx, f"^{r['marker']}^"))

        # edit the body outside the notes: take the lines of every block out, edit, put them back
        if edits:
            mask = set()
            for b in blocks:
                mask.update(range(b["start"], b["end"]))
            for r, rx, _ in edits:
                if rx.search(front):
                    errors.append(f"{entry_id}: {r['inline']!r} also occurs in the front matter; fix it by hand")
                # the heading and paragraph of a note must not hold the text
                if any(rx.search(lines[i]) for i in mask):
                    errors.append(f"{entry_id}: {r['inline']!r} occurs inside a footnote block")
            # the text between the notes, joined with a placeholder line per note
            chunks, cur = [], []
            for i, line in enumerate(lines):
                if i in mask:
                    if cur:
                        chunks.append(("text", cur))
                        cur = []
                    if not chunks or chunks[-1][0] != "note":
                        chunks.append(("note", []))
                    chunks[-1][1].append(line)
                else:
                    cur.append(line)
            if cur:
                chunks.append(("text", cur))
            out = []
            for kind, ls in chunks:
                if kind == "note":
                    out.extend(ls)
                    continue
                seg = "\n".join(ls)
                for r, rx, rep in edits:
                    seg, n = rx.subn(rep, seg)
                    if n:
                        stats[f"markers restored ({r['action']})"] += n
                        report.append((entry_id, r["anchor"], "restored", r["inline"], f"{n} x {rep}"))
                out.extend(seg.split("\n"))
            lines = out
            done = all(
                f"^{r['marker']}^" in "\n".join(lines) or r["action"] == "skip" for r, _, _ in edits
            )
            if not done:
                for r, _, _ in edits:
                    if f"^{r['marker']}^" not in "\n".join(lines):
                        stats["restore rows with nothing to restore"] += 1
                        report.append((entry_id, r["anchor"], "nothing-to-restore", r["inline"], ""))
        if delete:
            # the edits above can change the line numbers, so find the notes again; each one must
            # still match its anchor, label and text hash, and be the only block with its anchor
            now = base.footnote_blocks(lines)
            ranges = []
            for anchor, label, sha in delete:
                same = [b for b in now if b["anchor"] == anchor]
                ok = [
                    b
                    for b in same
                    if b["label"] == label
                    and base.text_sha(base.strip_md(" ".join(l.strip() for l in b["paragraph"]))) == sha
                ]
                if len(same) != 1 or len(ok) != 1:
                    errors.append(f"{entry_id}: cannot find exactly one reviewed note under {anchor}; row not applied")
                    continue
                ranges.append((ok[0]["start"], ok[0]["end"]))
            ranges.sort()
            for (s1, e1), (s2, e2) in zip(ranges, ranges[1:]):
                if s2 < e1:
                    errors.append(f"{entry_id}: two rows delete overlapping lines; row not applied")
                    ranges = []
                    break
            lines = base.drop_ranges(lines, ranges)

        new_body = base.tidy("\n".join(lines))
        for row in new_rows:
            if row not in known:
                known.add(row)
                new_exclusions.append(row)
        new_text = "+++\n" + front + "\n+++\n" + new_body
        if new_text != text:
            stats["entries changed"] += 1
            writes.append((path, new_text))

    if errors:
        for e in errors:
            print("error:", e, file=sys.stderr)
        sys.exit(1)

    if not args.dry_run:
        # the exclusion rows first, in one replace of the file, so that no note is deleted
        # without its row; then the entry files
        if new_exclusions:
            out = [
                f"[[excluded]]\npath = {base.toml_str(path)}\nrecords = 0\nreason = {base.toml_str(reason)}\n"
                for path, reason in new_exclusions
            ]
            write_atomic(exclusions_path, exclusions_path.read_text() + "\n" + "\n".join(out))
        for path, new_text in writes:
            write_atomic(path, new_text)
    stats["exclusion rows appended"] = len(new_exclusions)
    if args.report:
        with open(args.report, "w", newline="") as f:
            w = csv.writer(f, delimiter="\t", lineterminator="\n")
            w.writerow(["entry_id", "anchor", "result", "text", "detail"])
            w.writerows(report)
    for k in sorted(stats):
        print(f"{k}: {stats[k]}")


if __name__ == "__main__":
    main()
