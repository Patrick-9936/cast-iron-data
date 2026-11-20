#!/usr/bin/env python3
"""The review queue of the trades migration (phynics/cast-iron#452).

`trade-review-452.tsv` holds one row per trade that the migration could not resolve, plus one row per
`**Replaces:**` or `**Alters:**` line that no trade can hold. This script turns the decisions of
`trade-review-452-decisions.tsv` into the rows and into the entries:

  fill   [--print FILE]  copy each decision onto the queue rows it covers (first matching decision wins)
  apply                  write the `feature`, `class`, `levels` and `power` of every resolved row into its entry
  check  [--allow-open]  fail unless every row is closed and the entries agree with the rows
  stats                  count the rows per disposition and reason

Run it from the root of the corpus: `python3 -I scripts/trade-review-452.py <command>`. `fill` and
`apply` are idempotent. `apply` rewrites only the trades that the queue lists (they had no `feature` when the migration
ran), so it never changes a link that the migration wrote.

Dispositions of a row:

  open       not decided yet; `check` fails while any row is open
  resolved   print settles the feature: `feature` (and `class`, `levels`, `power`) go into the trade
  exception  the trade stays unresolved on purpose; `decision` names the documented reason

The decisions file has one decision per line: `scope` (an entry id, `class <ref/class/x>`,
`reason <reason>`, `prefix <id prefix>`, or `kind <kind>`), `printed` (the printed name in lower case, `*` for any, or
`~regex` that must match the whole name), then `disposition`, `code`, `feature`, `class`, `levels`
(comma separated), `power` (`=printed` copies the printed name), and `levels` may be `ordinals` (read the ordinals of the printed name) or `steps:<table>`. A `~regex` printed pattern may use its groups as `\\1` in `feature`, `power` and `note`, `note`.
"""
import csv
import re
import sys
import tomllib
from collections import Counter
from pathlib import Path

ROOT = Path(".")
QUEUE = ROOT / "scripts/trade-review-452.tsv"
DECISIONS = ROOT / "scripts/trade-review-452-decisions.tsv"
COLUMNS = [
    "id", "kind", "trade", "op", "printed", "reason", "candidates", "unclaimed_old_anchors",
    "disposition", "decision", "feature", "class", "levels", "power", "book", "page", "print", "class_print",
]


def read_tsv(path):
    with open(path, newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle, delimiter="\t", quoting=csv.QUOTE_NONE))


def write_queue(rows):
    with open(QUEUE, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle, COLUMNS, delimiter="\t", lineterminator="\n", quoting=csv.QUOTE_NONE, escapechar="\\"
        )
        writer.writeheader()
        for row in rows:
            writer.writerow({column: row.get(column, "") for column in COLUMNS})


def entry_path(entry_id):
    return ROOT / "entries" / (entry_id.removeprefix("ref/") + ".md")


def split_entry(text):
    head, front, body = text.split("+++\n", 2)
    return front, body


_publications = None


def publication_title(publication):
    global _publications
    if _publications is None:
        data = tomllib.loads((ROOT / "publications.toml").read_text(encoding="utf-8"))
        rows = data.get("publication") or data.get("publications") or []
        _publications = {row["id"]: row.get("title", row["id"]) for row in rows}
    return _publications.get(publication, publication)


def entry_info(entry_id):
    front, _ = split_entry(entry_path(entry_id).read_text(encoding="utf-8"))
    data = tomllib.loads(front)
    relations = [r["target"] for r in data.get("relations", []) if r["kind"] == "archetype"]
    return data, relations


def base_classes(entry_id, data, relations):
    if data["kind"] == "archetype":
        return relations
    return []


def match_printed(pattern, printed):
    """The match object (or True) when the pattern covers the printed name, else None."""
    printed = " ".join(printed.lower().split())
    if pattern == "*":
        return True
    if pattern.startswith("~"):
        return re.fullmatch(pattern[1:], printed, re.I)
    return True if " ".join(pattern.lower().split()) == printed else None


ORDINAL = re.compile(r"\b(\d{1,2})(?:st|nd|rd|th)\b|\bfirst\b", re.I)


