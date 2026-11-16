+++
id = "ref/spell/glimpse-the-hidden"
kind = "spell"
title = "Glimpse the Hidden"
aon = "SpellDisplay.aspx?ItemName=Glimpse%20the%20Hidden"
source_ids = ["core-rulebook", "potions-and-poisons"]
provenance = [
  { dataset = "pathfinder-data-1-e", record = "glimpse_the_hidden", path = "json/spells15.json" },
]
relations = [
  { kind = "variant", target = "ref/spell/see-invisibility" },
]
[[sources]]
publication = "potions-and-poisons"
page = "17"

[fields]
kind = "spell"
school = "divination"
levels = [
  { class = "Alchemist", level = 3 },
  { class = "Arcanist", level = 3 },
  { class = "Inquisitor", level = 3 },
  { class = "Investigator", level = 3 },
  { class = "Sorcerer", level = 3 },
  { class = "Summoner", level = 3 },
  { class = "Unchained Summoner", level = 3 },
  { class = "Witch", level = 3 },
  { class = "Wizard", level = 3 },
]
casting_time = "1 standard action"
components = "V, S, M (a pinch of magnesium and platinum)"
range = "touch"
effects = [
  { label = "Target", value = "creature touched" },
]
duration = "1 round/level (D)"
saving_throw = "Will negates (harmless)"
spell_resistance = "yes (harmless)"
+++

::: statblock
title = "Spell statistics"
School: divination
Level: 3: Alchemist, Arcanist, Inquisitor, Investigator, Sorcerer, Summoner, Unchained Summoner, Witch, Wizard
Casting time: 1 standard action
Components: V, S, M (a pinch of magnesium and platinum)
Range: touch
Duration: 1 round/level (D)
Saving throw: Will negates (harmless)
Spell resistance: yes (harmless)
Target: creature touched
:::

### Glimpse the Hidden

This spell functions as [see invisibility](ref/spell/see-invisibility), except as noted here. This
spell cannot be made permanent.
