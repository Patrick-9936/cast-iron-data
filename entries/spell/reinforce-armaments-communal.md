+++
id = "ref/spell/reinforce-armaments-communal"
kind = "spell"
title = "Communal Reinforce Armaments"
aon = "SpellDisplay.aspx?ItemName=Reinforce%20Armaments%2C%20Communal"
source_ids = ["ultimate-combat"]
provenance = [
  { dataset = "pathfinder-data-1-e", record = "reinforce_armaments_communal", path = "json/spells8.json" },
]
relations = [
  { kind = "variant", target = "ref/spell/reinforce-armaments" },
]
[[sources]]
publication = "ultimate-combat"
page = "241"

[fields]
kind = "spell"
school = "transmutation"
levels = [
  { class = "Arcanist", level = 2 },
  { class = "Cleric", level = 2 },
  { class = "Magus", level = 2 },
  { class = "Occultist", level = 2 },
  { class = "Oracle", level = 2 },
  { class = "Red Mantis Assassin", level = 2 },
  { class = "Sorcerer", level = 2 },
  { class = "Warpriest", level = 2 },
  { class = "Witch", level = 2 },
  { class = "Wizard", level = 2 },
]
casting_time = "1 standard action"
components = "V, S, M/DF (a metal pin)"
range = "touch"
effects = [
  { label = "Targets", value = "armor suits or weapons touched" },
]
duration = "10 minutes/level"
saving_throw = "Will negates (harmless) (object)"
spell_resistance = "yes (harmless) (object)"
+++

::: statblock
title = "Spell statistics"
School: transmutation
Level: 2: Arcanist, Cleric, Magus, Occultist, Oracle, Red Mantis Assassin, Sorcerer, Warpriest, Witch, Wizard
Casting time: 1 standard action
Components: V, S, M/DF (a metal pin)
Range: touch
Duration: 10 minutes/level
Saving throw: Will negates (harmless) (object)
Spell resistance: yes (harmless) (object)
Targets: armor suits or weapons touched
:::

### Communal Reinforce Armaments

This spell functions like [reinforce armaments](ref/spell/reinforce-armaments), except you divide
the duration in 10-minute intervals among the objects touched.
