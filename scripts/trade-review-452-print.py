#!/usr/bin/env python3
"""Check the rows of the trades review queue against print (phynics/cast-iron#452).

For each row, the script looks for the printed trade name in the text of the book that the row cites, on
the printed page that it cites (a page either side counts: an archetype spans pages). The citation of a
variant row is the source of the subsection that prints the line, not the parent entry's. The verdict goes
into the `print` column of `trade-review-452.tsv`:

  page   the name is on the cited page or next to it
  words  the words of the name are all on the cited page or next to it (a line break, a column or a
         marker in the text splits the name)
  book   the name is in the book, but not near the cited page
  none   the name is not in the book (a spelling or extraction difference; read the page)
  nobook no copy of the book was found

It reads PDFs from the directory that `--books` names (searched recursively, matched to a publication by
the words of its title) and extracts them with `pdftotext` into `--cache`, one text file for each PDF,
named by the SHA-256 of the PDF. The index of the cache records a file only after `pdftotext` succeeded
and wrote text. The directory, the file names and the extracted text stay on the machine that runs the
script: the queue records only the book title, the page and the verdict. Never commit the cache.

  python3 -I scripts/trade-review-452-print.py --books DIR --cache DIR [--only ID-PREFIX]

`--only` limits both the rows that are checked and the rows that are written; the other rows keep their
columns.

Class evidence. For a closed row that names a part of a feature (`power`), the script also searches the
class's own pages in the book that the class entry cites (the class's page and the 16 pages after it) for
the name of the part. The class of an archetype is its `archetype` relation; the class of a class option is
found through its option group (`option-groups.toml`). `class_hit` is `hit` (a search hit: the text occurs
in those pages), `none`, `book` (a hit is not possible: no printed page can be tied to the PDF) or `nobook`;
on a hit `class_book` and `class_page` are the book and the printed page of the first hit. A hit shows that
the book prints the name in the class's section, not that the feature grants it.
"""
import hashlib
import importlib.util
import re
import subprocess
import sys
import tomllib
import unicodedata
from collections import Counter
from pathlib import Path

HERE = Path(__file__).parent
spec = importlib.util.spec_from_file_location("queue", HERE / "trade-review-452.py")
queue = importlib.util.module_from_spec(spec)
spec.loader.exec_module(queue)


def norm(text):
    text = unicodedata.normalize("NFKD", text)
    text = text.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
    text = text.replace("–", "-").replace("—", "-").replace("­", "")
    text = re.sub(r"-\s*\n\s*", "-", text)
    text = re.sub(r"[*_`]", "", text)
    return " ".join(text.lower().split())


def compact(text):
    """Letters and digits only: a PDF that spaces its letters (`T his arc hetype`) still matches."""
    return re.sub(r"[^a-z0-9]+", "", norm(text))


def tokens(text):
    """Lower-case words without apostrophes; a plural loses its s (Blood of the Beast, Blood of Beasts)."""
    words = re.findall(r"[a-z0-9]+", text.lower().replace("'", "").replace("’", ""))
    return {w[:-1] if len(w) > 4 and w.endswith("s") else w for w in words}


def sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def read_pdfs(books, cache):
    """[(file name, text path)] for every PDF under `books`; extracts the ones that the cache lacks."""
    cache.mkdir(parents=True, exist_ok=True)
    index = cache / "index.tsv"
    known = set()
    if index.exists():
        known = {line.split("\t", 1)[0] for line in index.read_text(encoding="utf-8").splitlines() if line}
    out = []
    for f in sorted(Path(books).rglob("*.pdf")):
        digest = sha256(f)
        text = cache / f"{digest}.txt"
        if digest not in known or not text.exists():
            result = subprocess.run(["pdftotext", str(f), str(text)], check=False, capture_output=True)
            if result.returncode != 0 or not text.exists() or text.stat().st_size == 0:
                text.unlink(missing_ok=True)
                print(f"extraction failed, not indexed: {f.name}", file=sys.stderr)
                continue
            with open(index, "a", encoding="utf-8") as handle:
                handle.write(f"{digest}\t{f.name}\n")
            known.add(digest)
        out.append((f.name, text))
    return out


def find_book(title, pdfs):
    want = tokens(title) - {"the", "of", "and", "a"}
    best, score = None, 0
    for name, path in pdfs:
        have = tokens(re.sub(r"^PZO\d+", "", name.removesuffix(".pdf")))
        if not want:
            continue
        s = len(want & have) / len(want) - 0.01 * len(have - want)
        if s > score:
            best, score = path, s
    return best if score >= 0.96 else None


def row_sources(row):
    """The sources whose pages may hold the row: [(publication id, page string)]."""
    data, _ = queue.entry_info(row["id"])
    if row["reason"] == "variant-only":
        occ = queue.variant_for(row)
        out = []
        for title, page in (occ or {}).get("sources", []):
            pid = queue.publication_by_title(title)
            if pid:
                out.append((pid, page))
        return out
    sources = data.get("sources") or [{"publication": i} for i in data.get("source_ids", [])]
    return [(s["publication"], str(s.get("page", ""))) for s in sources]


