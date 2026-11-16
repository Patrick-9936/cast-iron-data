+++
id = "ref/spell/object-possession"
kind = "spell"
title = "Object Possession"
aon = "SpellDisplay.aspx?ItemName=Object%20Possession"
source_ids = ["occult-adventures"]
provenance = [
  { dataset = "pathfinder-data-1-e", record = "object_possession", path = "json/spells7.json" },
]
relations = [
  { kind = "variant", target = "ref/spell/object-possession-lesser" },
]
[[sources]]
publication = "occult-adventures"
page = "179"

[fields]
kind = "spell"
school = "necromancy"
levels = [
  { class = "Arcanist", level = 5 },
  { class = "Medium", level = 4 },
  { class = "Mesmerist", level = 5 },
  { class = "Occultist", level = 4 },
  { class = "Psychic", level = 5 },
  { class = "Sorcerer", level = 5 },
  { class = "Spiritualist", level = 5 },
  { class = "Witch", level = 5 },
  { class = "Wizard", level = 5 },
]
casting_time = "1 standard action"
components = "V, S"
range = "close (25 ft. + 5 ft./2 levels)"
effects = [
  { label = "Target", value = "unattended Large or smaller object (minimum Tiny)" },
]
duration = "10 minutes/level (D)"
saving_throw = "none"
spell_resistance = "no"
+++

::: statblock
title = "Spell statistics"
School: necromancy
Level: 4: Medium, Occultist\
5: Arcanist, Mesmerist, Psychic, Sorcerer, Spiritualist, Witch, Wizard
Casting time: 1 standard action
Components: V, S
Range: close (25 ft. + 5 ft./2 levels)
Duration: 10 minutes/level (D)
Saving throw: none
Spell resistance: no
Target: unattended Large or smaller object (minimum Tiny)
:::

### Object Possession

This spell functions as [lesser object possession](ref/spell/object-possession-lesser), except as
noted above. The possessed animated object has a number of Construction Points appropriate for its
size (up to 3 CP for Large objects).

You can return your consciousness to your body as a standard action. On your next turn, you can
attempt to possess a different object as a standard action instead of ending the spell.
