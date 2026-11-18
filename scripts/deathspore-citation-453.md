# Deathspore Toxin citation review

Scope: `ref/affliction/zombie/deathspore-toxin`, app issue
[phynics/cast-iron#453](https://github.com/phynics/cast-iron/issues/453).
Reviewed 2026-11-18 against data main `32a4d2f0fb6d65a69804d15c16a089182443ec93`.

## Outcome

The correction is already present. Data #99 removed Classic Horrors Revisited membership
and its p. 25 citation in commit `5f5601bca`. The app's v0.1.26 pin at
`a4b3ef61952098358e62274be1d0e17da99ea2c8` includes it. The latest #453 comment still
calls this citation open; that comment does not describe the pinned entry.

Retain Horror Realms p. 33 as the toxin's printed source. No replacement page in
Classic Horrors Revisited is supported. There is a valid retained source, so continued
inclusion needs no new owner decision for this correction. This review changes no entry,
ID, parent, provenance, membership or book placement. In particular, Bestiary membership
is outside this correction and is preserved without claiming that it prints the toxin.

## Printed evidence

| Book and printed page | Observation and significance |
| --- | --- |
| Classic Horrors Revisited p. 25 | Ghost material, including Ghostly Corruptions. This is not the toxin or its deathspore zombie carrier. |
| Classic Horrors Revisited pp. 54-55 | Faces of Death prints other skeleton and zombie variants. Cursed Zombie has Zombie Curse; Gasburst Zombie uses poisonous gas. Neither is the injury poison printed as Deathspore Toxin. A shared zombie family does not establish this affliction's publication. |
| Classic Horrors Revisited pp. 56-57 | Walking-dead examples and the Gillamoor Plague Zombie. Its affliction is Zombie Rot, a disease with different timing and effects, not Deathspore Toxin. |
| Horror Realms p. 33 | Zombies of the Yellow Mire prints Deathspore Zombie and its Deathspore Toxin stat line. All six corpus stat lines match: injury poison, Fortitude DC 14, once per round for six rounds, initial Constitution drain 1, secondary Dexterity damage 1d3, cure two saves. |

The cited pages were read directly and their printed page numbers checked. This conclusion
uses the positive matching printing and the distinct surrounding rules, not title-search
absence alone. No book text or artwork is included here.

## Upstream and prior audit

The corpus provenance points to `zombie|affliction:deathspore-toxin` in
[`json/monster_template4.json`](https://github.com/jasontankapps/pathfinder-data-1-e/blob/08ea71f24375908d0190c822fd1fd080797667a9/json/monster_template4.json)
at the `legal.toml` dataset pin. The `zombie` host lists Horror Realms, Bestiary and
Classic Horrors Revisited together. Its Zombies of the Yellow Mire section explicitly
switches to Horror Realms p. 33 before the toxin directive. Only afterward does Faces of
Death switch to Classic Horrors Revisited p. 25. The combined host's publications are
not independent print evidence for every extracted child. The latter page marker is
itself wrong for Faces of Death, which starts at Classic Horrors Revisited p. 54.

Data #92 left the extra toxin case untouched. Data #98 also explicitly left it open.
Data #99 subsequently removed it and retained the invalidated citation in
`scripts/membership-citation-audit-461.tsv`; its matching queue row is in
`scripts/membership-queue-461.tsv`. Those historical rows remain unchanged.

## Reproduce the artifact check

Compile this corpus with the app compiler, using its `sources/published-ids.txt` and
`sources/published-books.txt` guards, then run:

```sh
python3 scripts/check-deathspore-453.py --content /path/to/compiled/content
```

The check reads the entry, compiled entry shards and book Contents. It requires the
Horror Realms p. 33 citation, rejects Classic Horrors Revisited membership, citation and
Contents placement, and preserves the existing Bestiary and Horror Realms placements.
It does not establish print evidence automatically. The table above records that review.

This is separate from #483. No Deadeye Devotee files or data #100 marker corrections are
changed. Tagging, the combined app pin and final issue closure belong to the parent task.
