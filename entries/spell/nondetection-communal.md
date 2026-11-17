+++
id = "ref/spell/nondetection-communal"
kind = "spell"
title = "Communal Nondetection"
aon = "SpellDisplay.aspx?ItemName=Nondetection%2C%20Communal"
source_ids = ["core-rulebook", "ultimate-combat"]
provenance = [
  { dataset = "pathfinder-data-1-e", record = "nondetection_communal", path = "json/spells7.json" },
]
relations = [
  { kind = "variant", target = "ref/spell/nondetection" },
]
[[sources]]
publication = "ultimate-combat"
page = "238"

[fields]
kind = "spell"
school = "abjuration"
levels = [
  { class = "Antipaladin", level = 4 },
  { class = "Arcanist", level = 4 },
  { class = "Mesmerist", level = 4 },
  { class = "Occultist", level = 4 },
  { class = "Psychic", level = 4 },
  { class = "Sorcerer", level = 4 },
  { class = "Wizard", level = 4 },
]
casting_time = "1 standard action"
components = "V, S, M (diamond dust worth 25 gp per target)"
range = "touch"
effects = [
  { label = "Targets", value = "creatures or objects touched" },
]
duration = "1 hour/level"
saving_throw = "Will negates (harmless) (object)"
spell_resistance = "yes (harmless) (object)"
+++

::: statblock
title = "Spell statistics"
School: abjuration
Level: 4: Antipaladin, Arcanist, Mesmerist, Occultist, Psychic, Sorcerer, Wizard
Casting time: 1 standard action
Components: V, S, M (diamond dust worth 25 gp per target)
Range: touch
Duration: 1 hour/level
Saving throw: Will negates (harmless) (object)
Spell resistance: yes (harmless) (object)
Targets: creatures or objects touched
:::

### Communal Nondetection

This spell functions like [nondetection](ref/spell/nondetection), except you divide the duration in
1-hour increments among the creatures or objects touched.
