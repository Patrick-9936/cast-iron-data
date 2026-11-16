+++
id = "ref/spell/bestow-planar-infusion-3"
kind = "spell"
title = "Bestow Planar Infusion III"
aon = "SpellDisplay.aspx?ItemName=Bestow%20Planar%20Infusion%20III"
source_ids = ["planar-adventures"]
provenance = [
  { dataset = "pathfinder-data-1-e", record = "bestow_planar_infusion_3", path = "json/spells12.json" },
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
  { class = "Arcanist", level = 7 },
  { class = "Cleric", level = 7 },
  { class = "Oracle", level = 7 },
  { class = "Psychic", level = 7 },
  { class = "Sorcerer", level = 7 },
  { class = "Witch", level = 7 },
  { class = "Wizard", level = 7 },
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
Level: 7: Arcanist, Cleric, Oracle, Psychic, Sorcerer, Witch, Wizard
Casting time: 1 standard action
Components: V, S
Range: touch
Duration: 1 hour/level
Saving throw: Fortitude negates (harmless)
Spell resistance: yes
Target: creature touched
:::

### Bestow Planar Infusion III

This functions as [bestow planar infusion I](ref/spell/bestow-planar-infusion-1), except that the
touched creature gains the greater infusion of the current plane.