def ordinals(printed):
    """The levels that the ordinals of a printed name state (`2nd-, 8th-, and 16th-level` is 2, 8, 16)."""
    found = {1 if m.group(0).lower() == "first" else int(m.group(1)) for m in ORDINAL.finditer(printed)}
    if not found or any(not 1 <= n <= 20 for n in found):
        raise SystemExit(f"no usable ordinal level in {printed!r}")
    return ",".join(str(n) for n in sorted(found))


_anchors = {}


def class_anchors(class_id):
    """The heading anchors of a class entry: the features a trade may name."""
    if class_id not in _anchors:
        text = entry_path(class_id).read_text(encoding="utf-8")
        _anchors[class_id] = set(re.findall(r"^#{3,6} .*? \{#([^}]+)\}$", text, re.M))
    return _anchors[class_id]


def decision_for(row, decisions, info):
    data, relations = info
    for d in decisions:
        scope = d["scope"]
        if scope.startswith("class "):
            if scope[6:] not in relations:
                continue
        elif scope.startswith("reason "):
            if scope[7:] != row["reason"]:
                continue
        elif scope.startswith("prefix "):
            if not row["id"].startswith(scope[7:]):
                continue
        elif scope.startswith("kind "):
            if scope[5:] != row["kind"]:
                continue
        elif scope != row["id"]:
            continue
        m = match_printed(d["printed"], row["printed"])
        if m and d["disposition"] == "resolved" and relations and d["feature"]:
            # A decision names a feature that every base class of the entry must hold; a generic
            # decision that one class cannot take leaves the row for a later, more specific one.
            if not all(d["feature"] in class_anchors(c) for c in relations):
                continue
        if m:
            if m is True:
                return d
            # A pattern may use its groups in the other fields: `\\1` in `feature`, `power`, `note`.
            return {k: (m.expand(v) if k in ("feature", "power", "note") and "\\" in v else v) for k, v in d.items()}
    return None


def source_of(data, print_pages):
    sources = data.get("sources") or []
    if print_pages:
        pass
    if sources:
        s = sources[0]
        return publication_title(s["publication"]), str(s.get("page", ""))
    ids = data.get("source_ids") or []
    return (publication_title(ids[0]) if ids else ""), ""


# Step lists: the class level at which each step of a feature is gained, from the class table of the
# class entry (and print). A decision whose `levels` is `steps:<table>` reads the step numbers out of
# the printed name (`Weapon training 1, 3, and 4`, `Gun training 1-4`, `Trap sense +1 and +4`) and
# takes the levels from the table.
STEP_TABLES = {
    "armor-training": {1: 3, 2: 7, 3: 11, 4: 15},  # fighter: Armor training +1 at 3rd, +2 at 7th, +3 at 11th, +4 at 15th
    "weapon-training": {1: 5, 2: 9, 3: 13, 4: 17},  # fighter: Weapon training +1 at 5th ... +4 at 17th
    "trap-sense": {n: 3 * n for n in range(1, 7)},  # rogue: trap sense +1 at 3rd, then every three levels, +6 at 18th
    "gun-training": {1: 5, 2: 9, 3: 13, 4: 17},  # gunslinger: gun training 1 at 5th ... 4 at 17th
    "outside-contact": {1: 8, 2: 12, 3: 16, 4: 20},  # occultist: outside contact 1 at 8th ... 4 at 20th
    "poison-resistance": {2: 2, 4: 5, 6: 8},  # alchemist: poison resistance +2 at 2nd, +4 at 5th, +6 at 8th
}


def step_levels(table, printed):
    text = re.sub(r"^\D*?(?=[+\d])", "", re.sub(r"(\d+)\s*(?:-|through)\s*(\d+)", lambda m: ", ".join(str(n) for n in range(int(m.group(1)), int(m.group(2)) + 1)), printed.lower()), count=1)
    numbers = [int(n) for n in re.findall(r"\d+", text)]
    steps = STEP_TABLES[table]
    return ",".join(str(steps[n]) for n in sorted(set(numbers)))


def claim_of(trade):
    """What a trade claims: (op, feature, class, power, levels) with levels None for every level."""
    op = "replaces" if "replaces" in trade else "alters"
    levels = frozenset(trade["levels"]) if trade.get("levels") else None
    return op, trade["feature"], trade.get("class"), trade.get("power"), levels


