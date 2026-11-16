+++
id = "ref/spell/ant-haul-communal"
kind = "spell"
title = "Communal Ant Haul"
aon = "SpellDisplay.aspx?ItemName=Ant%20Haul%2C%20Communal"
source_ids = ["advanced-players-guide", "ultimate-combat"]
provenance = [
  { dataset = "pathfinder-data-1-e", record = "ant_haul_communal", path = "json/spells.json" },
]
relations = [
  { kind = "variant", target = "ref/spell/ant-haul" },
]
[[sources]]
publication = "ultimate-combat"
page = "223"

[fields]
kind = "spell"
school = "transmutation"
levels = [
  { class = "Alchemist", level = 2 },
  { class = "Arcanist", level = 2 },
  { class = "Cleric", level = 2 },
  { class = "Druid", level = 2 },
  { class = "Hunter", level = 2 },
  { class = "Investigator", level = 2 },
  { class = "Occultist", level = 2 },
  { class = "Oracle", level = 2 },
  { class = "Psychic", level = 2 },
  { class = "Ranger", level = 2 },
  { class = "Red Mantis Assassin", level = 2 },
  { class = "Sorcerer", level = 2 },
  { class = "Summoner", level = 2 },
  { class = "Unchained Summoner", level = 2 },
  { class = "Warpriest", level = 2 },
  { class = "Wizard", level = 2 },
]
casting_time = "1 standard action"
components = "V, S, M/DF (a small pulley)"
range = "touch"
effects = [
  { label = "Targets", value = "creatures touched" },
]
duration = "2 hours/level"
saving_throw = "Fortitude negates (harmless)"
spell_resistance = "yes (harmless)"
+++

::: statblock
title = "Spell statistics"
School: transmutation
Level: 2: Alchemist, Arcanist, Cleric, Druid, Hunter, Investigator, Occultist, Oracle, Psychic, Ranger, Red Mantis Assassin, Sorcerer, Summoner, Unchained Summoner, Warpriest, Wizard
Casting time: 1 standard action
Components: V, S, M/DF (a small pulley)
Range: touch
Duration: 2 hours/level
Saving throw: Fortitude negates (harmless)
Spell resistance: yes (harmless)
Targets: creatures touched
:::

### Communal Ant Haul

This spell functions like [ant haul](ref/spell/ant-haul), except you may divide the duration in
2-hour intervals among the creatures touched.
