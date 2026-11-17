+++
id = "ref/spell/curse-major"
kind = "spell"
title = "Major Curse"
aon = "SpellDisplay.aspx?ItemName=Curse%2C%20Major"
source_ids = ["core-rulebook", "pathfinder-82-secrets-of-the-sphinx", "ultimate-intrigue", "ultimate-magic"]
provenance = [
  { dataset = "pathfinder-data-1-e", record = "curse_major", path = "json/spells12.json" },
]
relations = [
  { kind = "variant", target = "ref/spell/bestow-curse" },
]
[[sources]]
publication = "ultimate-magic"
page = "215"
[[sources]]
publication = "pathfinder-82-secrets-of-the-sphinx"
page = "75"
[[sources]]
publication = "ultimate-intrigue"
page = "206"

[fields]
kind = "spell"
school = "necromancy"
descriptors = ["curse"]
levels = [
  { class = "Arcanist", level = 6 },
  { class = "Cleric", level = 5 },
  { class = "Mesmerist", level = 4 },
  { class = "Occultist", level = 5 },
  { class = "Oracle", level = 5 },
  { class = "Psychic", level = 6 },
  { class = "Shaman", level = 5 },
  { class = "Sorcerer", level = 6 },
  { class = "Spiritualist", level = 5 },
  { class = "Warpriest", level = 5 },
  { class = "Witch", level = 5 },
  { class = "Wizard", level = 6 },
]
casting_time = "1 standard action"
components = "V, S"
range = "close (25 ft. + 5 ft./2 levels)"
effects = [
  { label = "Target", value = "one creature" },
]
duration = "permanent"
saving_throw = "Will negates"
spell_resistance = "yes"
+++

::: statblock
title = "Spell statistics"
School: necromancy
Level: 4: Mesmerist\
5: Cleric, Occultist, Oracle, Shaman, Spiritualist, Warpriest, Witch\
6: Arcanist, Psychic, Sorcerer, Wizard
Casting time: 1 standard action
Components: V, S
Range: close (25 ft. + 5 ft./2 levels)
Duration: permanent
Saving throw: Will negates
Spell resistance: yes
Target: one creature
Descriptors: curse
:::

### Major Curse

This spell functions as [bestow curse](ref/spell/bestow-curse), except the DC to remove the curse is
equal to the save DC + 5.
