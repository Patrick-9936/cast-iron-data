+++
id = "ref/spell/escape-alarm"
kind = "spell"
title = "Escape Alarm"
aon = "SpellDisplay.aspx?ItemName=Escape%20Alarm"
source_ids = ["core-rulebook", "villain-codex", "ultimate-intrigue"]
provenance = [
  { dataset = "pathfinder-data-1-e", record = "escape_alarm", path = "json/spells.json" },
]
relations = [
  { kind = "variant", target = "ref/spell/alarm" },
]
[[sources]]
publication = "villain-codex"
page = "45"
[[sources]]
publication = "ultimate-intrigue"
page = "224"

[fields]
kind = "spell"
school = "abjuration"
levels = [
  { class = "Arcanist", level = 2 },
  { class = "Bard", level = 2 },
  { class = "Hunter", level = 2 },
  { class = "Inquisitor", level = 2 },
  { class = "Occultist", level = 2 },
  { class = "Psychic", level = 2 },
  { class = "Ranger", level = 2 },
  { class = "Skald", level = 2 },
  { class = "Sorcerer", level = 2 },
  { class = "Spiritualist", level = 2 },
  { class = "Summoner", level = 2 },
  { class = "Unchained Summoner", level = 2 },
  { class = "Wizard", level = 2 },
]
casting_time = "1 standard action"
components = "V, S, F (a short segment of a chain)"
range = "medium (100 ft. + 10 ft./level)"
effects = [
  { label = "Area", value = "ten 10-foot cubes/level" },
]
duration = "24 hours"
saving_throw = "none"
spell_resistance = "no"
+++

::: statblock
title = "Spell statistics"
School: abjuration
Level: 2: Arcanist, Bard, Hunter, Inquisitor, Occultist, Psychic, Ranger, Skald, Sorcerer, Spiritualist, Summoner, Unchained Summoner, Wizard
Casting time: 1 standard action
Components: V, S, F (a short segment of a chain)
Range: medium (100 ft. + 10 ft./level)
Duration: 24 hours
Saving throw: none
Spell resistance: no
Area: ten 10-foot cubes/level
:::

### Escape Alarm

You place a ward on an area that notifies you when a creature exits it. This functions as
[alarm](ref/spell/alarm), except as noted. It alerts you when a creature leaves, rather than enters,
the area, and you can't select a password to bypass its effects. Instead, when you place an escape
alarm, you can attune up to one additional creature per caster level to the spell. You are
automatically attuned to your own escape alarm and don't count against the limit. Attuned creatures
can enter and exit the spell's area without triggering the alarm. If you select a mental alarm
rather than an audible one, all attuned creatures receive the mental alert when someone exits the
warded area.
