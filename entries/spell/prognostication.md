+++
id = "ref/spell/prognostication"
kind = "spell"
title = "Prognostication"
aon = "SpellDisplay.aspx?ItemName=Prognostication"
source_ids = ["ultimate-intrigue"]
provenance = [
  { dataset = "pathfinder-data-1-e", record = "prognostication", path = "json/spells13.json" },
]
relations = [
  { kind = "variant", target = "ref/spell/divination" },
]
[[sources]]
publication = "ultimate-intrigue"
page = "223"

[fields]
kind = "spell"
school = "divination"
levels = [
  { class = "Cleric", level = 6 },
  { class = "Inquisitor", level = 6 },
  { class = "Medium", level = 4 },
  { class = "Oracle", level = 6 },
  { class = "Psychic", level = 6 },
  { class = "Shaman", level = 6 },
  { class = "Spiritualist", level = 6 },
  { class = "Warpriest", level = 6 },
  { class = "Witch", level = 6 },
]
casting_time = "8 hours"
components = "V, S, M (rare incense and tonics worth 250 gp)"
range = "personal"
effects = [
  { label = "Target", value = "you" },
]
duration = "instantaneous"
saving_throw = "none"
spell_resistance = "no"
+++

::: statblock
title = "Spell statistics"
School: divination
Level: 4: Medium\
6: Cleric, Inquisitor, Oracle, Psychic, Shaman, Spiritualist, Warpriest, Witch
Casting time: 8 hours
Components: V, S, M (rare incense and tonics worth 250 gp)
Range: personal
Duration: instantaneous
Saving throw: none
Spell resistance: no
Target: you
:::

### Prognostication

You glimpse the future. Prognostication functions as [divination](ref/spell/divination) except that
the spell can see up to a year and a day into the future. Because of the increased unpredictability
of the distant future, prognostication is significantly more cryptic than the already-cryptic
divination spell.
