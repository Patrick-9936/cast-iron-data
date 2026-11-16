+++
id = "ref/spell/flare-burst"
kind = "spell"
title = "Flare Burst"
aon = "SpellDisplay.aspx?ItemName=Flare%20Burst"
source_ids = ["core-rulebook", "advanced-players-guide"]
provenance = [
  { dataset = "pathfinder-data-1-e", record = "flare_burst", path = "json/spells4.json" },
]
relations = [
  { kind = "variant", target = "ref/spell/flare" },
]
[[sources]]
publication = "advanced-players-guide"
page = "223"

[fields]
kind = "spell"
school = "evocation"
descriptors = ["light"]
levels = [
  { class = "Arcanist", level = 1 },
  { class = "Bloodrager", level = 1 },
  { class = "Bard", level = 1 },
  { class = "Druid", level = 1 },
  { class = "Hunter", level = 1 },
  { class = "Magus", level = 1 },
  { class = "Psychic", level = 1 },
  { class = "Skald", level = 1 },
  { class = "Sorcerer", level = 1 },
  { class = "Wizard", level = 1 },
]
casting_time = "1 standard action"
components = "V"
range = "close (25 ft. + 5 ft./2 levels)"
effects = [
  { label = "Effect", value = "10-ft.-radius burst of light" },
]
duration = "instantaneous"
saving_throw = "Fortitude negates"
spell_resistance = "yes"
+++

::: statblock
title = "Spell statistics"
School: evocation
Level: 1: Arcanist, Bloodrager, Bard, Druid, Hunter, Magus, Psychic, Skald, Sorcerer, Wizard
Casting time: 1 standard action
Components: V
Range: close (25 ft. + 5 ft./2 levels)
Duration: instantaneous
Saving throw: Fortitude negates
Spell resistance: yes
Effect: 10-ft.-radius burst of light
Descriptors: light
:::

### Flare Burst

This spell functions as [flare](ref/spell/flare), except it affects all creatures in a
10-foot-radius burst from the target point.
