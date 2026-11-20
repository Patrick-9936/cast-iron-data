+++
id = "ref/spell/share-language-communal"
kind = "spell"
title = "Communal Share Language"
aon = "SpellDisplay.aspx?ItemName=Share%20Language%2C%20Communal"
source_ids = ["ultimate-combat"]
provenance = [
  { dataset = "pathfinder-data-1-e", record = "share_language_communal", path = "json/spells9.json" },
]
relations = [
  { kind = "variant", target = "ref/spell/share-language" },
]
[[sources]]
publication = "ultimate-combat"
page = "243"

[fields]
kind = "spell"
school = "divination"
levels = [
  { class = "Arcanist", level = 3 },
  { class = "Bard", level = 2 },
  { class = "Cleric", level = 3 },
  { class = "Druid", level = 3 },
  { class = "Hunter", level = 3 },
  { class = "Mesmerist", level = 2 },
  { class = "Occultist", level = 3 },
  { class = "Oracle", level = 3 },
  { class = "Psychic", level = 2 },
  { class = "Skald", level = 2 },
  { class = "Sorcerer", level = 3 },
  { class = "Warpriest", level = 3 },
  { class = "Wizard", level = 3 },
]
casting_time = "1 standard action"
components = "V, S, M (a page from a dictionary)"
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
School: divination
Level: 2: Bard, Mesmerist, Psychic, Skald\
3: Arcanist, Cleric, Druid, Hunter, Occultist, Oracle, Sorcerer, Warpriest, Wizard
Casting time: 1 standard action
Components: V, S, M (a page from a dictionary)
Range: touch
Duration: 24 hours
Saving throw: Will negates (harmless)
Spell resistance: yes (harmless)
Targets: creatures touched
:::

### Communal Share Language

This spell functions like [share language](ref/spell/share-language), except you divide the duration
in 1-hour increments among the creatures touched.
