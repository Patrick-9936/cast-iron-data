+++
id = "ref/spell/rend-body-4"
kind = "spell"
title = "Rend Body IV"
aon = "SpellDisplay.aspx?ItemName=Rend%20Body%20IV"
source_ids = ["psychic-anthology"]
provenance = [
  { dataset = "pathfinder-data-1-e", record = "rend_body_4", path = "json/spells8.json" },
]
relations = [
  { kind = "variant", target = "ref/spell/rend-body-3" },
]
[[sources]]
publication = "psychic-anthology"
page = "10"

[fields]
kind = "spell"
school = "evocation"
levels = [
  { class = "Psychic", level = 8 },
]
casting_time = "1 full-round action"
components = "S"
range = "close (25 ft. + 5 ft./2 levels)"
effects = [
  { label = "Target", value = "one creature" },
]
duration = "instantaneous"
saving_throw = "none"
spell_resistance = "no"
+++

::: statblock
title = "Spell statistics"
School: evocation
Level: 8: Psychic
Casting time: 1 full-round action
Components: S
Range: close (25 ft. + 5 ft./2 levels)
Duration: instantaneous
Saving throw: none
Spell resistance: no
Target: one creature
:::

### Rend Body IV

This functions as per [rend body III](ref/spell/rend-body-3), but the target takes 1d8 points of
damage per caster level (maximum 20d8), and one of the target's limbs is ripped off if the amount of
damage dealt is greater than 1/4 of its maximum hit point total. This spell can be undercast.
