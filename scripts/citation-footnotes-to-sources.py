#!/usr/bin/env python3
"""Convert page-citation footnotes to structured sources (phynics/cast-iron-data#112).

    python3 scripts/citation-footnotes-to-sources.py <corpus-dir>
        [--decisions scripts/citation-footnotes-112.tsv] [--report out.tsv] [--dry-run]

The editorial footnotes audit (phynics/cast-iron docs/research/editorial-footnotes-audit.md,
ticket 7, owner decision (b) of 2026-11-19) found footnote blocks that only cite a printed page,
such as "Aquatic Adventures pg. 62". The app already shows `[[sources]]` as "Sources: Book p. N"
and `[[expanded_in]]` as "Expanded in". This script moves each such citation there and removes the
footnote block.

The decision file has one row per (entry, footnote anchor, cited book, cited page):

  verdict   holds       the book prints the entry (or a section of its body) on that page
            fails       the page was read and the book does not print the entry there
            unchecked   the page could not be read
  basis     aon-prd     the #109 audit found the citation on the item's Archives of Nethys page
                        or in the PRD
            print       the cited page was read in the printed book (`evidence` says what it holds)
  evidence  a short reason that goes into `exclusions.toml` for `fails` and `unchecked` rows

For each entry named in the decision file the script

  1. parses every footnote block whose whole text is a list of `Title pg. N` citations, maps the
     titles to publication ids through `publications.toml`, and refuses a citation that has no
     decision row, a decision row that disagrees with the corpus, and a title that does not map;
  2. turns each `holds` citation into a `[[sources]]` row when the book is in the entry's
     `source_ids`, else into an `[[expanded_in]]` row (a book that is not a member only expands the
     entry; `corpus-check` requires that split). The row merges with an existing row for the
     publication: the existing page stays and a cited page it does not cover is added (adjacent
     pages join into a range). It never writes a second row for a publication. New `[[sources]]`
     rows follow the order of `source_ids`;
  3. appends one `[[excluded]]` row per entry to `exclusions.toml` for its `fails` and `unchecked`
     citations (`records = 0`: the record ships, only a note on it does not). A row that is already
     there is not written twice;
  4. removes every citation block of the entry, with its marker references in the body (a marker
     whose block is gone would link to nothing).

It never edits an `id`, never moves a file, and leaves the footnotes that are not citations alone.
It is idempotent: once a block is gone, a second run finds nothing to do for it. Run
`cargo xtask corpus-fmt <corpus-dir>` afterwards to put the files in canonical form.
"""
import argparse
import csv
import re
import sys
import tomllib
from collections import defaultdict
from pathlib import Path

HEADING = re.compile(r"^(#{1,6}) ")
FOOTNOTE_HEADING = re.compile(r"^###### \^(.*)\^ \{#(footnote-[^}]+)\}$")
CITATION = re.compile(r"\s*(.+?) pg\. (\d+(?:-\d+)?)(?:,\s+|$)")
PAGE = re.compile(r"^(\d+)(?:-(\d+))?$")
TITLE_PREFIX = re.compile(r"^(pathfinder rpg|pathfinder roleplaying game|prpg) ")


def norm_title(title):
    t = title.replace("\\#", "#").replace("’", "'").lower().strip()
    t = TITLE_PREFIX.sub("", t)
    return re.sub(r"[^a-z0-9#]+", " ", t).strip()


def load_publications(corpus):
    by_title = {}
    titles = {}
    with open(corpus / "publications.toml", "rb") as f:
        for row in tomllib.load(f)["publication"]:
            by_title[norm_title(row["title"])] = row["id"]
            titles[row["id"]] = row["title"]
    return by_title, titles


def split_entry(text):
    if not text.startswith("+++\n"):
        raise ValueError("no front matter")
    end = text.index("\n+++\n", 4)
    return text[4:end], text[end + 5 :]


def parse_citations(text):
    """[(title, page)] when the whole text is a citation list, else None."""
    text = text.strip()
    out = []
    pos = 0
    while pos < len(text):
        m = CITATION.match(text, pos)
        if not m:
            return None
        out.append((m.group(1).strip(), m.group(2)))
        pos = m.end()
    return out or None


def footnote_blocks(lines):
    """[(start, end, marker, anchor, text)] for each level-six footnote heading; the block runs to
    the next heading of any level (or the end)."""
    blocks = []
    for i, line in enumerate(lines):
        m = FOOTNOTE_HEADING.match(line)
        if not m:
            continue
        j = i + 1
        while j < len(lines) and not HEADING.match(lines[j]):
            j += 1
        text = " ".join(l.strip() for l in lines[i + 1 : j] if l.strip())
        blocks.append((i, j, m.group(1), m.group(2), text))
    return blocks


def page_span(raw):
    m = PAGE.match(raw)
    if not m:
        return None
    lo = int(m.group(1))
    hi = m.group(2)
    if hi is None:
        return lo, lo
    hi_i = int(hi)
    if len(hi) < len(m.group(1)):  # "263-4" abbreviates 263-264
        hi_i = int(m.group(1)[: len(m.group(1)) - len(hi)] + hi)
    return lo, hi_i


