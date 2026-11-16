+++
id = "ref/spell/absorb-rune-2"
kind = "spell"
title = "Absorb Rune II"
aon = "SpellDisplay.aspx?ItemName=Absorb%20Rune%20II"
source_ids = ["adventurers-guide"]
provenance = [
  { dataset = "pathfinder-data-1-e", record = "absorb_rune_2", path = "json/spells.json" },
]
relations = [
  { kind = "variant", target = "ref/spell/absorb-rune-1" },
]
[[sources]]
publication = "adventurers-guide"
page = "60"

[fields]
kind = "spell"
school = "abjuration"
levels = [
  { class = "Arcanist", level = 6 },
  { class = "Bard", level = 6 },
  { class = "Cleric", level = 6 },
  { class = "Magus", level = 6 },
  { class = "Occultist", level = 6 },
  { class = "Oracle", level = 6 },
  { class = "Skald", level = 6 },
  { class = "Sorcerer", level = 6 },
  { class = "Warpriest", level = 6 },
  { class = "Wizard", level = 6 },
]
casting_time = "1 standard action"
components = "V, S, M (a white silk glove worth 25 gp)"
range = "touch"
effects = [
  { label = "Target", value = "one spell effect" },
]
duration = "instantaneous plus 1 minute/level (see text)"
saving_throw = "Will negates (harmless)"
spell_resistance = "yes (harmless)"
+++

::: statblock
title = "Spell statistics"
School: abjuration
Level: 6: Arcanist, Bard, Cleric, Magus, Occultist, Oracle, Skald, Sorcerer, Warpriest, Wizard
Casting time: 1 standard action
Components: V, S, M (a white silk glove worth 25 gp)
Range: touch
Duration: instantaneous plus 1 minute/level (see text)
Saving throw: Will negates (harmless)
Spell resistance: yes (harmless)
Target: one spell effect
:::

### Absorb Rune II

This spell functions like [absorb rune I](ref/spell/absorb-rune-1), but it can affect runes
equivalent to a spell of 5th level or lower.
