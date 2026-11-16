+++
id = "ref/spell/bestow-planar-infusion-2"
kind = "spell"
title = "Bestow Planar Infusion II"
aon = "SpellDisplay.aspx?ItemName=Bestow%20Planar%20Infusion%20II"
source_ids = ["planar-adventures"]
provenance = [
  { dataset = "pathfinder-data-1-e", record = "bestow_planar_infusion_2", path = "json/spells12.json" },
]
relations = [
  { kind = "variant", target = "ref/spell/bestow-planar-infusion-1" },
]
[[sources]]
publication = "planar-adventures"
page = "39"

[fields]
kind = "spell"
school = "evocation"
levels = [
  { class = "Arcanist", level = 4 },
  { class = "Cleric", level = 4 },
  { class = "Inquisitor", level = 4 },
  { class = "Magus", level = 4 },
  { class = "Medium", level = 4 },
  { class = "Occultist", level = 4 },
  { class = "Oracle", level = 4 },
  { class = "Psychic", level = 4 },
  { class = "Sorcerer", level = 4 },
  { class = "Summoner", level = 4 },
  { class = "Unchained Summoner", level = 4 },
  { class = "Warpriest", level = 4 },
  { class = "Witch", level = 4 },
  { class = "Wizard", level = 4 },
]
casting_time = "1 standard action"
components = "V, S"
range = "touch"
effects = [
  { label = "Target", value = "creature touched" },
]
duration = "1 hour/level"
saving_throw = "Fortitude negates (harmless)"
spell_resistance = "yes"
+++

::: statblock
title = "Spell statistics"
School: evocation
Level: 4: Arcanist, Cleric, Inquisitor, Magus, Medium, Occultist, Oracle, Psychic, Sorcerer, Summoner, Unchained Summoner, Warpriest, Witch, Wizard
Casting time: 1 standard action
Components: V, S
Range: touch
Duration: 1 hour/level
Saving throw: Fortitude negates (harmless)
Spell resistance: yes
Target: creature touched
:::

### Bestow Planar Infusion II

This functions as [bestow planar infusion I](ref/spell/bestow-planar-infusion-1), except that the
touched creature gains the improved infusion of the current plane.
