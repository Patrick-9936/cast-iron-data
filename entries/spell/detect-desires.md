+++
id = "ref/spell/detect-desires"
kind = "spell"
title = "Detect Desires"
aon = "SpellDisplay.aspx?ItemName=Detect%20Desires"
source_ids = ["ultimate-intrigue"]
provenance = [
  { dataset = "pathfinder-data-1-e", record = "detect_desires", path = "json/spells3.json" },
]
relations = [
  { kind = "variant", target = "ref/spell/detect-thoughts" },
]
[[sources]]
publication = "ultimate-intrigue"
page = "211"

[fields]
kind = "spell"
school = "divination"
descriptors = ["mind-affecting"]
levels = [
  { class = "Antipaladin", level = 2 },
  { class = "Arcanist", level = 3 },
  { class = "Bard", level = 2 },
  { class = "Cleric", level = 3 },
  { class = "Inquisitor", level = 3 },
  { class = "Medium", level = 2 },
  { class = "Mesmerist", level = 3 },
  { class = "Oracle", level = 3 },
  { class = "Paladin", level = 3 },
  { class = "Psychic", level = 2 },
  { class = "Skald", level = 2 },
  { class = "Sorcerer", level = 3 },
  { class = "Spiritualist", level = 3 },
  { class = "Warpriest", level = 3 },
  { class = "Witch", level = 3 },
  { class = "Wizard", level = 3 },
]
casting_time = "1 standard action"
components = "V, S, F/DF (a medallion)"
range = "60 ft."
effects = [
  { label = "Area", value = "cone-shaped emanation" },
]
duration = "concentration, up to 1 minute/level (D)"
saving_throw = "Will negates (see text)"
spell_resistance = "no"
+++

::: statblock
title = "Spell statistics"
School: divination
Level: 2: Antipaladin, Bard, Medium, Psychic, Skald\
3: Arcanist, Cleric, Inquisitor, Mesmerist, Oracle, Paladin, Sorcerer, Spiritualist, Warpriest, Witch, Wizard
Casting time: 1 standard action
Components: V, S, F/DF (a medallion)
Range: 60 ft.
Duration: concentration, up to 1 minute/level (D)
Saving throw: Will negates (see text)
Spell resistance: no
Area: cone-shaped emanation
Descriptors: mind-affecting
:::

### Detect Desires

This spell functions as per [detect thoughts](ref/spell/detect-thoughts), except you sense
significant desires of creatures with an Intelligence score of 1 or higher, regardless of whether
they are conscious or not.

Instead of Intelligence, the second round of concentration reveals each mind's Charisma score. If
the highest Charisma score is 26 or higher (and at least 10 points higher than your own Charisma
score), you are stunned for 1 round and the spell ends. Instead of surface thoughts, the third round
of concentration reveals the most pressing current desire of any mind in the area (Will negates).

Presenting a creature with an opportunity to fulfill a significant desire grants you a +2
circumstance bonus (or higher, at the GM's discretion) on Diplomacy checks to influence it.
