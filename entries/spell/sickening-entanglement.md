+++
id = "ref/spell/sickening-entanglement"
kind = "spell"
title = "Sickening Entanglement"
aon = "SpellDisplay.aspx?ItemName=Sickening%20Entanglement"
source_ids = ["core-rulebook", "advanced-class-guide", "legacy-of-the-first-world"]
provenance = [
  { dataset = "pathfinder-data-1-e", record = "sickening_entanglement", path = "json/spells4.json" },
]
relations = [
  { kind = "variant", target = "ref/spell/entangle" },
]
[[sources]]
publication = "advanced-class-guide"
page = "192"
[[sources]]
publication = "legacy-of-the-first-world"
page = "17"

[fields]
kind = "spell"
school = "transmutation"
descriptors = ["poison"]
levels = [
  { class = "Druid", level = 2 },
  { class = "Hunter", level = 2 },
  { class = "Ranger", level = 2 },
  { class = "Shaman", level = 2 },
]
casting_time = "1 standard action"
components = "V, S, DF"
range = "long (400 ft. + 40 ft./level)"
effects = [
  { label = "Area", value = "plants in a 40-ft.-radius spread" },
]
duration = "1 minute/level (D)"
saving_throw = "Reflex partial and Fortitude negates (see text)"
spell_resistance = "no"
+++

::: statblock
title = "Spell statistics"
School: transmutation
Level: 2: Druid, Hunter, Ranger, Shaman
Casting time: 1 standard action
Components: V, S, DF
Range: long (400 ft. + 40 ft./level)
Duration: 1 minute/level (D)
Saving throw: Reflex partial and Fortitude negates (see text)
Spell resistance: no
Area: plants in a 40-ft.-radius spread
Descriptors: poison
:::

### Sickening Entanglement

This spell functions as [entangle](ref/spell/entangle), except the plants are coated with an
irritating sap that creates a painful, itching rash on creatures that touch them. Any creature that
enters the area or ends its turn there must succeed at a Fortitude save or be sickened as long as it
remains in the area and for 1d4 rounds afterward. This is a poison effect.
