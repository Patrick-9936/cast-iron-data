# The trades review queue (phynics/cast-iron#452)

`trade-review-452-baseline.tsv` is the queue as `cast-iron-corpus migrate-trades` wrote it: one row for each
trade that the migration could not resolve, and one row for each `**Replaces:**` or `**Alters:**` line that no
trade can hold (`trade` is 0; `subsection` names the variant section that prints the line). It is preserved
and never edited. `trade-review-452.tsv` has the same rows with a decision for each, and `check` fails when
the two disagree (a row missing, added or repeated). Every row is closed: `resolved` (the trade names a
feature) or `exception` (it stays unresolved on purpose). A trade without a feature is never treated as
compatible by a filter, so an exception costs a missing link, never a wrong one.

Tools (run from the corpus root): `trade-review-452.py` (`fill`, `apply`, `normalize`, `check`, `stats`),
`trade-review-452-print.py` (needs the book PDFs as an argument; commits only titles, pages and verdicts) and
`trade-review-452-decisions.tsv` (the decisions: first matching line wins).

## Convention: steps are grant levels

`levels` identifies a progression step by the base-class grant levels, read from the class table of the base
class: `Armor training 2` is `levels = [7]`, `Trap sense +3` is `[9]`, `Judgment 1/day` is `[1]`,
`Spirit power (lesser)` is `[1]`, and a list of steps is the levels of its steps (`Weapon training 1 and 3` is
`[5, 13]`). `power` names a stable component of a feature (a bardic performance, a deed, a school power, a
proficiency) only when the level alone is not enough, and the name is the same text in every entry. A step is
never a `power`: the migration wrote `power = "2"` for `Armor training 2` and `power = "+4"` for
`Poison resistance +4`, and `normalize` rewrites those to levels (the rewrite of each such trade is in
`trade-adjustments-452.tsv`, with its class table row). The overlap rule of `corpus-check` compares `power`
exactly first, so a step written as a power would never meet the same step written as a level.

Columns of the queue: `id`, `kind`, `trade` (1-based position in the entry's `trades`), `op`, `printed`,
`reason` (why the migration left it), `candidates`, `unclaimed_old_anchors`, `subsection`; then the decision:
`disposition`, `decision` (`code: note`), `feature`, `class`, `levels`, `power`; then the evidence: `book` and
`page` (where the item is printed; for a variant row, the source of the subsection that prints the line),
`page_reason` (why there is no page), `print` (what the print check found), `evidence` and `evidence_note` (what settles
the row: see below), and for a named part of a feature
`class_hit`, `class_book`, `class_page` (a search hit for the name in the class's own pages: see below).

## Codes of `resolved` rows

| Code | Meaning |
|---|---|
| `step-list`, `grant-level` | A step or a list of steps of one feature; `levels` are the grant levels of the class table. |
| `instance-level` | The nth instance of a feature (`2nd favored enemy`); `levels` is the level at which the class gains it. |
| `level-of-feature` | The name states class levels (`The additional use of wild shape at 6th level`); they are `levels`. |
| `named-part` | A named part of a feature (a bardic performance, a deed, a bloodline power, a spirit power); `power` names it. |
| `named-part-list` | Several named parts of one feature; the whole feature is named. |
| `same-feature`, `name-variant` | The printed name is the feature, or a variant spelling of it. |
| `editor-note` | The parenthesis is the book's note; the whole feature is named. |
| `proficiency`, `spellcasting` | The class's proficiencies, or its spells. |

## Codes of `exception` rows

| Code | Meaning |
|---|---|
| `base-is-not-a-class` | An animal companion or familiar archetype: no class entry is its base. |
| `variant-only` | The line is printed in a variant section (subdomain, mutated bloodline), below the normal part of the entry. |
| `repeated-item` | The book prints the item again for another ability; an earlier trade of the entry names the feature. |
| `levels-overlap`, `overlaps-earlier-claim` | An earlier trade of the same key names the feature at a shared level and power (the one-claim rule of `corpus-check`). |
| `conditional-replacement` | The archetype replaces the feature only if a choice is made; format 2 has no condition field. |
| `class-statistic` | Class skills, alignment, skill ranks, saves: printed in the class statistics, not as a feature. |
| `single-slot-loss` | The archetype gives up one slot of the Spells feature (one 4th-level spell slot); the whole feature would overstate it and no component names a slot. |
| `composite` | The printed item names several features at once; a trade holds one feature. |
| `free-text-part` | The item describes a part of a feature in words, with no stable name to compare by exact text. |
| `no-class-heading` | The class entry has no heading or text for it (the code of conduct, an ability of the phantom). |
| `not-a-class-feature` | A racial trait, or a feature of another class (the unchained rogue). |
| `name-not-a-feature` | The printed name is not a feature name in print. |
| `print-contradicts-class` | Print lists a grant level that the base class contradicts (Possessed Oracle's 1st-level mystery bonus spell); no link is written. |
| `print-ambiguity` | Print and the class entry disagree about which feature or level (Guild Agent's Improved Evasion at 8th level); no link is written. |

`print` is `page` (the printed name is on the cited page or next to it), `words` (all its words are), `book`
(in the book, not near the cited page), `none`, or `nobook` (no copy of the book was available). It is a
search hit on the text of the cited page, not a reading of the trade's scope.

`class_hit` is `hit` when the name of a named part (`power`) occurs in the class's pages of the book that the
class entry cites (the class's page and the 16 pages after it); `class_book` and `class_page` are then the book
and the printed page of the first hit. A class option finds its class through its option group. A hit shows
that the book prints the name in the class's section; it does not show that the feature grants it.

## Evidence

`print` is a search hit, not a reading. `evidence` says what settles each closed row:

| `evidence` | Meaning |
|---|---|
| `print` | The search found the printed name on the cited page or next to it. |
| `manual` | A reader checked the book page. `trade-evidence-452.tsv` records the book, the printed page and what the page says; `fill` copies them. |
| `corpus` | No search hit and no reading. The entry's own line and the class table settle it, and `evidence_note` says why print did not: no copy of the book, or the book is available but nobody read the page. |

A count of rows "resolved by print" is the count of `resolved` rows with `evidence` `print` or `manual`; the rest are
resolved from the corpus.

Rows that a reader adjusted by hand (and the step values that `normalize` rewrote) are in `trade-adjustments-452.tsv`;
the hand adjustments are written in `trade-adjustments-manual-452.tsv`, each with its reason.
