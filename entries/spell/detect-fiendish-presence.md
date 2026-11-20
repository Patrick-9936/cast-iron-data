+++
id = "ref/spell/detect-fiendish-presence"
kind = "spell"
title = "Detect Fiendish Presence"
aon = "SpellDisplay.aspx?ItemName=Detect%20Fiendish%20Presence"
source_ids = ["core-rulebook", "agents-of-evil"]
provenance = [
  { dataset = "pathfinder-data-1-e", record = "detect_fiendish_presence", path = "json/spells3.json" },
]
relations = [
  { kind = "variant", target = "ref/spell/detect-evil" },
]
[[sources]]
publication = "agents-of-evil"
page = "16"

[fields]
kind = "spell"
school = "divination"
levels = [
  { class = "Arcanist", level = 0 },
  { class = "Bard", level = 0 },
  { class = "Cleric", level = 0 },
  { class = "Magus", level = 0 },
  { class = "Oracle", level = 0 },
  { class = "Skald", level = 0 },
  { class = "Sorcerer", level = 0 },
  { class = "Warpriest", level = 0 },
  { class = "Witch", level = 0 },
  { class = "Wizard", level = 0 },
]
casting_time = "1 standard action"
components = "V, S, DF"
range = "60 ft."
effects = [
  { label = "Area", value = "cone-shaped emanation" },
]
duration = "concentration, up to 10 min./level (D)"
saving_throw = "none"
spell_resistance = "no"
+++

::: statblock
title = "Spell statistics"
School: divination
Level: 0: Arcanist, Bard, Cleric, Magus, Oracle, Skald, Sorcerer, Warpriest, Witch, Wizard
Casting time: 1 standard action
Components: V, S, DF
Range: 60 ft.
Duration: concentration, up to 10 min./level (D)
Saving throw: none
Spell resistance: no
Area: cone-shaped emanation
:::

### Detect Fiendish Presence

This spell functions like _[detect evil](ref/spell/detect-evil),_ except that it detects only
outsiders with the evil subtype, as well as the lingering effects caused by their gifts, presence,
and spells. It can also detect clerics and paladins of fiendish deities, including
[Asmodeus](ref/faith/asmodeus), archdevils, daemonic harbingers, and demon lords.
