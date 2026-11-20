+++
id = "ref/spell/resist-energy-communal"
kind = "spell"
title = "Communal Resist Energy"
aon = "SpellDisplay.aspx?ItemName=Resist%20Energy%2C%20Communal"
source_ids = ["ultimate-combat"]
provenance = [
  { dataset = "pathfinder-data-1-e", record = "resist_energy_communal", path = "json/spells8.json" },
]
relations = [
  { kind = "variant", target = "ref/spell/resist-energy" },
]
[[sources]]
publication = "ultimate-combat"
page = "242"

[fields]
kind = "spell"
school = "abjuration"
levels = [
  { class = "Alchemist", level = 3 },
  { class = "Arcanist", level = 3 },
  { class = "Cleric", level = 3 },
  { class = "Druid", level = 3 },
  { class = "Hunter", level = 3 },
  { class = "Inquisitor", level = 3 },
  { class = "Investigator", level = 3 },
  { class = "Occultist", level = 3 },
  { class = "Oracle", level = 3 },
  { class = "Paladin", level = 3 },
  { class = "Psychic", level = 3 },
  { class = "Ranger", level = 3 },
  { class = "Sorcerer", level = 3 },
  { class = "Summoner", level = 3 },
  { class = "Unchained Summoner", level = 3 },
  { class = "Warpriest", level = 3 },
  { class = "Wizard", level = 3 },
]
casting_time = "1 standard action"
components = "V, S, DF"
range = "touch"
effects = [
  { label = "Targets", value = "creatures touched" },
]
duration = "10 minutes/level"
saving_throw = "Fortitude negates (harmless)"
spell_resistance = "yes (harmless)"
+++

::: statblock
title = "Spell statistics"
School: abjuration
Level: 3: Alchemist, Arcanist, Cleric, Druid, Hunter, Inquisitor, Investigator, Occultist, Oracle, Paladin, Psychic, Ranger, Sorcerer, Summoner, Unchained Summoner, Warpriest, Wizard
Casting time: 1 standard action
Components: V, S, DF
Range: touch
Duration: 10 minutes/level
Saving throw: Fortitude negates (harmless)
Spell resistance: yes (harmless)
Targets: creatures touched
:::

### Communal Resist Energy

This spell functions like [resist energy](ref/spell/resist-energy), except you divide the duration
in 10-minute intervals among the creatures touched.