def main():
    args = sys.argv[1:]
    opts = {"--books": None, "--cache": None, "--only": ""}
    for k in opts:
        if k in args:
            opts[k] = args[args.index(k) + 1]
    if not opts["--books"] or not opts["--cache"]:
        raise SystemExit(__doc__)
    pdfs = read_pdfs(opts["--books"], Path(opts["--cache"]))
    publications = queue.publications()
    rows = queue.read_tsv(queue.QUEUE)
    texts, paths = {}, {}

    def pages_of(pub):
        if pub not in paths:
            paths[pub] = find_book(publications.get(pub, pub), pdfs)
        path = paths[pub]
        if path is None:
            return None
        if path not in texts:
            texts[path] = [
                (norm(p), compact(p)) for p in path.read_text(encoding="utf-8", errors="replace").split("\f")
            ]
        return texts[path]

    sources_of_row = {}
    for i, row in enumerate(rows):
        sources_of_row[i] = row_sources(row)
    # The offset between a book's printed pages and its PDF pages: the most common difference over the
    # rows whose printed name sits on one or two pages.
    votes = {}
    for i, row in enumerate(rows):
        printed = norm(row["printed"])
        if len(printed) < 10:
            continue
        for pub, page in sources_of_row[i]:
            pages = pages_of(pub)
            if pages is None or not page.isdigit():
                continue
            hits = [n for n, p in enumerate(pages) if printed in p[0]]
            if 1 <= len(hits) <= 2:
                for n in hits:
                    votes.setdefault(pub, Counter())[(n + 1) - int(page)] += 1
    offsets = {pub: c.most_common(1)[0][0] for pub, c in votes.items()}
    if "--offsets" in args:
        for pub, off in sorted(offsets.items()):
            print(f"offset {pub}: {off}")
    counts = Counter()
    for i, row in enumerate(rows):
        if opts["--only"] and not row["id"].startswith(opts["--only"]):
            continue
        printed = norm(row["printed"])
        printed_compact = compact(row["printed"])
        verdict, chosen = "nobook", None
        for pub, page in sources_of_row[i]:
            pages = pages_of(pub)
            if pages is None:
                continue
            verdict = "none" if verdict == "nobook" else verdict
            hits = [
                n for n, p in enumerate(pages)
                if printed in p[0] or (len(printed_compact) >= 14 and printed_compact in p[1])
            ]
            if not hits and page.isdigit() and pub in offsets:
                want = tokens(row["printed"])
                centre = int(page) + offsets[pub] - 1
                near_text = " ".join(p[1] for p in pages[max(0, centre - 1): centre + 2])
                if want and all(compact(w) in near_text for w in want):
                    verdict, chosen = "words", (pub, page)
                    break
            if not hits:
                continue
            near = page.isdigit() and pub in offsets and any(abs((n + 1) - offsets[pub] - int(page)) <= 1 for n in hits)
            if near:
                verdict, chosen = "page", (pub, page)
                break
            verdict = "book"
        if chosen:
            row["book"] = publications.get(chosen[0], chosen[0])
            row["page"] = chosen[1]
            row["page_reason"] = ""
        row["print"] = verdict
        counts[verdict] += 1
        if verdict not in ("page", "words"):
            print(f"{verdict}: {row['id']} trade {row['trade']}: {row['printed']}")
    class_counts = Counter()
    groups = None
    for i, row in enumerate(rows):
        if opts["--only"] and not row["id"].startswith(opts["--only"]):
            continue
        row["class_hit"] = row["class_book"] = row["class_page"] = ""
        if row["disposition"] != "resolved" or not row["power"] or not row["decision"].startswith("named-part"):
            continue
        data, relations = queue.entry_info(row["id"])
        if not relations:
            if groups is None:
                groups = tomllib.loads((queue.ROOT / "option-groups.toml").read_text(encoding="utf-8"))["groups"]
            relations = groups.get(data.get("fields", {}).get("group", ""), {}).get("classes", [])
        verdict = "nobook"
        for class_id in relations:
            cdata, _ = queue.entry_info(class_id)
            csources = cdata.get("sources") or []
            if not csources:
                continue
            c = csources[0]
            pages = pages_of(c["publication"])
            if pages is None:
                continue
            verdict = "none"
            if c["publication"] not in offsets or not str(c.get("page", "")).isdigit():
                verdict = "book"
                continue
            offset = offsets[c["publication"]]
            start = int(c["page"]) + offset - 1
            term = compact(row["power"])
            hit = next((n for n in range(max(0, start - 1), min(len(pages), start + 16)) if term in pages[n][1]), None)
            if hit is not None:
                verdict = "hit"
                row["class_book"] = publications.get(c["publication"], c["publication"])
                row["class_page"] = str((hit + 1) - offset)
                break
        row["class_hit"] = verdict
        class_counts[verdict] += 1
    print("class sections:", dict(class_counts))
    queue.write_queue(rows)
    print(dict(counts))


if __name__ == "__main__":
    main()
