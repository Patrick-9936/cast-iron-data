#!/usr/bin/env python3
"""Audit book placements against entry membership in the Cast Iron corpus (issue #420).

Read-only. Stdlib only (Python 3.11+ for tomllib). Rerun it on any checkout of the corpus:

    python3 scripts/placement-audit.py <corpus-dir> [--json out.json] [--limit N]

It reads `publications.toml`, `books.toml` and every `entries/**/*.md`, and reports:

  1. every placement whose book is not in the entry's `source_ids` (the proposed corpus-check
     rule), and every book with no `publications.toml` row (the second proposed rule);
  2. those placements grouped by likely cause:
       (c) phantom: the book has no publications row;
       (a) evidence: the entry's `[[sources]]` or a body `**Sources:**` line names the book,
           so `source_ids` is probably missing it;
       (b) listing: a catch-all ("New entries (page order)"), "Page order" or "Unpaged"
           chapter placement with no evidence in the entry;
       (d) other: a curated chapter placement with no evidence;
  3. a sample of entries per group, with the mechanical fix;
  4. what the rule rejects today and what it rejects after each fix is applied in simulation;
  5. what the removals do to the first-placement ("canonical") book of each entry and to the
     catch-all reachability rules (the Rust compiler is the authority for the final numbers).

A placement is a distinct (book, entry) pair; an entry named twice in one book counts once.
Output is deterministic: sorted, no timestamps.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import tomllib
from collections import Counter, defaultdict
from pathlib import Path

CATCH_ALL = "New entries (page order)"
LISTING_TITLES = {"Page order", "Unpaged"}
SAMPLE = 10


def norm(text: str) -> str:
    """Normalise quotes and case so a printed title matches a body line."""
    return (
        text.replace("’", "'")
        .replace("‘", "'")
        .replace("“", '"')
        .replace("”", '"')
        .casefold()
    )


def split_entry(text: str) -> tuple[str, str]:
    """Front matter and body of an entry file."""
    assert text.startswith("+++\n"), "entry must start with +++"
    end = text.index("\n+++\n", 4)
    return text[4:end], text[end + 5 :]


# ---------------------------------------------------------------- load


def load_publications(root: Path) -> dict[str, dict]:
    data = tomllib.loads((root / "publications.toml").read_text(encoding="utf-8"))
    return {p["id"]: p for p in data["publication"]}


def load_books(root: Path) -> list[dict]:
    """Every book with its placements.

    A placement is (entry id, kind of chapter, top-level chapter title, path of titles).
    `kind` is "catch_all" under a `New entries (page order)` node, "listing" under a
    `Page order` or `Unpaged` top-level chapter, else "curated".
    """
    data = tomllib.loads((root / "books.toml").read_text(encoding="utf-8"))
    books = []
    for order, book in enumerate(data["books"]):
        placements: list[dict] = []

        def walk(node: dict, trail: list[str], top: str, in_catch_all: bool) -> None:
            title = node.get("title", "")
            trail = trail + [title]
            in_catch_all = in_catch_all or title == CATCH_ALL
            entry = node.get("entry")
            if entry:
                if in_catch_all:
                    kind = "catch_all"
                elif top in LISTING_TITLES:
                    kind = "listing"
                else:
                    kind = "curated"
                placements.append(
                    {"entry": entry, "kind": kind, "top": top, "trail": " > ".join(trail)}
                )
            for child in node.get("children", []):
                walk(child, trail, top, in_catch_all)

        for chapter in book.get("chapters", []):
            walk(chapter, [], chapter.get("title", ""), False)
        books.append(
            {
                "order": order,
                "source": book["source"],
                "title": book.get("title", book["source"]),
                "placements": placements,
            }
        )
    return books


LINK_RE = re.compile(r"\]\((ref/[^)#\s]+)")
TARGET_RE = re.compile(r'^target = "(ref/[^"]+)"', re.M)
SOURCES_LINE_RE = re.compile(r"^(?:>\s*)?\*\*Sources?:\*\*\s*(.*)$", re.M)


def load_entries(root: Path) -> dict[str, dict]:
    entries: dict[str, dict] = {}
    for path in sorted((root / "entries").rglob("*.md")):
        text = path.read_text(encoding="utf-8")
        front, body = split_entry(text)
        meta = tomllib.loads(front)
        links = set(LINK_RE.findall(body)) | set(TARGET_RE.findall(body))
        for rel in meta.get("relations", []):
            links.add(rel["target"])
        entries[meta["id"]] = {
            "id": meta["id"],
            "kind": meta["kind"],
            "title": meta["title"],
            "source_ids": list(meta.get("source_ids", [])),
            "table_sources": [s["publication"] for s in meta.get("sources", [])],
            "body_sources_text": SOURCES_LINE_RE.findall(body),
            "links": links,
            "relations": [(r["kind"], r["target"]) for r in meta.get("relations", [])],
        }
    return entries


def titles_in_text(text: str, title_index: list[tuple[str, str]]) -> set[str]:
    """Publication ids whose title appears in a `**Sources:**` line.

    Longest titles match first and consume their span, so `Bestiary` does not match inside
    `Bestiary 2`.
    """
    work = norm(text)
    found: set[str] = set()
    for title, pub in title_index:
        pattern = re.compile(r"(?<![\w])" + re.escape(title) + r"(?![\w])")
        if pattern.search(work):
            found.add(pub)
            work = pattern.sub(" " * len(title), work)
    return found


# ---------------------------------------------------------------- analysis


def simulate_reachable_without_catch_all(entries: dict[str, dict], outside: set[str]) -> set[str]:
    """Mirror of `reachable_without_catch_all` (crates/content-compiler/src/reachability.rs).

    Rule 1: placed outside the catch-all chapter, or any kind except `rule`.
    Rule 3: a reachable entry's links and relations reach their targets.
    Rule 4: an addon, variant or revision hangs off a reachable base.
    """
    reachable = {i for i, e in entries.items() if e["kind"] != "rule" or i in outside}
    while True:
        added: set[str] = set()
        for i in reachable:
            for t in entries[i]["links"]:
                if t in entries and t not in reachable:
                    added.add(t)
        for i, e in entries.items():
            if i in reachable:
                continue
            if any(k in ("addon", "variant", "revision") and t in reachable for k, t in e["relations"]):
                added.add(i)
        if not added:
            return reachable
        reachable |= added


def canonical_book(books: list[dict], placements_by_entry: dict[str, list[tuple[int, str]]], entry: str,
                   skip_catch_all: bool) -> str | None:
    """First placement in book order (graph.rs `place`), optionally skipping catch-all chapters."""
    rows = placements_by_entry.get(entry, [])
    if skip_catch_all:
        curated = [r for r in rows if r[1] != "catch_all"]
        rows = curated or rows
    return books[min(r[0] for r in rows)]["source"] if rows else None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("corpus", type=Path)
    ap.add_argument("--json", type=Path, help="write the full machine-readable result here")
    ap.add_argument("--limit", type=int, default=20, help="rows in each top-N table")
    args = ap.parse_args()
    root: Path = args.corpus

    pubs = load_publications(root)
    books = load_books(root)
    entries = load_entries(root)
    title_index = sorted(((norm(p["title"]), pid) for pid, p in pubs.items()), key=lambda t: -len(t[0]))
    book_by_source = {b["source"]: b for b in books}

    # Evidence per entry: publications named by [[sources]] and by body `**Sources:**` lines.
    for e in entries.values():
        e["body_sources"] = set()
        for line in e["body_sources_text"]:
            e["body_sources"] |= titles_in_text(line, title_index)

    # Distinct (book, entry) placements; keep the strongest-kind row for the sample.
    distinct: dict[tuple[str, str], dict] = {}
    unresolved: list[tuple[str, str]] = []
    raw_nodes = 0
    for b in books:
        for p in b["placements"]:
            raw_nodes += 1
            if p["entry"] not in entries:
                unresolved.append((b["source"], p["entry"]))
                continue
            key = (b["source"], p["entry"])
            rank = {"curated": 0, "listing": 1, "catch_all": 2}
            if key not in distinct or rank[p["kind"]] < rank[distinct[key]["kind"]]:
                distinct[key] = dict(p, book=b["source"])
            else:
                distinct[key].setdefault("dup", 0)
                distinct[key]["dup"] += 1

    phantoms = sorted(b["source"] for b in books if b["source"] not in pubs)
    books_without_row = sorted(set(pubs) - set(book_by_source))

    # Entries that an add-on, revision or variant of the book points at: base -> {entry}.
    partners: dict[str, set[str]] = defaultdict(set)
    for oid, oe in entries.items():
        for kind, target in oe["relations"]:
            if kind in ("addon", "revision", "variant"):
                partners[target].add(oid)

    violations: list[dict] = []
    for (src, eid), p in sorted(distinct.items()):
        e = entries[eid]
        if src in e["source_ids"]:
            continue
        in_table = src in e["table_sources"]
        in_body = src in e["body_sources"]
        carried = re.match(r"ref/carried/([^/]+)/", eid)
        id_path = bool(carried and carried.group(1) == src)
        own = [o for o in partners.get(eid, ()) if src in entries[o]["source_ids"]]
        partner = bool(own)
        partner_placed = any((src, o) in distinct for o in own)
        if src not in pubs:
            group = "c"
        elif in_table or in_body:
            group = "a"
        elif p["kind"] in ("catch_all", "listing"):
            group = "b"
        else:
            group = "d"
        violations.append(
            {
                "book": src,
                "entry": eid,
                "entry_title": e["title"],
                "entry_kind": e["kind"],
                "chapter_kind": p["kind"],
                "top_chapter": p["top"],
                "group": group,
                "evidence": "sources_table" if in_table else "body_line" if in_body else "none",
                "carried_id_names_book": id_path,
                "addon_partner_in_book": partner,
                "addon_partner_placed_in_book": partner_placed,
                "source_ids": e["source_ids"],
            }
        )
    by_group: dict[str, list[dict]] = defaultdict(list)
    for v in violations:
        by_group[v["group"]].append(v)

    # Placements by entry for the simulations.
    def placement_table(skip: set[tuple[str, str]]) -> dict[str, list[tuple[int, str]]]:
        table: dict[str, list[tuple[int, str]]] = defaultdict(list)
        for (src, eid), p in distinct.items():
            if (src, eid) in skip:
                continue
            table[eid].append((book_by_source[src]["order"], p["kind"]))
        return table

    bad = {(v["book"], v["entry"]) for v in violations}
    now = placement_table(set())
    after_remove_all = placement_table(bad)

    # Fix simulation. (a) adds the book to source_ids, so the placement stays and becomes valid.
    # (b) and (c) remove the placement. (d) is not fixed mechanically.
    removal = {(v["book"], v["entry"]) for v in violations if v["group"] in ("b", "c")}
    after_mech = placement_table(removal)
    residual_d = {(v["book"], v["entry"]) for v in by_group["d"]}

    def outside(table: dict[str, list[tuple[int, str]]]) -> set[str]:
        return {eid for eid, rows in table.items() if any(k != "catch_all" for _, k in rows)}

    reach_now = simulate_reachable_without_catch_all(entries, outside(now))
    reach_mech = simulate_reachable_without_catch_all(entries, outside(after_mech))
    reach_all = simulate_reachable_without_catch_all(entries, outside(after_remove_all))
    newly_unreachable_mech = sorted(i for i in reach_now if i not in reach_mech)
    newly_unreachable_all = sorted(i for i in reach_now if i not in reach_all)

    def first_book(table: dict[str, list[tuple[int, str]]], eid: str) -> str:
        """graph.rs `BookLookup::place`: the first book in book order that places the entry.
        An entry with no placement falls back to the catalog `source`, which is `source_ids[0]`."""
        return canonical_book(books, table, eid, False) or entries[eid]["source_ids"][0]

    canon_changes = [
        (eid, first_book(now, eid), first_book(after_mech, eid))
        for eid in entries
        if first_book(now, eid) != first_book(after_mech, eid)
    ]
    # Entries whose first placement is outside their source_ids today: what `is_stub_active`
    # tests when a reader turns a book off.
    canon_outside_now = {
        eid: (first_book(now, eid), min(r[1] for r in now[eid] if books[r[0]]["source"] == first_book(now, eid)) if eid in now else "-")
        for eid, e in entries.items()
        if first_book(now, eid) not in e["source_ids"]
    }

    group_a_set = {(v["book"], v["entry"]) for v in by_group["a"]}
    a_by_entry: dict[str, set[str]] = defaultdict(set)
    for b_, e_ in group_a_set:
        a_by_entry[e_].add(b_)

    def in_own_book(eid: str, table: dict[str, list[tuple[int, str]]], extra: bool) -> bool:
        """True when some placement is in a book of the entry's own `source_ids`."""
        ids = set(entries[eid]["source_ids"]) | (a_by_entry.get(eid, set()) if extra else set())
        return any(books[o]["source"] in ids for o, _ in table.get(eid, []))

    no_own_placement_now = sorted(e for e in entries if not in_own_book(e, now, False))
    no_own_placement_after = sorted(e for e in entries if not in_own_book(e, after_mech, True))
    lose_all_placements = sorted(eid for eid in now if eid not in after_mech)

    # ------------------------------------------------------------ phantom detail
    phantom_rows = []
    for ph in phantoms:
        b = book_by_source[ph]
        placed = sorted({p["entry"] for p in b["placements"] if p["entry"] in entries})
        kinds = Counter(distinct[(ph, e)]["kind"] for e in placed if (ph, e) in distinct)
        # Best duplicate: publication that most of the phantom's entries list in source_ids.
        votes: Counter[str] = Counter()
        for e in placed:
            for s in entries[e]["source_ids"]:
                votes[s] += 1
        # Title similarity as a tie-breaker.
        import difflib

        def sim(pid: str) -> float:
            return difflib.SequenceMatcher(None, norm(b["title"]), norm(pubs[pid]["title"])).ratio()

        cand = sorted(pubs, key=lambda pid: (-votes.get(pid, 0), -sim(pid), pid))[:3]
        also_in_other = sum(
            1
            for e in placed
            if any(src != ph and (src, e) in distinct for src in book_by_source)
        )
        phantom_rows.append(
            {
                "book": ph,
                "book_title": b["title"],
                "entries": len(placed),
                "chapter_kinds": dict(kinds),
                "also_placed_elsewhere": also_in_other,
                "duplicate_of": (
                    pubs[cand[0]]["title"]
                    if placed and votes.get(cand[0], 0) / len(placed) >= 0.5
                    else None
                ),
                "likely_duplicates": [
                    {"id": pid, "title": pubs[pid]["title"], "entries_naming_it": votes.get(pid, 0),
                     "title_similarity": round(sim(pid), 2)}
                    for pid in cand
                ],
            }
        )

    # ------------------------------------------------------------ report
    out: list[str] = []
    w = out.append
    total_placements = len(distinct)
    w("# Placement audit")
    w("")
    w(f"corpus entries: {len(entries)}")
    w(f"publications rows: {len(pubs)}")
    w(f"books in books.toml: {len(books)}")
    w(f"book nodes that name an entry: {raw_nodes}")
    w(f"distinct (book, entry) placements: {total_placements}")
    w(f"placements naming an id that is not an entry: {len(unresolved)}")
    w("")
    w("## Rule 1: a placement's book must be in the entry's source_ids")
    w("")
    w(f"rejected today: {len(violations)} placements ({100*len(violations)/total_placements:.1f}% of {total_placements})")
    w(f"entries with at least one such placement: {len({v['entry'] for v in violations})}")
    w("")
    w("## Rule 2: every book has a publications row")
    w("")
    w(f"books with no publications row: {len(phantoms)}")
    w(f"publications with no books row: {len(books_without_row)} {books_without_row}")
    w("")
    w("## Groups")
    w("")
    w("| group | meaning | placements | entries | proposed fix |")
    w("|---|---|---:|---:|---|")
    desc = {
        "a": ("evidence names the book", "add the book to source_ids"),
        "b": ("catch-all / Page order / Unpaged, no evidence", "remove the placement"),
        "c": ("phantom book (no publications row)", "delete the book; fold into the real publication"),
        "d": ("curated chapter, no evidence", "decide by hand"),
    }
    for g in "abcd":
        rows = by_group.get(g, [])
        w(f"| {g} | {desc[g][0]} | {len(rows)} | {len({r['entry'] for r in rows})} | {desc[g][1]} |")
    w(f"| total | | {len(violations)} | {len({v['entry'] for v in violations})} | |")
    w("")
    w("### Chapter kind inside each group")
    w("")
    w("| group | curated | catch-all | Page order / Unpaged |")
    w("|---|---:|---:|---:|")
    for g in "abcd":
        c = Counter(r["chapter_kind"] for r in by_group.get(g, []))
        w(f"| {g} | {c['curated']} | {c['catch_all']} | {c['listing']} |")
    w("")
    w("### Evidence inside group (a)")
    w("")
    ev = Counter(r["evidence"] for r in by_group.get("a", []))
    w(f"- `[[sources]]` row names the book: {ev['sources_table']}")
    w(f"- body `**Sources:**` line names the book: {ev['body_line']}")
    w("")
    w("### Top books per group")
    w("")
    per_book: dict[str, Counter] = defaultdict(Counter)
    for v in violations:
        per_book[v["book"]][v["group"]] += 1
    ranked = sorted(per_book, key=lambda b: (-sum(per_book[b].values()), b))
    w(f"| # | book | a | b | c | d | total | placements in book |")
    w("|---:|---|---:|---:|---:|---:|---:|---:|")
    book_totals = Counter(src for (src, _e) in distinct)
    for i, src in enumerate(ranked[: args.limit], 1):
        c = per_book[src]
        title = book_by_source[src]["title"]
        w(f"| {i} | {title} | {c['a']} | {c['b']} | {c['c']} | {c['d']} | {sum(c.values())} | {book_totals[src]} |")
    w(f"")
    w(f"books with at least one rejected placement: {len(per_book)}")
    w("")
    w("### Group (c): phantom books")
    w("")
    w("A book is a likely duplicate when at least half of its entries name one publication in `source_ids`.")
    w("")
    w("| book id | book title | entries | chapter kinds | also placed in another book | likely duplicate of (entries naming it) |")
    w("|---|---|---:|---|---:|---|")
    for r in sorted(phantom_rows, key=lambda r: (-r["entries"], r["book"])):
        top = r["likely_duplicates"][0]
        dup = (
            f"{r['duplicate_of']} ({top['entries_naming_it']} of {r['entries']})"
            if r["duplicate_of"]
            else "none: a one-off web or comic source; the entry's source_ids already name its printed books"
        )
        w(f"| `{r['book']}` | {r['book_title']} | {r['entries']} | {r['chapter_kinds']} | {r['also_placed_elsewhere']} | {dup} |")
    w("")
    for g in "abcd":
        rows = by_group.get(g, [])
        w(f"### Sample, group ({g}): {desc[g][0]}")
        w("")
        # Spread the sample over books so one book does not fill it; group d is listed in full.
        picked: list[dict] = []
        seen_books: Counter[str] = Counter()
        for r in rows:
            if g == "d" or (seen_books[r["book"]] < 2 and len(picked) < SAMPLE):
                picked.append(r)
                seen_books[r["book"]] += 1
        for r in picked:
            w(
                f"- {r['entry_title']} (`{r['entry']}`, {r['entry_kind']}) is placed in "
                f"{book_by_source[r['book']]['title'] if r['book'] in book_by_source else r['book']} "
                f"[{r['chapter_kind']}: {r['top_chapter']}]; source_ids = {r['source_ids']}; "
                f"evidence = {r['evidence']}; carried id names the book = {r['carried_id_names_book']}"
            )
        w("")
    w("### Group (b) detail")
    w("")
    bb = by_group.get("b", [])
    w(f"- catch-all placements: {sum(1 for r in bb if r['chapter_kind']=='catch_all')}; "
      f"Page order / Unpaged placements: {sum(1 for r in bb if r['chapter_kind']=='listing')}")
    w(f"- the entry is the base of an add-on, revision or variant whose own source_ids name the book: "
      f"{sum(1 for r in bb if r['addon_partner_in_book'])}")
    w(f"  - and that add-on, revision or variant is itself placed in the book: "
      f"{sum(1 for r in bb if r['addon_partner_placed_in_book'])}")
    w(f"- entries of kind rule: {sum(1 for r in bb if r['entry_kind']=='rule')}; other kinds: "
      f"{sum(1 for r in bb if r['entry_kind']!='rule')}")
    kinds_b = Counter(r["entry_kind"] for r in bb)
    w(f"- by entry kind: {dict(kinds_b.most_common())}")
    w("")
    w("### Group (d) detail")
    w("")
    dd = by_group.get("d", [])
    w(f"- the carried id path names the placement's book: {sum(1 for r in dd if r['carried_id_names_book'])} of {len(dd)}")
    w("")
    w("## After the mechanical fixes (a: add to source_ids, b and c: remove)")
    w("")
    w(f"rule 1 would still reject: {len(residual_d)} placements (group d, undecided)")
    w(f"rule 2 would still reject: 0 books (phantoms deleted)")
    w("")
    w("## What the fixes change in the app")
    w("")
    w(
        f"entries whose first placement (graph.rs `place`, so `canonical_book_source`) is in a book outside "
        f"their source_ids today: {len(canon_outside_now)}"
    )
    cc = Counter((src, kind) for src, kind in canon_outside_now.values())
    for (src, kind), n in cc.most_common():
        w(f"  - {book_by_source[src]['title']} ({kind} chapter): {n}")
    w(f"entries whose first placement changes after the mechanical fixes: {len(canon_changes)}")
    chg = Counter((b, a) for _e, b, a in canon_changes)
    w("")
    w("first-placement moves (from -> to):")
    for (b, a), n in chg.most_common(10):
        w(f"- {book_by_source[b]['title']} -> {book_by_source[a]['title']}: {n}")
    w("")
    w(f"entries that lose every placement under the mechanical fixes: {len(lose_all_placements)}")
    w(f"entries with no placement in any book of their own source_ids, today: {len(no_own_placement_now)}")
    w(f"entries with no placement in any book of their own source_ids, after the fixes: {len(no_own_placement_after)}")
    w(f"entries reachable without the catch-all chapter today (simulation): {len(reach_now)}")
    w(f"entries newly unreachable after the mechanical fixes (simulation): {len(newly_unreachable_mech)}")
    w(f"entries newly unreachable if every violation is removed (simulation): {len(newly_unreachable_all)}")
    kinds_u = Counter(entries[i]["kind"] for i in newly_unreachable_mech)
    w(f"  by kind: {dict(kinds_u)}")
    for i in newly_unreachable_mech[:SAMPLE]:
        w(f"  - {entries[i]['title']} (`{i}`)")
    w("")
    w("Note: the simulation mirrors reachability.rs. The Rust compiler is the authority.")

    report = "\n".join(out) + "\n"
    sys.stdout.write(report)
    if args.json:
        args.json.write_text(
            json.dumps(
                {
                    "totals": {
                        "entries": len(entries),
                        "publications": len(pubs),
                        "books": len(books),
                        "placements": total_placements,
                        "violations": len(violations),
                    },
                    "phantoms": phantom_rows,
                    "violations": violations,
                    "unresolved": unresolved,
                    "newly_unreachable_mech": newly_unreachable_mech,
                    "no_own_placement_after": no_own_placement_after,
                    "canonical_changes": canon_changes,
                },
                indent=1,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
