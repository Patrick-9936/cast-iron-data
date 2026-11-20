+++
id = "ref/spell/undeath-sense"
kind = "spell"
title = "Undeath Sense"
aon = "SpellDisplay.aspx?ItemName=Undeath%20Sense"
source_ids = ["potions-and-poisons"]
provenance = [
  { dataset = "pathfinder-data-1-e", record = "undeath_sense", path = "json/spells3.json" },
]
relations = [
  { kind = "variant", target = "ref/spell/detect-undead" },
]
[[sources]]
publication = "potions-and-poisons"
page = "18"

[fields]
kind = "spell"
school = "divination"
levels = [
  { class = "Alchemist", level = 2 },
  { class = "Arcanist", level = 2 },
  { class = "Cleric", level = 2 },
  { class = "Inquisitor", level = 2 },
  { class = "Investigator", level = 2 },
  { class = "Oracle", level = 2 },
  { class = "Paladin", level = 2 },
  { class = "Shaman", level = 2 },
  { class = "Sorcerer", level = 2 },
  { class = "Warpriest", level = 2 },
  { class = "Wizard", level = 2 },
]
casting_time = "1 standard action"
components = "V, S, M/DF (ashes from an urn)"
range = "touch"
effects = [
  { label = "Target", value = "creature touched" },
]
duration = "10 minutes/level (D)"
saving_throw = "none"
spell_resistance = "no"
+++

::: statblock
title = "Spell statistics"
School: divination
Level: 2: Alchemist, Arcanist, Cleric, Inquisitor, Investigator, Oracle, Paladin, Shaman, Sorcerer, Warpriest, Wizard
Casting time: 1 standard action
Components: V, S, M/DF (ashes from an urn)
Range: touch
Duration: 10 minutes/level (D)
Saving throw: none
Spell resistance: no
Target: creature touched
:::

### Undeath Sense

You grant the target the ability to pick up on the subtle scents and disturbances to the natural
order that are specific to the living dead, granting the target the ability to sense the presence of
undead creatures. The target is constantly aware of whether there are any undead auras within 60
feet of her in any direction. If at least one undead aura is present, the target can concentrate on
the spell's effects in order to gain more information on the auras present. This functions similarly
to [detect undead](ref/spell/detect-undead), except the number of rounds of concentration needed to
learn about the undead auras is reduced by 1 (1 round to learn the number of auras, and 2 rounds to
learn the strength and location of each aura).
