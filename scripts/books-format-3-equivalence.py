#!/usr/bin/env python3
"""Compare the library compiled from this corpus before and after the format 3 layout
migration (phynics/cast-iron#425): `books.json` book by book, the first book of every entry, and
the stable section anchors against the app's legacy section table.

Compile the library from the corpus before and after `cast-iron-corpus migrate-layout`, with the
same inputs as `cargo xtask content`, then run it with Python 3.11 or later:

  python3 -I scripts/books-format-3-equivalence.py BEFORE/books.json AFTER/books.json \\
      CORPUS_DIR OUT_DIR APP/sources/legacy-sections.json

CORPUS_DIR is the migrated corpus (it reads `[[sources]]` pages). OUT_DIR gets `differences.tsv`,
one row per difference (book, class, entry, detail). Compare the other files of the two libraries
with `sha256sum`: only `books.json`, `search.bin` and `manifest.json` may differ.

Classes: book-new-after, book-title-changed, book-basis-changed, chapter-shape-changed,
chapter-moved, entry-gained, entry-lost, nesting-differs, node-title-differs, order-same-page-tie,
order-different-page, order-unpaged, order-group-changed, curated-tree-differs, catchall-*.
"""
import collections
import json
import os
import re
import sys
import tomllib

CATCH = "New entries (page order)"


def slug(text):
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def lead(page):
    match = re.match(r"\s*(\d+)", page or "")
    return int(match.group(1)) if match else None


def load_entries(corpus):
    info = {}
    for root, _, files in os.walk(os.path.join(corpus, "entries")):
        for name in files:
            if not name.endswith(".md"):
                continue
            text = open(os.path.join(root, name), encoding="utf-8").read()
            front = tomllib.loads(re.match(r"\+\+\+\n(.*?)\n\+\+\+\n", text, re.S).group(1))
            pages, rows = {}, {}
            for source in front.get("sources", []):
                rows.setdefault(source["publication"], []).append(source.get("page"))
                if source["publication"] not in pages and lead(source.get("page")) is not None:
                    pages[source["publication"]] = lead(source["page"])
            info[front["id"]] = {"pages": pages, "rows": rows}
    return info


def flatten(book):
    """(chapter, entry, depth, host entry, node title) in document order."""
    out = []

    def walk(node, chapter, depth, host):
        entry = node.get("entry")
        if entry is not None:
            out.append((chapter, entry, depth, host, node["title"]))
        for child in node.get("children", []):
            walk(child, chapter, depth + 1, entry if entry is not None else host)

    for chapter in book["chapters"]:
        walk(chapter, chapter["title"], 0, None)
    return out


def compare_books(before, after, info, out_dir):
    rows = []

    def add(book, cls, entry, detail):
        rows.append((book, cls, entry, detail))

    curated_identical = 0
    for src in sorted(after):
        a, b = after[src], before.get(src)
        if b is None:
            for chapter, entry, *_ in flatten(a):
                add(src, "book-new-after", entry, f"chapter={chapter}")
            continue
        curated = any(c["title"] not in ("Page order", "Unpaged", CATCH) for c in b["chapters"])
        for key in ("title", "basis", "review"):
            if a[key] != b[key]:
                detail = f"{b[key]!r} -> {a[key]!r}" if key == "title" else "text differs"
                add(src, f"book-{key}-changed", "", detail)
        if curated:
            if [c for c in a["chapters"] if c["title"] != CATCH] == [
                c for c in b["chapters"] if c["title"] != CATCH
            ]:
                curated_identical += 1
            else:
                add(src, "curated-tree-differs", "", "stored chapters differ")
            fa = [x[1] for c in a["chapters"] if c["title"] == CATCH for x in flatten({"chapters": [c]})]
            fb = [x[1] for c in b["chapters"] if c["title"] == CATCH for x in flatten({"chapters": [c]})]
            for entry in sorted(set(fa) - set(fb)):
                add(src, "catchall-only-after", entry, "")
            for entry in sorted(set(fb) - set(fa)):
                add(src, "catchall-only-before", entry, "")
            if fa != fb:
                add(src, "catchall-order-differs", "", f"{len(fb)} rows before, {len(fa)} after")
            continue
        titles_b = [c["title"] for c in b["chapters"]]
        titles_a = [c["title"] for c in a["chapters"]]
        if titles_b != titles_a:
            add(src, "chapter-shape-changed", "", f"{titles_b} -> {titles_a}")
        flat_b, flat_a = flatten(b), flatten(a)
        mb, ma = {x[1]: x for x in flat_b}, {x[1]: x for x in flat_a}
        for entry in sorted(set(mb) - set(ma)):
            add(src, "entry-lost", entry, "")
        for entry in sorted(set(ma) - set(mb)):
            add(src, "entry-gained", entry, f"chapter={ma[entry][0]}")
        for entry in sorted(set(mb) & set(ma)):
            x, y = mb[entry], ma[entry]
            if x[0] != y[0]:
                page = info[entry]["pages"].get(src)
                add(src, "chapter-moved", entry, f"{x[0]} -> {y[0]}; page {page} from the [[sources]] row")
            if x[2] != y[2] or x[3] != y[3]:
                add(src, "nesting-differs", entry, f"depth {x[2]}->{y[2]} host {x[3]}->{y[3]}")
            if x[4] != y[4]:
                add(src, "node-title-differs", entry, f"{x[4]!r} -> {y[4]!r}")
        keep = {e for e in mb if e in ma and mb[e][0] == ma[e][0] and mb[e][3] == ma[e][3]}

        def groups(flat):
            out = collections.defaultdict(list)
            for chapter, entry, _, host, _ in flat:
                if entry in keep:
                    out[(chapter, host)].append(entry)
            return out

        gb, ga = groups(flat_b), groups(flat_a)
        for key, new in ga.items():
            old = gb.get(key, [])
            if old == new:
                continue
            position = {e: i for i, e in enumerate(old)}
            for p, q in zip(new, new[1:]):
                if position[p] > position[q]:
                    pp, pq = info[p]["pages"].get(src), info[q]["pages"].get(src)
                    cls = (
                        "order-unpaged"
                        if key[0] == "Unpaged"
                        else "order-same-page-tie"
                        if pp == pq
                        else "order-different-page"
                    )
                    add(src, cls, p, f"now before {q}; pages {pp}/{pq}; was after")
            add(src, "order-group-changed", "", f"chapter={key[0]} host={key[1]} n={len(new)}")
    with open(os.path.join(out_dir, "differences.tsv"), "w", encoding="utf-8") as handle:
        handle.write("book\tclass\tentry\tdetail\n")
        for row in rows:
            handle.write("\t".join(x.replace("\t", " ").replace("\n", " ") for x in row) + "\n")
    counts = collections.Counter(r[1] for r in rows)
    print(f"books before {len(before)}, after {len(after)}; curated trees identical: {curated_identical}")
    for cls, n in sorted(counts.items()):
        print(f"{n:7d}  {cls}  ({len({r[0] for r in rows if r[1] == cls})} books)")
    print("books with no difference:", len(after) - len({r[0] for r in rows}))


