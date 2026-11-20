# The trades review queue (phynics/cast-iron#452)

`trade-review-452.tsv` has one row for each trade that the format 2 migration could not resolve, and for each
`**Replaces:**` or `**Alters:**` line that no trade can hold (`trade` is 0). Every row is closed: `resolved` (the
trade names a feature) or `exception` (it stays unresolved on purpose). The tools are `trade-review-452.py`
(`fill`, `apply`, `check`, `stats`) and `trade-review-452-print.py`; the decisions are
`trade-review-452-decisions.tsv`. A trade without a feature is never treated as compatible by a filter, so an
exception costs a missing link, never a wrong one.

Columns: `id`, `kind`, `trade` (1-based position in the entry's `trades`), `op`, `printed`, `reason` (why the
migration left it), `candidates`, `unclaimed_old_anchors`, then the decision: `disposition`, `decision`
(`code: note`), `feature`, `class`, `levels`, `power`, then the evidence: `book` and `page` (where the item is
printed), `print` and `class_print` (what the print check found).

## Codes of `resolved` rows

| Code | Meaning |
|---|---|
| `step-list` | A list of steps of one feature (`Armor training 2, 3, and 4`); `levels` are the class levels of those steps, from the class table. |
| `instance-level` | The nth instance of a feature (`2nd favored enemy`); `levels` is the level at which the class gains it. |
| `level-of-feature` | The name states class levels (`The additional use of wild shape at 6th level`); they are `levels`. |
| `named-part` | A named part of a feature (a bardic performance, a deed, a bloodline power, a spirit power); `power` names it. |
| `named-part-list` | Several named parts of one feature; the whole feature is named. |
| `same-feature` / `name-variant` | The printed name is the feature, or a variant spelling of it. |
| `editor-note` | The parenthesis is the book's note (`(but see text)`); the whole feature is named. |
| `proficiency`, `spellcasting` | The class's proficiencies, or its spells (casting and spell list). |

## Codes of `exception` rows

| Code | Meaning |
|---|---|
| `base-is-not-a-class` | An animal companion or familiar archetype: no class entry is its base. |
| `variant-only` | The line is printed in a variant section (subdomain, mutated bloodline), below the normal part of the entry. |
| `repeated-item` | The book prints the item again for another ability; an earlier trade of the entry names the feature. |
| `levels-overlap`, `overlaps-earlier-claim` | An earlier trade of the same key names the feature at a shared level and power (the one-claim rule of `corpus-check`). |
| `class-statistic` | Class skills, alignment, skill ranks, saves: printed in the class statistics, not as a feature. |
| `composite` | The printed item names several features at once; a trade holds one feature. |
| `free-text-part` | The item describes a part of a feature in words, with no stable name to compare by exact text. |
| `no-class-heading` | The class entry has no heading or text for it (the code of conduct, an ability of the phantom). |
| `not-a-class-feature` | A racial trait, or a feature of another class (the unchained rogue). |
| `name-not-a-feature` | The printed name is not a feature name in print. |

`print` is `page` (the printed name is on the cited page or next to it), `words` (all its words are), `book`
(in the book, not near the cited page), `none`, or `nobook` (no copy of the book was available). `class_print` is
`page` when a named part is in the class's own section of the book.
