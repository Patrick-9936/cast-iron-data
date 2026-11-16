+++
id = "ref/spell/water-walk-communal"
kind = "spell"
title = "Communal Water Walk"
aon = "SpellDisplay.aspx?ItemName=Water%20Walk%2C%20Communal"
source_ids = ["core-rulebook", "ultimate-combat"]
provenance = [
  { dataset = "pathfinder-data-1-e", record = "water_walk_communal", path = "json/spells11.json" },
]
relations = [
  { kind = "variant", target = "ref/spell/water-walk" },
]
[[sources]]
publication = "ultimate-combat"
page = "249"

[fields]
kind = "spell"
school = "transmutation"
descriptors = ["water"]
levels = [
  { class = "Cleric", level = 2 },
  { class = "Hunter", level = 2 },
  { class = "Oracle", level = 2 },
  { class = "Psychic", level = 4 },
  { class = "Ranger", level = 2 },
  { class = "Warpriest", level = 2 },
]
casting_time = "1 standard action"
components = "V, S, DF"
range = "touch"
effects = [
  { label = "Targets", value = "creatures touched" },
]
duration = "10 minutes/level (D)"
saving_throw = "Will negates (harmless)"
spell_resistance = "yes (harmless)"
+++

::: statblock
title = "Spell statistics"
School: transmutation
Level: 2: Cleric, Hunter, Oracle, Ranger, Warpriest\
4: Psychic
Casting time: 1 standard action
Components: V, S, DF
Range: touch
Duration: 10 minutes/level (D)
Saving throw: Will negates (harmless)
Spell resistance: yes (harmless)
Targets: creatures touched
Descriptors: water
:::

### Communal Water Walk

This spell functions like [water walk](ref/spell/water-walk), except you divide the duration in
10-minute intervals among the creatures touched.
