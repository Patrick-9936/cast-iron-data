#!/usr/bin/env python3
"""Check the rows of the trades review queue against print (phynics/cast-iron#452).

For each row, the script looks for the printed trade name in the text of the book that the entry
cites, on the printed page that the entry cites (a page either side counts: an archetype spans
pages). It prints one line per row that it cannot find, and writes the verdict into the `print`
column of `trade-review-452.tsv`:

  page   the name is on the cited page or next to it
  words  the words of the name are all on the cited page or next to it (a line break, a column or a
         marker in the text splits the name)
  book   the name is in the book, but not near the cited page
  none   the name is not in the book (a spelling or extraction difference; read the page)
  nobook no copy of the book was found

`class_print` is the same check for the named part of a feature (`power`): is it in the class's own
section of the book that the class entry cites (the 16 pages from the class's page)?

It reads PDFs from the directory that `--books` names (searched recursively, matched to a
publication by the words of its title) and extracts them with `pdftotext` into `--cache`. The
directory, the file names and the extracted text stay on the machine that runs it: the queue
records only the book title, the page and the verdict. Never commit the cache.

  python3 -I scripts/trade-review-452-print.py --books DIR --cache DIR [--only ID-PREFIX]
"""
import csv
import re
from collections import Counter
import subprocess
import sys
import tomllib
import unicodedata
from pathlib import Path

ROOT = Path(".")
QUEUE = ROOT / "scripts/trade-review-452.tsv"


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
    return set(re.findall(r"[a-z0-9]+", text.lower().replace("'", "").replace("\u2019", "")))


def read_pdfs(books, cache):
    cache.mkdir(parents=True, exist_ok=True)
    index = cache / "index.tsv"
    seen = {}
    if index.exists():
        for line in index.read_text(encoding="utf-8").splitlines():
            n, name = line.split("\t", 1)
            seen[name] = n
    files = sorted(Path(books).rglob("*.pdf"))
    out = []
    for f in files:
        if f.name not in seen:
            n = str(len(seen) + 1)
            subprocess.run(["pdftotext", str(f), str(cache / f"{n}.txt")], check=False)
            seen[f.name] = n
            with open(index, "a", encoding="utf-8") as h:
                h.write(f"{n}\t{f.name}\n")
        out.append((f.name, cache / f"{seen[f.name]}.txt"))
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
    return best if score >= 0.99 - 0.01 * 3 else None


def main():
    args = sys.argv[1:]
    opts = {"--books": None, "--cache": None, "--only": ""}
    for k in opts:
        if k in args:
            opts[k] = args[args.index(k) + 1]
    if not opts["--books"] or not opts["--cache"]:
        raise SystemExit(__doc__)
    pdfs = read_pdfs(opts["--books"], Path(opts["--cache"]))
    publications = {
        p["id"]: p["title"]
        for p in tomllib.loads((ROOT / "publications.toml").read_text(encoding="utf-8"))["publication"]
    }
    with open(QUEUE, newline="", encoding="utf-8") as h:
        rows = list(csv.DictReader(h, delimiter="\t", quoting=csv.QUOTE_NONE))
    texts, paths = {}, {}

    def pages_of(pub):
        if pub not in paths:
            paths[pub] = find_book(publications.get(pub, pub), pdfs)
        path = paths[pub]
        if path is None:
            return None
        if path not in texts:
            texts[path] = [(norm(p), compact(p)) for p in path.read_text(encoding="utf-8", errors="replace").split("\f")]
        return texts[path]

    work = []
    for row in rows:
        front = (ROOT / "entries" / (row["id"][4:] + ".md")).read_text(encoding="utf-8").split("+++\n", 2)[1]
        data = tomllib.loads(front)
        sources = data.get("sources") or [{"publication": i} for i in data.get("source_ids", [])]
        work.append((row, sources))
    # The offset between a book's printed pages and its PDF pages: the most common difference
    # over the rows whose printed name sits on one or two pages.
    votes = {}
    for row, sources in work:
        printed = norm(row["printed"])
        if len(printed) < 10:
            continue
        for s in sources:
            pages = pages_of(s["publication"])
            if pages is None or not str(s.get("page", "")).isdigit():
                continue
            hits = [i for i, p in enumerate(pages) if printed in p[0]]
            if 1 <= len(hits) <= 2:
                for i in hits:
                    votes.setdefault(s["publication"], Counter())[(i + 1) - int(s["page"])] += 1
    offsets = {pub: c.most_common(1)[0][0] for pub, c in votes.items()}
    counts = Counter()
    for row, sources in work:
        if opts["--only"] and not row["id"].startswith(opts["--only"]):
            continue
        printed = norm(row["printed"])
        printed_compact = compact(row["printed"])
        verdict = "nobook"
        chosen = None
        for s in sources:
            pages = pages_of(s["publication"])
            if pages is None:
                continue
            verdict = "none" if verdict == "nobook" else verdict
            hits = [
                i for i, p in enumerate(pages) if printed in p[0] or (len(printed_compact) >= 14 and printed_compact in p[1])
            ]
            page = s.get("page", "")
            if not hits and page.isdigit() and s["publication"] in offsets:
                # The words of the name all sit on the cited page or next to it.
                want = tokens(row["printed"])
                centre = int(page) + offsets[s["publication"]] - 1
                near_text = " ".join(p[1] for p in pages[max(0, centre - 1): centre + 2])
                if want and all(compact(w) in near_text for w in want):
                    verdict, chosen = "words", s
                    break
            if not hits:
                continue
            near = page.isdigit() and s["publication"] in offsets and any(
                abs((i + 1) - offsets[s["publication"]] - int(page)) <= 1 for i in hits
            )
            if near:
                verdict, chosen = "page", s
                break
            verdict = "book"
        if chosen:  # (also for `words`)
            row["book"] = publications.get(chosen["publication"], chosen["publication"])
            row["page"] = str(chosen["page"])
        row["print"] = verdict
        counts[verdict] += 1
        if verdict not in ("page", "words"):
            print(f"{verdict}: {row['id']} trade {row['trade']}: {row['printed']}")
    # The named part of a feature (a bardic performance, a deed, a school power) should be in the class's
    # own section of the book that the class entry cites: look for it in the 16 pages from the class's page.
    class_counts = Counter()
    for row, sources in work:
        row["class_print"] = ""
        if not row["power"] or not row["decision"].startswith("named-part"):
            continue
        front = (ROOT / "entries" / (row["id"][4:] + ".md")).read_text(encoding="utf-8").split("+++\n", 2)[1]
        relations = [r["target"] for r in tomllib.loads(front).get("relations", []) if r["kind"] == "archetype"]
        if row["id"].startswith("ref/spirit/"):
            relations = ["ref/class/medium"]
        verdict = "nobook"
        for class_id in relations:
            cfront = (ROOT / "entries" / (class_id[4:] + ".md")).read_text(encoding="utf-8").split("+++\n", 2)[1]
            csources = tomllib.loads(cfront).get("sources") or []
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
            start = int(c["page"]) + offsets[c["publication"]] - 1
            term = compact(row["power"])
            if any(term in p[1] for p in pages[max(0, start - 1): start + 16]):
                verdict = "page"
                break
        row["class_print"] = verdict
        class_counts[verdict] += 1
    print("class sections:", dict(class_counts))
    sys.path.insert(0, str(Path(__file__).parent))
    import importlib.util

    spec = importlib.util.spec_from_file_location("queue", Path(__file__).parent / "trade-review-452.py")
    queue = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(queue)
    queue.write_queue(rows)
    print(dict(counts))


if __name__ == "__main__":
    main()
