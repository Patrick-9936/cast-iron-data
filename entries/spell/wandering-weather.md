+++
id = "ref/spell/wandering-weather"
kind = "spell"
title = "Wandering Weather"
aon = "SpellDisplay.aspx?ItemName=Wandering%20Weather"
source_ids = ["ultimate-wilderness"]
provenance = [
  { dataset = "pathfinder-data-1-e", record = "wandering_weather", path = "json/spells12.json" },
]
relations = [
  { kind = "variant", target = "ref/spell/control-weather" },
]
[[sources]]
publication = "ultimate-wilderness"
page = "237"

[fields]
kind = "spell"
school = "transmutation"
levels = [
  { class = "Arcanist", level = 8 },
  { class = "Cleric", level = 8 },
  { class = "Druid", level = 8 },
  { class = "Oracle", level = 8 },
  { class = "Shaman", level = 8 },
  { class = "Sorcerer", level = 8 },
  { class = "Witch", level = 8 },
  { class = "Wizard", level = 8 },
]
casting_time = "10 minutes; see text"
components = "V, S"
range = "2 miles"
effects = [
  { label = "Area", value = "2-mile-radius circle, centered on you; see text" },
]
duration = "4d12 hours; see text"
saving_throw = "none"
spell_resistance = "no"
+++

::: statblock
title = "Spell statistics"
School: transmutation
Level: 8: Arcanist, Cleric, Druid, Oracle, Shaman, Sorcerer, Witch, Wizard
Casting time: 10 minutes; see text
Components: V, S
Range: 2 miles
Duration: 4d12 hours; see text
Saving throw: none
Spell resistance: no
Area: 2-mile-radius circle, centered on you; see text
:::

### Wandering Weather

This spell functions as [control weather](ref/spell/control-weather) except you can opt for the
weather to remain centered on you as you move.
