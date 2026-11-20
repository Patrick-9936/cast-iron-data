# Licenses

This repository combines tooling and structure, game content, and upstream notices. No single
license covers all of it. Each part is covered by the license listed here.

| Part | License | Where |
|---|---|---|
| The corpus format, the contributor kit, the examples, the workflow, and the repository structure | MIT | [LICENSES/MIT.txt](LICENSES/MIT.txt) |
| Open Game Content in the entries (`entries/`, `books.toml`, `publications.toml`, `aliases.toml`, and the other corpus files to the extent they carry Open Game Content) | Open Game License v1.0a | [LICENSES/OGL-1.0a.md](LICENSES/OGL-1.0a.md) |
| Section 15 copyright notices | OGL 1.0a Section 15 | [LICENSES/OGL-1.0a.md](LICENSES/OGL-1.0a.md) and `legal.toml` |
| Paizo Product Identity (names, deities, places, characters, and similar setting content) | Paizo's Community Use Policy | [LICENSES/community-use.md](LICENSES/community-use.md) |

Copyright (c) 2026 Atakan Dulker holds the copyright in the MIT-licensed parts.

## This project is unofficial

This project is not published, endorsed, or specifically approved by Paizo Inc. It makes no claim
of official status and no claim of compatibility with any Paizo product. It does not use the
Pathfinder logo or any other Paizo artwork or trade dress. "Pathfinder" and other Paizo names
appear only as descriptive references, under the Community Use Policy.

## MIT: format, tooling, examples, structure

The MIT license covers the corpus format, the contributor kit (`README.md` in this repository, the
`examples/` directory, and the `.github/` workflow and pull request template), and the layout of the
repository. It does not cover the rules content. The bare license text is in
[LICENSES/MIT.txt](LICENSES/MIT.txt).

The tool that reads and checks the corpus, `cast-iron-corpus`, is part of
[Cast Iron](https://github.com/phynics/cast-iron) and is MIT-licensed there. This repository does
not contain it.

## Open Game License v1.0a: Open Game Content

The rules text in the entries is Open Game Content, used under the Open Game License, version 1.0a.
Section 10 of the license requires a copy of it with every copy of the Open Game Content, so
[LICENSES/OGL-1.0a.md](LICENSES/OGL-1.0a.md) carries the full license text, the Product Identity
declaration, and the complete Section 15 copyright notice list for every publication in the corpus.
It also lists the publications whose Section 15 notice is still pending (see below).

The OGL covers only Open Game Content. Product Identity is excluded from its grant.

If you add or change text, the new text must be Open Game Content or your own contribution under
the same terms. If you contribute original Open Game Content, add its Section 15 notice to
`legal.toml` in the same pull request. Do not copy artwork.

## Paizo Community Use Policy: Product Identity

Some entries carry Paizo Product Identity: proper names, deities, characters, places, and
descriptive text about them. Those uses rest on Paizo's Community Use Policy
(<https://paizo.com/licenses/communityuse>), not on the OGL. The policy requires its notice, which is in
[LICENSES/community-use.md](LICENSES/community-use.md). Every entry refers to it through
`license_refs` (the default in `corpus.toml` is `["ogl-1.0a", "legal#community-use"]`).

The policy allows free, non-commercial use only. This repository and everything built from it must
stay free to use and access.

## Section 15 notice pending

These publications have no Section 15 notice in any source the project reviewed. Their records are
kept as assumed Open Game Content under the Open Game License, and the project tracks their notice
coverage as open work (<https://github.com/phynics/cast-iron/issues/34>):

- Bestiary 6
- Faiths of Purity
- Goblins of Golarion
- Horror Realms
- Inner Sea Taverns
- Kingmaker Player's Guide
- Magic of Thassilon
- Serpent's Skull Player's Guide

## Where the content came from

The first version of the corpus was compiled once from two public datasets and then frozen as plain
text, so that fixes are ordinary edits to this repository. The datasets are pinned in `legal.toml`:

- [PSRD-Data](https://github.com/devonjones/PSRD-Data), commit
  `76ea4784604145ba3dea40eb56f83bb904759467`. The repository has no license file and no license
  field. Its content derives from Paizo's Pathfinder Reference Document, which Paizo published as
  Open Game Content under the OGL 1.0a. The corpus uses it under that grant and under Paizo's
  Community Use Policy.
- [Pathfinder Data 1e](https://github.com/jasontankapps/pathfinder-data-1-e), commit
  `08ea71f24375908d0190c822fd1fd080797667a9`. Its `json/` directory is Open Game Content under the
  OGL 1.0a (its `OPENGAMECONTENT.md` carries the license text, the Section 15 credits, and Paizo's
  Product Identity exclusion). The application content in that repository is copyright 2024 Jason
  Tamez under GPL-3.0-or-later. Its code, its renderer, and its other application content were not
  copied. The one part that may count as application content is the dataset's editor's notes (see
  below). Its Pathfinder Second Edition material is licensed under the ORC License and is out of
  scope: no ORC-licensed record or notice is in this corpus.

Section 15 notices come from those datasets' own notice lists and from a reviewed export of the
d20pfsrd.com Section 15 statements. d20pfsrd.com distributes its Pathfinder First Edition Open
Game Content under OGL 1.0a. The research behind these decisions is in the Cast Iron repository:
`docs/research/licensing-audit.md` and `docs/research/pf-data-licensing.md`.

Excluded and rejected material is listed in `exclusions.toml`. Records of Pathfinder comics, which
have no usable notice, are excluded.

### Editor's notes from Pathfinder Data 1e

Pathfinder Data 1e adds notes to its records (footnotes and similar notes). The dataset does not
mark each note as Open Game Content or as application content, and its notices support either
reading. A note stays in this corpus only when Archives of Nethys (AoN) or the Paizo Pathfinder
Reference Document (PRD) carries the same text. The corpus removed or converted the notes that
neither carries (cast-iron-data pull requests #113 and #115).

The notes that stay are, by kind:

- Notes that a Paizo book prints, such as the "Bonus feat." legends in stat blocks, notes under
  tables, and the markers on spell lists, in the dataset's wording or a close paraphrase of the
  printed text. This is most of them.
- A small number of cross-reference pointers, short compiled lists, and similar notes that AoN or
  the PRD carries.

About 770 footnote blocks in about 530 entries remained when this note was written. The count falls
if the review of the remaining candidates (cast-iron-data issue #117) removes more notes. The basis
below applies to whichever notes stay.

The basis is the game text that AoN or the PRD carries, not the dataset's editorial work:

- Text that the PRD carries is Paizo's Open Game Content, published under the Open Game License
  1.0a. The Section 15 notices of the book that printed it apply, and they are in
  [LICENSES/OGL-1.0a.md](LICENSES/OGL-1.0a.md).
- Text that AoN carries is Paizo's printed rules text as AoN presents it, mostly condensed printed
  sentences. The corpus treats it as it treats the rest of the entry: Open Game Content under the
  Open Game License 1.0a, with the Section 15 notice of the book and of the dataset ("Pf Data 1e
  Copyright 2025, Jason Tamez"), as `legal.toml` records. Notes that AoN's own editors wrote
  (Nethys Notes) are not Paizo text, and the corpus claims no other license for them.

Paizo's Community Use Policy covers Paizo's own material only. It does not cover a third party's
prose, so it is not the basis for any of these notes. This is a statement of the project's basis,
not a legal clearance. A rights holder who disagrees can ask for a note's removal through the
contact address below.

## Contact

Questions about licensing, and requests to correct or remove an entry, go to
<https://github.com/phynics/cast-iron-data/issues>.
