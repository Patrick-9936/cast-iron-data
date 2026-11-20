+++
id = "ref/spell/brightest-light"
kind = "spell"
title = "Brightest Light"
aon = "SpellDisplay.aspx?ItemName=Brightest%20Light"
source_ids = ["adventurers-guide", "inner-sea-intrigue"]
provenance = [
  { dataset = "pathfinder-data-1-e", record = "brightest_light", path = "json/spells3.json" },
]
relations = [
  { kind = "variant", target = "ref/spell/daylight" },
]
[[sources]]
publication = "adventurers-guide"
page = "115"
[[sources]]
publication = "inner-sea-intrigue"
page = "58"

[fields]
kind = "spell"
school = "evocation"
descriptors = ["light"]
levels = [
  { class = "Arcanist", level = 4 },
  { class = "Bard", level = 4 },
  { class = "Cleric", level = 4 },
  { class = "Druid", level = 4 },
  { class = "Hunter", level = 4 },
  { class = "Inquisitor", level = 4 },
  { class = "Magus", level = 4 },
  { class = "Occultist", level = 4 },
  { class = "Oracle", level = 4 },
  { class = "Paladin", level = 4 },
  { class = "Ranger", level = 4 },
  { class = "Shaman", level = 4 },
  { class = "Skald", level = 4 },
  { class = "Sorcerer", level = 4 },
  { class = "Warpriest", level = 4 },
  { class = "Wizard", level = 4 },
]
casting_time = "1 standard action"
components = "V, S"
range = "touch"
effects = [
  { label = "Target", value = "object touched" },
]
duration = "1 hour/level (D)"
saving_throw = "none"
spell_resistance = "no"
+++

::: statblock
title = "Spell statistics"
School: evocation
Level: 4: Arcanist, Bard, Cleric, Druid, Hunter, Inquisitor, Magus, Occultist, Oracle, Paladin, Ranger, Shaman, Skald, Sorcerer, Warpriest, Wizard
Casting time: 1 standard action
Components: V, S
Range: touch
Duration: 1 hour/level (D)
Saving throw: none
Spell resistance: no
Target: object touched
Descriptors: light
:::

### Brightest Light

This trademark spell of the [Lantern Bearers](ref/rule/aff-lights) functions as
[daylight](ref/spell/daylight), except it lasts longer. In addition, as a swift action once during
the spell's duration, you can will the light to try to end a magical darkness effect located within
60 feet of the light this spell emits. Attempt a dispel check (1d20 + your caster level), with a DC
equal to 11 + the caster level of the darkness effect. If you succeed, the darkness effect ends.
Regardless of whether you are successful, the light from this spell dims to the brightness of a
torch for the spell's remaining duration.
