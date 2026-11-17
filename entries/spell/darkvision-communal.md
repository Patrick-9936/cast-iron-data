+++
id = "ref/spell/darkvision-communal"
kind = "spell"
title = "Communal Darkvision"
aon = "SpellDisplay.aspx?ItemName=Darkvision%2C%20Communal"
source_ids = ["core-rulebook", "ultimate-combat"]
provenance = [
  { dataset = "pathfinder-data-1-e", record = "darkvision_communal", path = "json/spells3.json" },
]
relations = [
  { kind = "variant", target = "ref/spell/darkvision" },
]
[[sources]]
publication = "ultimate-combat"
page = "226"

[fields]
kind = "spell"
school = "transmutation"
levels = [
  { class = "Alchemist", level = 3 },
  { class = "Antipaladin", level = 3 },
  { class = "Arcanist", level = 3 },
  { class = "Hunter", level = 4 },
  { class = "Investigator", level = 3 },
  { class = "Occultist", level = 3 },
  { class = "Psychic", level = 3 },
  { class = "Ranger", level = 4 },
  { class = "Red Mantis Assassin", level = 3 },
  { class = "Sorcerer", level = 3 },
  { class = "Wizard", level = 3 },
]
casting_time = "1 standard action"
components = "V, S, M (either a pinch of dried carrot or an agate)"
range = "touch"
effects = [
  { label = "Targets", value = "creatures touched" },
]
duration = "1 hour/level"
saving_throw = "Will negates (harmless)"
spell_resistance = "yes (harmless)"
+++

::: statblock
title = "Spell statistics"
School: transmutation
Level: 3: Alchemist, Antipaladin, Arcanist, Investigator, Occultist, Psychic, Red Mantis Assassin, Sorcerer, Wizard\
4: Hunter, Ranger
Casting time: 1 standard action
Components: V, S, M (either a pinch of dried carrot or an agate)
Range: touch
Duration: 1 hour/level
Saving throw: Will negates (harmless)
Spell resistance: yes (harmless)
Targets: creatures touched
:::

### Communal Darkvision

This spell functions like [darkvision](ref/spell/darkvision), except you may divide the duration in
1-hour intervals among the creatures touched.