def fmt_span(lo, hi):
    return str(lo) if lo == hi else f"{lo}-{hi}"


def merge_pages(existing, cited):
    """Merge cited page strings into an existing page string (or None). The existing page stays: a
    cited page that an existing token covers adds nothing; one it does not cover is added, joined
    with the existing tokens it overlaps or touches. Returns (page or None, changed)."""
    toks = []  # [lo, hi, raw]
    opaque = []
    for raw in [t.strip() for t in (existing or "").split(",") if t.strip()]:
        sp = page_span(raw)
        if sp is None:
            opaque.append(raw)
        else:
            toks.append([sp[0], sp[1], raw])
    changed = False
    for raw in cited:
        lo, hi = page_span(raw)
        if any(t[0] <= lo and hi <= t[1] for t in toks):
            continue
        changed = True
        near = [t for t in toks if t[0] <= hi + 1 and lo <= t[1] + 1]
        for t in near:
            toks.remove(t)
            lo, hi = min(lo, t[0]), max(hi, t[1])
        toks.append([lo, hi, fmt_span(lo, hi)])
    toks.sort(key=lambda t: (t[0], t[1]))
    out = [t[2] for t in toks] + opaque
    return (", ".join(out) if out else None), changed


def toml_str(s):
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def emit_rows(sources, expanded):
    out = []
    for r in sources:
        out += ["[[sources]]", f"publication = {toml_str(r['publication'])}"]
        if r.get("page"):
            out.append(f"page = {toml_str(r['page'])}")
    for r in expanded:
        out += ["[[expanded_in]]", f"publication = {toml_str(r['publication'])}"]
        if r.get("page"):
            out.append(f"page = {toml_str(r['page'])}")
        if r.get("via"):
            out.append(f"via = {toml_str(r['via'])}")
    return out


def replace_rows(front_lines, new_rows):
    """Swap the contiguous `[[sources]]`/`[[expanded_in]]` tables of the header for new_rows."""
    first = next(
        (i for i, l in enumerate(front_lines) if l in ("[[sources]]", "[[expanded_in]]")), None
    )
    fields = next(i for i, l in enumerate(front_lines) if l == "[fields]")
    if first is None:
        at = fields - 1 if fields > 0 and front_lines[fields - 1] == "" else fields
        return front_lines[:at] + new_rows + front_lines[at:]
    last = fields - 1 if front_lines[fields - 1] == "" else fields
    for l in front_lines[first:last]:
        if l not in ("[[sources]]", "[[expanded_in]]") and not re.match(
            r'^(publication|page|via) = ".*"$', l
        ):
            raise ValueError(f"unexpected line between the source tables and [fields]: {l!r}")
    return front_lines[:first] + new_rows + front_lines[last:]


