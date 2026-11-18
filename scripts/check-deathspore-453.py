#!/usr/bin/env python3
"""Check the retained #453 correction against corpus and compiled library artifacts."""
import argparse
import json
from pathlib import Path
import tomllib

ENTRY = 'ref/affliction/zombie/deathspore-toxin'
MEMBERS = ['bestiary', 'horror-realms']
CITATIONS = [{'publication': 'horror-realms', 'page': '33'}]


def require(condition, message):
    if not condition:
        raise SystemExit(message)


def placements(nodes):
    for node in nodes:
        if node.get('entry') == ENTRY:
            yield node
        yield from placements(node.get('children', []))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--content', type=Path, required=True,
                        help='compiler output directory containing manifest.json')
    args = parser.parse_args()
    corpus = Path(__file__).resolve().parents[1]
    text = (corpus / 'entries/affliction/zombie/deathspore-toxin.md').read_text()
    authored = tomllib.loads(text.split('+++')[1])
    require(authored['id'] == ENTRY, 'permanent ID changed')
    require(authored['source_ids'] == MEMBERS, 'corpus membership changed')
    require(authored['sources'] == CITATIONS, 'corpus citation changed')
    require(authored['parent'] == 'ref/template/zombie', 'parent changed')
    require(authored['provenance'] == [{
        'dataset': 'pathfinder-data-1-e',
        'record': 'zombie|affliction:deathspore-toxin',
        'path': 'json/monster_template4.json',
    }], 'provenance changed')
    catalogs = list(args.content.rglob('catalog.json'))
    require(len(catalogs) == 1, 'expected one compiled library; use a fresh output directory')
    library = catalogs[0].parent
    stubs = [e for e in json.loads(catalogs[0].read_text())['entries'] if e['id'] == ENTRY]
    require(len(stubs) == 1, 'catalog ID must occur exactly once')
    stub = stubs[0]
    require(stub.get('books', [stub['source']]) == MEMBERS, 'catalog membership changed')
    entries = [e for e in json.loads((library / stub['shard']).read_text())
               if e['id'] == ENTRY]
    require(len(entries) == 1, 'compiled ID must occur exactly once')
    entry = entries[0]
    require(entry['source_ids'] == MEMBERS, 'compiled membership changed')
    require(entry['sources'] == CITATIONS, 'compiled citation changed')
    require(entry['parent'] == authored['parent'], 'compiled parent changed')
    books = json.loads((library / 'books.json').read_text())['books']
    counts = {b['source']: len(list(placements(b['chapters']))) for b in books}
    require(counts.get('classic-horrors-revisited') == 0,
            'false Classic Horrors Revisited Contents placement returned')
    for book in MEMBERS:
        require(counts.get(book) == 1, f'{book} Contents placement changed')
    print('PASS: permanent ID and parent; retained memberships and Horror Realms p. 33; '
          'no Classic Horrors Revisited citation or Contents placement')


if __name__ == '__main__':
    main()
