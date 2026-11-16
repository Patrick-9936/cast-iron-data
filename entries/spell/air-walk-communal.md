+++
id = "ref/spell/air-walk-communal"
kind = "spell"
title = "Communal Air Walk"
aon = "SpellDisplay.aspx?ItemName=Air%20Walk%2C%20Communal"
source_ids = ["core-rulebook", "ultimate-combat"]
provenance = [
  { dataset = "pathfinder-data-1-e", record = "air_walk_communal", path = "json/spells.json" },
]
relations = [
  { kind = "variant", target = "ref/spell/air-walk" },
]
[[sources]]
publication = "ultimate-combat"
page = "222"

[fields]
kind = "spell"
school = "transmutation"
descriptors = ["air"]
levels = [
  { class = "Alchemist", level = 5 },
  { class = "Cleric", level = 5 },
  { class = "Druid", level = 5 },
  { class = "Hunter", level = 5 },
  { class = "Investigator", level = 5 },
  { class = "Occultist", level = 5 },
  { class = "Oracle", level = 5 },
  { class = "Warpriest", level = 5 },
]
casting_time = "1 standard action"
components = "V, S, DF"
range = "touch"
effects = [
  { label = "Targets", value = "creatures touched" },
]
duration = "10 minutes/level"
saving_throw = "none"
spell_resistance = "yes"
+++

::: statblock
title = "Spell statistics"
School: transmutation
Level: 5: Alchemist, Cleric, Druid, Hunter, Investigator, Occultist, Oracle, Warpriest
Casting time: 1 standard action
Components: V, S, DF
Range: touch
Duration: 10 minutes/level
Saving throw: none
Spell resistance: yes
Targets: creatures touched
Descriptors: air
:::

### Communal Air Walk

This spell functions like [air walk](ref/spell/air-walk), except divide the duration in 10-minute
intervals among the creatures touched.
