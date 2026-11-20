+++
id = "ref/spell/mind-blank-communal"
kind = "spell"
title = "Communal Mind Blank"
aon = "SpellDisplay.aspx?ItemName=Mind%20Blank%2C%20Communal"
source_ids = ["ultimate-combat"]
provenance = [
  { dataset = "pathfinder-data-1-e", record = "mind_blank_communal", path = "json/spells14.json" },
]
relations = [
  { kind = "variant", target = "ref/spell/mind-blank" },
]
[[sources]]
publication = "ultimate-combat"
page = "236"

[fields]
kind = "spell"
school = "abjuration"
levels = [
  { class = "Arcanist", level = 9 },
  { class = "Psychic", level = 8 },
  { class = "Sorcerer", level = 9 },
  { class = "Witch", level = 9 },
  { class = "Wizard", level = 9 },
]
casting_time = "1 standard action"
components = "V, S"
range = "close (25 ft. + 5 ft./2 levels)"
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
Level: 8: Psychic\
9: Arcanist, Sorcerer, Witch, Wizard
Casting time: 1 standard action
Components: V, S
Range: close (25 ft. + 5 ft./2 levels)
Duration: 24 hours
Saving throw: Will negates (harmless)
Spell resistance: yes (harmless)
Targets: creatures touched
:::

### Communal Mind Blank

This spell functions like [mind blank](ref/spell/mind-blank), except you divide the duration in
1-hour increments among the creatures touched.
