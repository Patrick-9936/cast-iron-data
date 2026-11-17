+++
id = "ref/spell/detect-charm"
kind = "spell"
title = "Detect Charm"
aon = "SpellDisplay.aspx?ItemName=Detect%20Charm"
source_ids = ["core-rulebook", "adventurers-guide", "andoran-spirit-of-liberty", "ultimate-intrigue"]
provenance = [
  { dataset = "pathfinder-data-1-e", record = "detect_charm", path = "json/spells3.json" },
]
relations = [
  { kind = "variant", target = "ref/spell/detect-magic" },
]
[[sources]]
publication = "adventurers-guide"
page = "77"
[[sources]]
publication = "andoran-spirit-of-liberty"
page = "27"
[[sources]]
publication = "ultimate-intrigue"
page = "212"

[fields]
kind = "spell"
school = "divination"
levels = [
  { class = "Arcanist", level = 1 },
  { class = "Bard", level = 1 },
  { class = "Cleric", level = 1 },
  { class = "Inquisitor", level = 1 },
  { class = "Medium", level = 1 },
  { class = "Mesmerist", level = 1 },
  { class = "Occultist", level = 1 },
  { class = "Oracle", level = 1 },
  { class = "Paladin", level = 1 },
  { class = "Psychic", level = 1 },
  { class = "Shaman", level = 1 },
  { class = "Skald", level = 1 },
  { class = "Sorcerer", level = 1 },
  { class = "Spiritualist", level = 1 },
  { class = "Warpriest", level = 1 },
  { class = "Witch", level = 1 },
  { class = "Wizard", level = 1 },
]
casting_time = "1 standard action"
components = "V, S"
range = "60 ft."
effects = [
  { label = "Area", value = "cone-shaped emanation" },
]
duration = "concentration, up to 1 min./level (D)"
saving_throw = "none"
spell_resistance = "no"
+++

::: statblock
title = "Spell statistics"
School: divination
Level: 1: Arcanist, Bard, Cleric, Inquisitor, Medium, Mesmerist, Occultist, Oracle, Paladin, Psychic, Shaman, Skald, Sorcerer, Spiritualist, Warpriest, Witch, Wizard
Casting time: 1 standard action
Components: V, S
Range: 60 ft.
Duration: concentration, up to 1 min./level (D)
Saving throw: none
Spell resistance: no
Area: cone-shaped emanation
:::

### Detect Charm

This spell functions as per _[detect magic](ref/spell/detect-magic),_ except that it detects only
charm, compulsion, and possession effects. You immediately detect the strength and location of each
such aura on all creatures in the area. You can attempt to identify the properties of each aura (see
[Spellcraft](ref/skill/spellcraft)). In addition to noticing the targets of these effects, you can
recognize when creatures in the area are using these effects on others by attempting a
[Sense Motive](ref/skill/sense-motive) check as a standard action (DC = 20 + caster level). If you
succeed, you can attempt a Spellcraft check to identify what magic it is using (even if the target
is not in the area).