def overlap(a, b):
    """The one-claim rule of corpus-check: the same key, feature, class and power at a shared level."""
    if a[:4] != b[:4]:
        return False
    return a[4] is None or b[4] is None or bool(a[4] & b[4])


def cmd_fill(args):
    rows = read_tsv(QUEUE)
    decisions = read_tsv(DECISIONS)
    cache = {}
    changed = 0
    for row in rows:
        info = cache.setdefault(row["id"], entry_info(row["id"]))
        d = decision_for(row, decisions, info)
        if d is None:
            continue
        code = d["code"]
        note = d["note"]
        book, page = source_of(info[0], None)
        if row.get("print") in ("page", "words") and row.get("book"):
            book, page = row["book"], row["page"]
        levels = d["levels"]
        if levels == "ordinals":
            levels = ordinals(row["printed"])
        if levels.startswith("steps:"):
            levels = step_levels(levels[6:], row["printed"])
        power = row["printed"] if d["power"] == "=printed" else d["power"]
        new = dict(
            disposition=d["disposition"], decision=code + (": " + note if note else ""), feature=d["feature"],
            **{"class": d["class"]}, levels=levels, power=power, book=book, page=page,
        )
        row["_new"] = new
    # One trade of a key claims a feature at a level and power; a later trade that would claim the same
    # stays unresolved (the rule that migrate-trades follows too).
    by_entry = {}
    for row in rows:
        by_entry.setdefault(row["id"], []).append(row)
    for entry_id, entry_rows in by_entry.items():
        queued = {int(r["trade"]) for r in entry_rows if r["trade"] != "0"}
        trades = cache[entry_id][0].get("fields", {}).get("trades", [])
        claimed = [(i, claim_of(t)) for i, t in enumerate(trades, 1) if "feature" in t and i not in queued]
        for row in sorted(entry_rows, key=lambda r: int(r["trade"])):
            new = row.get("_new")
            if not new or new["disposition"] != "resolved":
                continue
            claim = (
                row["op"], new["feature"], new["class"] or None, new["power"] or None,
                frozenset(int(x) for x in new["levels"].split(",")) if new["levels"] else None,
            )
            clash = next((i for i, c in claimed if overlap(claim, c)), None)
            if clash is not None:
                new.update(
                    disposition="exception", feature="", levels="", power="", **{"class": ""},
                    decision=f"overlaps-earlier-claim: trade {clash} of the same key already names feature {claim[1]} at a shared level and power, and the one-claim rule lets one trade name it (the decision for this item was: {new['decision']})",
                )
            else:
                claimed.append((int(row["trade"]), claim))
    for row in rows:
        new = row.pop("_new", None)
        if new and any(row.get(k, "") != v for k, v in new.items()):
            row.update(new)
            changed += 1
    write_queue(rows)
    print(f"fill: {changed} rows changed, {sum(1 for r in rows if r['disposition'] == 'open')} open")


TRADE_RE = re.compile(r"^  \{ (replaces|alters) = (\"(?:[^\"\\]|\\.)*\")(.*) \},?$")


def trade_lines(front):
    lines = front.split("\n")
    start = next(i for i, l in enumerate(lines) if l == "trades = [")
    end = next(i for i in range(start + 1, len(lines)) if lines[i] == "]")
    return lines, start + 1, end


def render(line, row):
    m = TRADE_RE.match(line)
    op, printed, rest = m.group(1), m.group(2), m.group(3)
    parts = [f"{op} = {printed}", f'feature = "{row["feature"]}"']
    if row["class"]:
        parts.append(f'class = "{row["class"]}"')
    if row["levels"]:
        parts.append("levels = [" + ", ".join(row["levels"].split(",")) + "]")
    if row["power"]:
        parts.append('power = "' + row["power"].replace("\\", "\\\\").replace('"', '\\"') + '"')
    return "  { " + ", ".join(parts) + " },"


def bare(line):
    m = TRADE_RE.match(line)
    return f"  {{ {m.group(1)} = {m.group(2)} }},"


