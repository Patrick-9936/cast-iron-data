+++
id = "ref/spell/nexs-secret-workshop"
kind = "spell"
title = "Nex's Secret Workshop"
aon = "SpellDisplay.aspx?ItemName=Nex%27s%20Secret%20Workshop"
source_ids = ["inner-sea-intrigue"]
provenance = [
  { dataset = "pathfinder-data-1-e", record = "nexs_secret_workshop", path = "json/spells7.json" },
]
relations = [
  { kind = "variant", target = "ref/spell/nondetection" },
]
[[sources]]
publication = "inner-sea-intrigue"
page = "60"

[fields]
kind = "spell"
school = "abjuration"
levels = [
  { class = "Arcanist", level = 5 },
  { class = "Medium", level = 4 },
  { class = "Mesmerist", level = 5 },
  { class = "Occultist", level = 5 },
  { class = "Psychic", level = 5 },
  { class = "Sorcerer", level = 5 },
  { class = "Spiritualist", level = 5 },
  { class = "Summoner", level = 5 },
  { class = "Unchained Summoner", level = 5 },
  { class = "Wizard", level = 5 },
]
casting_time = "1 standard action"
components = "V, S, M (diamond dust worth 150 gp)"
range = "close (25 ft. + 5 ft./2 levels)"
effects = [
  { label = "Targets", value = "any number of creatures or objects in range" },
]
duration = "1 hour/level"
saving_throw = "Will negates (harmless) (object)"
spell_resistance = "yes (harmless) (object)"
+++

::: statblock
title = "Spell statistics"
School: abjuration
Level: 4: Medium\
5: Arcanist, Mesmerist, Occultist, Psychic, Sorcerer, Spiritualist, Summoner, Unchained Summoner, Wizard
Casting time: 1 standard action
Components: V, S, M (diamond dust worth 150 gp)
Range: close (25 ft. + 5 ft./2 levels)
Duration: 1 hour/level
Saving throw: Will negates (harmless) (object)
Spell resistance: yes (harmless) (object)
Targets: any number of creatures or objects in range
:::

### Nex's Secret Workshop

Designed to protect a large number of items from rivals of the Arclords of Nex, this spell functions
as [nondetection](ref/spell/nondetection) except as noted above. You can exclude any creatures or
objects in the spell's range when casting this spell, if you wish.
