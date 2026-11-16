+++
id = "ref/spell/spider-climb-communal"
kind = "spell"
title = "Communal Spider Climb"
aon = "SpellDisplay.aspx?ItemName=Spider%20Climb%2C%20Communal"
source_ids = ["core-rulebook", "ultimate-combat"]
provenance = [
  { dataset = "pathfinder-data-1-e", record = "spider_climb_communal", path = "json/spells9.json" },
]
relations = [
  { kind = "variant", target = "ref/spell/spider-climb" },
]
[[sources]]
publication = "ultimate-combat"
page = "245"

[fields]
kind = "spell"
school = "transmutation"
levels = [
  { class = "Alchemist", level = 3 },
  { class = "Arcanist", level = 3 },
  { class = "Druid", level = 3 },
  { class = "Hunter", level = 3 },
  { class = "Investigator", level = 3 },
  { class = "Occultist", level = 3 },
  { class = "Psychic", level = 3 },
  { class = "Red Mantis Assassin", level = 3 },
  { class = "Sorcerer", level = 3 },
  { class = "Summoner", level = 3 },
  { class = "Unchained Summoner", level = 3 },
  { class = "Wizard", level = 3 },
]
casting_time = "1 standard action"
components = "V, S, M (a live spider)"
range = "touch"
effects = [
  { label = "Target", value = "creatures touched" },
]
duration = "10 minutes/level"
saving_throw = "Will negates (harmless)"
spell_resistance = "yes (harmless)"
+++

::: statblock
title = "Spell statistics"
School: transmutation
Level: 3: Alchemist, Arcanist, Druid, Hunter, Investigator, Occultist, Psychic, Red Mantis Assassin, Sorcerer, Summoner, Unchained Summoner, Wizard
Casting time: 1 standard action
Components: V, S, M (a live spider)
Range: touch
Duration: 10 minutes/level
Saving throw: Will negates (harmless)
Spell resistance: yes (harmless)
Target: creatures touched
:::

### Communal Spider Climb

This spell functions like [spider climb](ref/spell/spider-climb), except you divide the duration in
10-minute intervals among the creatures touched.
