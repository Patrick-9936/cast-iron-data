+++
id = "ref/spell/spell-immunity-communal"
kind = "spell"
title = "Communal Spell Immunity"
aon = "SpellDisplay.aspx?ItemName=Spell%20Immunity%2C%20Communal"
source_ids = ["core-rulebook", "ultimate-combat"]
provenance = [
  { dataset = "pathfinder-data-1-e", record = "spell_immunity_communal", path = "json/spells9.json" },
]
relations = [
  { kind = "variant", target = "ref/spell/spell-immunity" },
]
[[sources]]
publication = "ultimate-combat"
page = "244"

[fields]
kind = "spell"
school = "abjuration"
levels = [
  { class = "Cleric", level = 5 },
  { class = "Inquisitor", level = 5 },
  { class = "Occultist", level = 5 },
  { class = "Oracle", level = 5 },
  { class = "Psychic", level = 5 },
  { class = "Warpriest", level = 5 },
]
casting_time = "1 standard action"
components = "V, S, DF"
range = "touch"
effects = [
  { label = "Targets", value = "creatures touched" },
]
duration = "10 minutes/level"
saving_throw = "Will negates (harmless)"
spell_resistance = "yes (harmless)"
+++

::: statblock
title = "Spell statistics"
School: abjuration
Level: 5: Cleric, Inquisitor, Occultist, Oracle, Psychic, Warpriest
Casting time: 1 standard action
Components: V, S, DF
Range: touch
Duration: 10 minutes/level
Saving throw: Will negates (harmless)
Spell resistance: yes (harmless)
Targets: creatures touched
:::

### Communal Spell Immunity

This spell functions like [spell immunity](ref/spell/spell-immunity), except you divide the duration
in 10-minute intervals among the creatures touched.
