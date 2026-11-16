+++
id = "ref/spell/ray-of-sickening"
kind = "spell"
title = "Ray of Sickening"
aon = "SpellDisplay.aspx?ItemName=Ray%20of%20Sickening"
source_ids = ["core-rulebook", "ultimate-magic", "dark-markets-a-guide-to-katapesh"]
provenance = [
  { dataset = "pathfinder-data-1-e", record = "ray_of_sickening", path = "json/spells8.json" },
]
relations = [
  { kind = "variant", target = "ref/spell/ray-of-exhaustion" },
]
[[sources]]
publication = "ultimate-magic"
page = "234"
[[sources]]
publication = "dark-markets-a-guide-to-katapesh"
page = "57"

[fields]
kind = "spell"
school = "necromancy"
levels = [
  { class = "Arcanist", level = 1 },
  { class = "Bloodrager", level = 1 },
  { class = "Cleric", level = 1 },
  { class = "Druid", level = 1 },
  { class = "Hunter", level = 1 },
  { class = "Mesmerist", level = 1 },
  { class = "Oracle", level = 1 },
  { class = "Sorcerer", level = 1 },
  { class = "Summoner", level = 1 },
  { class = "Unchained Summoner", level = 1 },
  { class = "Warpriest", level = 1 },
  { class = "Witch", level = 1 },
  { class = "Wizard", level = 1 },
]
casting_time = "1 standard action"
components = "V, S, M (a drop of sweat)"
range = "close (25 ft. + 5 ft./2 levels)"
effects = [
  { label = "Effect", value = "ray" },
]
duration = "1 minute/level"
saving_throw = "Fortitude partial, see text"
spell_resistance = "yes"
+++

::: statblock
title = "Spell statistics"
School: necromancy
Level: 1: Arcanist, Bloodrager, Cleric, Druid, Hunter, Mesmerist, Oracle, Sorcerer, Summoner, Unchained Summoner, Warpriest, Witch, Wizard
Casting time: 1 standard action
Components: V, S, M (a drop of sweat)
Range: close (25 ft. + 5 ft./2 levels)
Duration: 1 minute/level
Saving throw: Fortitude partial, see text
Spell resistance: yes
Effect: ray
:::

### Ray of Sickening

This spell functions as [ray of exhaustion](ref/spell/ray-of-exhaustion), except the target is
sickened if it fails its save and unaffected if it makes its save.
