#!/usr/bin/env python3
"""Test scripts/membership-apply.py on small synthetic corpora (no real data, no book text).

    python3 scripts/test-membership-apply.py

Cases: a `[[sources]]` row the audit file releases is dropped with the membership; the same
entry with a body `**Source:**` line as well is refused and left byte for byte unchanged; a
body line alone is refused; a row without an audit row is refused; a released row with a
wrong page is refused. Each refusal must happen before anything is written.
"""
import csv
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
APPLY = HERE / "membership-apply.py"
QUEUE_HEAD = ["book", "entry", "kind", "title", "member", "n_books", "tag", "status", "cited", "cite", "hits",
              "found", "via", "family", "parent_has_book", "gate", "proposed_primary", "proposed_status",
              "verdict", "print_page", "evidence"]
AUDIT_HEAD = ["entry", "book", "class", "cited_page", "print_page", "family", "related_cite", "edge",
              "mention_pages", "mention_kind", "read", "evidence", "invalidated"]
PUBS = '''[[publication]]
id = "book-a"
title = "Alpha Book"

[[publication]]
id = "book-b"
title = "Beta Book"

[[publication]]
id = "book-c"
title = "Gamma Book"
'''


def entry(sources: str, body: str) -> str:
    return ('+++\nid = "ref/spell/test-spell"\nkind = "spell"\ntitle = "Test Spell"\n'
            'source_ids = ["book-a", "book-b", "book-c"]\n' + sources + '\n[fields]\nkind = "spell"\n+++\n' + body)


ROW = '[[sources]]\npublication = "book-b"\npage = "12"\n'


class ApplyTest(unittest.TestCase):
    def run_apply(self, text: str, audit_page: str | None = "12", audit_class: str = "wrong-credit"):
        tmp = Path(tempfile.mkdtemp())
        (tmp / "entries/spell").mkdir(parents=True)
        (tmp / "publications.toml").write_text(PUBS, encoding="utf-8")
        (tmp / "books.toml").write_text('[[books]]\nsource = "book-a"\n', encoding="utf-8")
        path = tmp / "entries/spell/test-spell.md"
        path.write_text(text, encoding="utf-8")
        queue = tmp / "queue.tsv"
        row = dict.fromkeys(QUEUE_HEAD, "")
        row.update(book="book-b", entry="ref/spell/test-spell", kind="spell", title="Test Spell", tag="family-leak",
                   verdict="remove", print_page="3", evidence="wrong-credit-invalidated")
        with open(queue, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=QUEUE_HEAD, delimiter="\t", lineterminator="\n")
            w.writeheader()
            w.writerow(row)
        audit = tmp / "audit.tsv"
        with open(audit, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=AUDIT_HEAD, delimiter="\t", lineterminator="\n")
            w.writeheader()
            if audit_page is not None:
                a = dict.fromkeys(AUDIT_HEAD, "")
                a.update(entry="ref/spell/test-spell", book="book-b", cited_page=audit_page, print_page="none",
                         read="read p. 12", evidence="not printed", invalidated="Beta Book p. 12")
                a["class"] = audit_class
                w.writerow(a)
        r = subprocess.run([sys.executable, str(APPLY), str(tmp), "--queue", str(queue), "--audit", str(audit)],
                           capture_output=True, text=True)
        return r, path

    def test_row_released_by_audit_is_dropped(self):
        r, path = self.run_apply(entry(ROW, "Text.\n"))
        self.assertEqual(r.returncode, 0, r.stderr)
        out = path.read_text()
        self.assertIn('source_ids = ["book-a", "book-c"]', out)
        self.assertNotIn("[[sources]]", out)

    def test_body_line_beside_a_released_row_is_refused(self):
        text = entry(ROW, "Text.\n\n**Source:** Beta Book pg. 12\n")
        r, path = self.run_apply(text)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("body source line", r.stderr)
        self.assertEqual(path.read_text(), text)

    def test_plural_body_line_beside_a_row_is_refused(self):
        text = entry(ROW, "Text.\n\n**Sources:** Beta Book pg. 12, Alpha Book pg. 3\n")
        r, path = self.run_apply(text)
        self.assertNotEqual(r.returncode, 0)
        self.assertEqual(path.read_text(), text)

    def test_body_line_alone_is_refused(self):
        text = entry("", "Text.\n\n**source:** Beta Book/12\n")
        r, path = self.run_apply(text, audit_page=None)
        self.assertNotEqual(r.returncode, 0)
        self.assertEqual(path.read_text(), text)

    def test_body_line_for_another_book_does_not_block(self):
        r, path = self.run_apply(entry(ROW, "Text.\n\n**Source:** Alpha Book pg. 3\n"))
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_row_without_audit_is_refused(self):
        text = entry(ROW, "Text.\n")
        r, path = self.run_apply(text, audit_page=None)
        self.assertNotEqual(r.returncode, 0)
        self.assertEqual(path.read_text(), text)

    def test_audit_with_other_page_is_refused(self):
        text = entry(ROW, "Text.\n")
        r, path = self.run_apply(text, audit_page="13")
        self.assertNotEqual(r.returncode, 0)
        self.assertEqual(path.read_text(), text)


if __name__ == "__main__":
    unittest.main()