def remove_markers(body, entry_id, anchors):
    n = 0
    for anchor in anchors:
        marker = r"\^\[[^\]]*\]\(" + re.escape(f"{entry_id}#{anchor}") + r"\)\^"
        # a marker alone on its line: drop the line
        body, k = re.subn(r"(?m)^[ \t]*" + marker + r"[ \t]*\n", "", body)
        n += k
        # a marker after a word: drop it and one space before it
        body, k = re.subn(r"[ \t]?" + marker, "", body)
        n += k
    return body, n


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("corpus")
    ap.add_argument("--decisions", default=str(Path(__file__).with_name("citation-footnotes-112.tsv")))
    ap.add_argument("--report")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    corpus = Path(args.corpus)
    by_title, titles = load_publications(corpus)

    decisions = defaultdict(dict)  # entry -> {(anchor, publication, page): row}
    with open(args.decisions, newline="") as f:
        for row in csv.DictReader(f, delimiter="\t"):
            key = (row["anchor"], row["publication"], row["page"])
            if key in decisions[row["entry_id"]]:
                sys.exit(f"duplicate decision row {row['entry_id']} {key}")
            if row["verdict"] not in ("holds", "fails", "unchecked"):
                sys.exit(f"bad verdict {row['verdict']!r} for {row['entry_id']} {key}")
            decisions[row["entry_id"]][key] = row

    exclusions_path = corpus / "exclusions.toml"
    exclusions_text = exclusions_path.read_text()
    new_exclusions = []
    report = []
    stats = defaultdict(int)
    errors = []
    unmapped = set()

    for entry_id in sorted(decisions):
        path = corpus / "entries" / (entry_id.removeprefix("ref/") + ".md")
        text = path.read_text()
        front, body = split_entry(text)
        fm = tomllib.loads(front)
        if fm["id"] != entry_id:
            errors.append(f"{path}: id is {fm['id']!r}, not {entry_id!r}")
            continue
        lines = body.split("\n")
        blocks = footnote_blocks(lines)
        source_ids = fm.get("source_ids", [])
        want = decisions[entry_id]
        seen = set()
        removed = []  # (start, end, anchor)
        cites = []  # (anchor, publication, page, decision)
        seen_anchors = set()
        for start, end, marker, anchor, btext in blocks:
            parsed = parse_citations(btext)
            if parsed is None:
                continue
            ids = []
            for title, page in parsed:
                pub = by_title.get(norm_title(title))
                if pub is None:
                    unmapped.add(title)
                ids.append((pub, page))
            if any(p is None for p, _ in ids):
                continue
            if not any((anchor, p, pg) in want for p, pg in ids):
                continue  # a citation-like block this ticket does not cover
            if anchor in seen_anchors:
                errors.append(f"{entry_id}: footnote anchor {anchor} occurs twice")
            seen_anchors.add(anchor)
            for pub, page in ids:
                d = want.get((anchor, pub, page))
                if d is None:
                    errors.append(f"{entry_id} {anchor}: citation {pub} p. {page} has no decision row")
                    continue
                seen.add((anchor, pub, page))
                cites.append((anchor, pub, page, d))
            removed.append((start, end, anchor))
        if not removed:
            stats["entries already done"] += 1
            continue
        for key in sorted(set(want) - seen):
            errors.append(f"{entry_id}: decision row {key} matches no citation in the entry")

        # sources / expanded_in rows
        sources = [dict(r) for r in fm.get("sources", [])]
        expanded = [dict(r) for r in fm.get("expanded_in", [])]
        by_pub = defaultdict(list)
        for anchor, pub, page, d in cites:
            if d["verdict"] == "holds":
                by_pub[pub].append(page)
        for pub in dict.fromkeys(p for _, p, _, d in cites if d["verdict"] == "holds"):
            pages = by_pub[pub]
            if pub in source_ids:
                row = next((r for r in sources if r["publication"] == pub), None)
                page, changed = merge_pages(row.get("page") if row else None, pages)
                if row is None:
                    idx = source_ids.index(pub)
                    at = next(
                        (i for i, r in enumerate(sources) if source_ids.index(r["publication"]) > idx),
                        len(sources),
                    )
                    sources.insert(at, {"publication": pub, "page": page})
                    kind = "sources-added"
                elif changed:
                    row["page"] = page
                    kind = "sources-page-merged"
                else:
                    kind = "sources-already-present"
            else:
                row = next((r for r in expanded if r["publication"] == pub), None)
                page, changed = merge_pages(row.get("page") if row else None, pages)
                if row is None:
                    expanded.append({"publication": pub, "page": page})
                    kind = "expanded_in-added"
                elif changed:
                    row["page"] = page
                    kind = "expanded_in-page-merged"
                else:
                    kind = "expanded_in-already-present"
            stats[kind] += 1
            report.append((entry_id, titles[pub], ", ".join(pages), kind, page or ""))

        # exclusions: one row per entry
        bad = [(a, p, pg, d) for a, p, pg, d in cites if d["verdict"] != "holds"]
        if bad:
            prov = fm["provenance"][0]
            ex_path = f"{prov['path']}#{prov['record']}"
            parts = []
            for _, p, pg, d in bad:
                parts.append(f"{titles[p]} p. {pg} ({d['evidence']})")
                report.append((entry_id, titles[p], pg, "excluded", d["evidence"]))
                stats["excluded"] += 1
            n = len(bad)
            reason = (
                f"{n} page-citation footnote{'s' if n != 1 else ''} not converted to a source row "
                f"(#112): " + "; ".join(parts) + ". The footnote is removed; no record is left out."
            )
            row = f"[[excluded]]\npath = {toml_str(ex_path)}\nrecords = 0\nreason = {toml_str(reason)}\n"
            if row not in exclusions_text:
                new_exclusions.append(row)

        # write the entry
        for start, end, anchor in sorted(removed, reverse=True):
            del lines[start:end]
        new_body = "\n".join(lines)
        new_body, nmark = remove_markers(new_body, entry_id, [a for _, _, a in removed])
        stats["marker references removed"] += nmark
        new_body = new_body.rstrip("\n") + "\n"
        new_front = "\n".join(replace_rows(front.split("\n"), emit_rows(sources, expanded)))
        stats["footnote blocks removed"] += len(removed)
        stats["entries changed"] += 1
        left = re.findall(r"#footnote-[^)\s}]+", new_body)
        orphan = [a for _, _, a in removed if f"#{a})" in new_body]
        if orphan:
            errors.append(f"{entry_id}: marker references to a removed block remain: {orphan}")
        if not args.dry_run:
            path.write_text("+++\n" + new_front + "\n+++\n" + new_body)

    if unmapped:
        print("titles that map to no publication:", file=sys.stderr)
        for t in sorted(unmapped):
            print("  " + t, file=sys.stderr)
    if errors:
        for e in errors:
            print("error:", e, file=sys.stderr)
        sys.exit(1)
    if new_exclusions and not args.dry_run:
        with open(exclusions_path, "a") as f:
            f.write("\n" + "\n".join(new_exclusions))
    stats["exclusion rows appended"] = len(new_exclusions)
    if args.report:
        with open(args.report, "w", newline="") as f:
            w = csv.writer(f, delimiter="\t", lineterminator="\n")
            w.writerow(["entry_id", "book", "cited_pages", "action", "result"])
            w.writerows(report)
    for k in sorted(stats):
        print(f"{k}: {stats[k]}")


if __name__ == "__main__":
    main()
