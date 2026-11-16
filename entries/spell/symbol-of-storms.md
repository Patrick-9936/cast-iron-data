+++
id = "ref/spell/symbol-of-storms"
kind = "spell"
title = "Symbol of Storms"
aon = "SpellDisplay.aspx?ItemName=Symbol%20of%20Storms"
source_ids = ["core-rulebook", "blood-of-the-ancients"]
provenance = [
  { dataset = "pathfinder-data-1-e", record = "symbol_of_storms", path = "json/spells10.json" },
]
relations = [
  { kind = "variant", target = "ref/spell/symbol-of-death" },
]
[[sources]]
publication = "blood-of-the-ancients"
page = "28"

[fields]
kind = "spell"
school = "evocation"
descriptors = ["air", "electricity"]
levels = [
  { class = "Arcanist", level = 6 },
  { class = "Cleric", level = 6 },
  { class = "Druid", level = 6 },
  { class = "Hunter", level = 3 },
  { class = "Oracle", level = 6 },
  { class = "Ranger", level = 3 },
  { class = "Sorcerer", level = 6 },
  { class = "Warpriest", level = 6 },
  { class = "Witch", level = 6 },
  { class = "Wizard", level = 6 },
]
casting_time = "10 minutes"
components = "V, S, M (powdered copper and pumice worth a total of 1,500 gp)"
range = "0 ft.; see text"
effects = [
  { label = "Effect", value = "one symbol" },
]
duration = "see text"
saving_throw = "Reflex half; see text"
spell_resistance = "yes"
+++

::: statblock
title = "Spell statistics"
School: evocation
Level: 3: Hunter, Ranger\
6: Arcanist, Cleric, Druid, Oracle, Sorcerer, Warpriest, Witch, Wizard
Casting time: 10 minutes
Components: V, S, M (powdered copper and pumice worth a total of 1,500 gp)
Range: 0 ft.; see text
Duration: see text
Saving throw: Reflex half; see text
Spell resistance: yes
Effect: one symbol
Descriptors: air, electricity
:::

### Symbol of Storms

This spell functions as [symbol of death](ref/spell/symbol-of-death), except that when triggered, a
30-foot-radius centered on the symbol fills with hurricane-force winds (75 mph). Each round, a bolt
of lightning that deals 10d6 points of electricity damage strikes a random creature within the area.
A successful Reflex save halves this damage. Unlike symbol of death, symbol of storms has no hit
point limit. Regardless of the trigger method or methods chosen, a creature more than 30 feet from a
symbol of storms can't trigger it (even if it meets one or more of the triggering conditions, such
as reading the rune). Once triggered, a symbol of storms remains active for 1 minute per caster
level.
