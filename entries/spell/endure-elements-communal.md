+++
id = "ref/spell/endure-elements-communal"
kind = "spell"
title = "Communal Endure Elements"
aon = "SpellDisplay.aspx?ItemName=Endure%20Elements%2C%20Communal"
source_ids = ["ultimate-combat"]
provenance = [
  { dataset = "pathfinder-data-1-e", record = "endure_elements_communal", path = "json/spells4.json" },
]
relations = [
  { kind = "variant", target = "ref/spell/endure-elements" },
]
[[sources]]
publication = "ultimate-combat"
page = "228"

[fields]
kind = "spell"
school = "abjuration"
levels = [
  { class = "Alchemist", level = 3 },
  { class = "Arcanist", level = 2 },
  { class = "Cleric", level = 2 },
  { class = "Druid", level = 2 },
  { class = "Hunter", level = 2 },
  { class = "Investigator", level = 3 },
  { class = "Oracle", level = 2 },
  { class = "Paladin", level = 2 },
  { class = "Psychic", level = 2 },
  { class = "Ranger", level = 2 },
  { class = "Sorcerer", level = 2 },
  { class = "Warpriest", level = 2 },
  { class = "Wizard", level = 2 },
]
casting_time = "1 standard action"
components = "V, S"
range = "touch"
effects = [
  { label = "Targets", value = "creatures touched" },
]
duration = "24 hours"
saving_throw = "Will negates (harmless)"
spell_resistance = "yes (harmless)"
+++

::: statblock
title = "Spell statistics"
School: abjuration
Level: 2: Arcanist, Cleric, Druid, Hunter, Oracle, Paladin, Psychic, Ranger, Sorcerer, Warpriest, Wizard\
3: Alchemist, Investigator
Casting time: 1 standard action
Components: V, S
Range: touch
Duration: 24 hours
Saving throw: Will negates (harmless)
Spell resistance: yes (harmless)
Targets: creatures touched
:::

### Communal Endure Elements

This spell functions like [endure elements](ref/spell/endure-elements), except you divide the
duration in 1-hour increments among the creatures touched.