def cmd_apply(args):
    rows = [r for r in read_tsv(QUEUE) if r["disposition"] in ("resolved", "exception") and r["trade"] != "0"]
    by_entry = {}
    for row in rows:
        by_entry.setdefault(row["id"], []).append(row)
    written = 0
    for entry_id, entry_rows in by_entry.items():
        path = entry_path(entry_id)
        text = path.read_text(encoding="utf-8")
        head, front, body = text.split("+++\n", 2)
        lines, first, end = trade_lines(front)
        touched = False
        for row in entry_rows:
            index = first + int(row["trade"]) - 1
            line = lines[index]
            m = TRADE_RE.match(line)
            if not m or m.group(1) != row["op"]:
                raise SystemExit(f"{entry_id}: trade {row['trade']} is not a {row['op']} trade: {line!r}")
            # A queue row was unresolved when the migration ran, so its line may follow the row either way.
            want = render(bare(line), row) if row["disposition"] == "resolved" else bare(line)
            if line != want:
                lines[index] = want
                touched = True
        if touched:
            path.write_text(head + "+++\n" + "\n".join(lines) + "+++\n" + body, encoding="utf-8")
            written += 1
    print(f"apply: {written} entries written")


def cmd_check(args):
    rows = read_tsv(QUEUE)
    problems = []
    for row in rows:
        where = f"{row['id']} trade {row['trade']} ({row['printed']})"
        if row["disposition"] == "open" and "--allow-open" in args:
            continue
        if row["disposition"] not in ("resolved", "exception"):
            problems.append(f"{where}: disposition is {row['disposition']!r}")
            continue
        if not row["decision"] or not row["book"]:
            problems.append(f"{where}: decision or book is empty")
        if row["disposition"] == "resolved" and not row["feature"]:
            problems.append(f"{where}: resolved without a feature")
        if row["disposition"] == "exception" and row["feature"]:
            problems.append(f"{where}: exception with a feature")
    queued = {(r["id"], int(r["trade"])) for r in rows if r["trade"] != "0"}
    cache = {}
    for entry_id in {r["id"] for r in rows}:
        front, _ = split_entry(entry_path(entry_id).read_text(encoding="utf-8"))
        cache[entry_id] = tomllib.loads(front).get("fields", {}).get("trades", [])
    for row in rows:
        if row["trade"] == "0" or row["disposition"] == "open":
            continue
        trades = cache[row["id"]]
        i = int(row["trade"]) - 1
        where = f"{row['id']} trade {row['trade']} ({row['printed']})"
        if i >= len(trades) or trades[i].get(row["op"]) != row["printed"]:
            problems.append(f"{where}: the entry has no such trade")
            continue
        t = trades[i]
        if row["disposition"] == "resolved":
            want = (row["feature"], row["class"] or None, [int(x) for x in row["levels"].split(",")] if row["levels"] else None, row["power"] or None)
            have = (t.get("feature"), t.get("class"), t.get("levels"), t.get("power"))
            if want != have:
                problems.append(f"{where}: the entry holds {have}, the row says {want}")
        elif "feature" in t:
            problems.append(f"{where}: exception, but the entry resolves it to {t['feature']}")
    # Every unresolved trade of the corpus is in the queue.
    missing = 0
    for path in sorted((ROOT / "entries").glob("*/*.md")):
        text = path.read_text(encoding="utf-8")
        if "\ntrades = [" not in text:
            continue
        front, _ = split_entry(text)
        data = tomllib.loads(front)
        for i, t in enumerate(data["fields"]["trades"], 1):
            if "feature" not in t and (data["id"], i) not in queued:
                missing += 1
                problems.append(f"{data['id']} trade {i}: unresolved and not in the queue")
    for p in problems[:50]:
        print("check:", p)
    print(f"check: {len(rows)} rows, {len(problems)} problems, {missing} unresolved trades outside the queue")
    sys.exit(1 if problems else 0)


def cmd_stats(args):
    rows = read_tsv(QUEUE)
    counts = Counter((r["kind"], r["reason"], r["disposition"]) for r in rows)
    for key, n in sorted(counts.items()):
        print(n, *key)
    print(len(rows), "rows;", sum(1 for r in rows if r["disposition"] == "open"), "open")


def main():
    commands = {"fill": cmd_fill, "apply": cmd_apply, "check": cmd_check, "stats": cmd_stats}
    if len(sys.argv) < 2 or sys.argv[1] not in commands:
        raise SystemExit(__doc__)
    commands[sys.argv[1]](sys.argv[2:])


if __name__ == "__main__":
    main()