def first_books(books):
    first = {}
    for book in books.values():
        def walk(node):
            entry = node.get("entry")
            if entry is not None and entry not in first:
                first[entry] = book["source"]
            for child in node.get("children", []):
                walk(child)

        for chapter in book["chapters"]:
            walk(chapter)
    return first


def identity(node):
    anchor = slug(node["anchor"]) if node.get("anchor") else ""
    if node.get("entry") is not None:
        base = slug(node["entry"])
        return f"{base}--{anchor}" if anchor else base
    own = anchor or slug(node["title"])
    return "h-" + (own or "section")


def book_anchors(book):
    """The row anchors of books::section_anchors, for every chapter of the book."""
    found = set()
    for chapter in book["chapters"]:
        used = set()

        def walk(node, parent):
            for child in node.get("children", []):
                ident = identity(child)
                base = f"row-{ident}" if child.get("entry") is not None else f"row-{parent}--{ident}"
                anchor, suffix = base, 2
                while anchor in used:
                    anchor, suffix = f"{base}-{suffix}", suffix + 1
                used.add(anchor)
                found.add(anchor)
                walk(child, ident)

        walk(chapter, identity(chapter))
    return found


def main():
    before_p, after_p, corpus, out_dir, legacy_p = sys.argv[1:6]
    before = {b["source"]: b for b in json.load(open(before_p, encoding="utf-8"))["books"]}
    after = {b["source"]: b for b in json.load(open(after_p, encoding="utf-8"))["books"]}
    os.makedirs(out_dir, exist_ok=True)
    compare_books(before, after, load_entries(corpus), out_dir)

    fb, fa = first_books(before), first_books(after)
    print(
        f"entries placed: {len(fb)} before, {len(fa)} after; first book changes: "
        f"{sum(1 for e in fb if e in fa and fb[e] != fa[e])}; only before: {len(set(fb) - set(fa))}"
    )

    table = json.load(open(legacy_p, encoding="utf-8"))["books"]
    lost, rows = [], 0
    for src, wanted in table.items():
        was = book_anchors(before[src]) if src in before else set()
        now = book_anchors(after[src]) if src in after else set()
        for toc, anchor in wanted.items():
            rows += 1
            if anchor in was and anchor not in now:
                lost.append((src, toc, anchor))
    print(f"legacy section rows: {rows}; resolving before and not after: {len(lost)}")
    for item in lost:
        print("  ", *item)
    gone = {s: len(book_anchors(before[s]) - book_anchors(after[s])) for s in before if s in after}
    print("books that lost a row anchor:", {s: n for s, n in gone.items() if n})


if __name__ == "__main__":
    main()
