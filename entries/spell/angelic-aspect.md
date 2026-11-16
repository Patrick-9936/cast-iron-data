+++
id = "ref/spell/angelic-aspect"
kind = "spell"
title = "Angelic Aspect"
aon = "SpellDisplay.aspx?ItemName=Angelic%20Aspect"
source_ids = ["champions-of-purity"]
provenance = [
  { dataset = "pathfinder-data-1-e", record = "angelic_aspect", path = "json/spells.json" },
]
relations = [
  { kind = "variant", target = "ref/spell/angelic-aspect-lesser" },
]
[[sources]]
publication = "champions-of-purity"
page = "28"

[fields]
kind = "spell"
school = "transmutation"
descriptors = ["good"]
levels = [
  { class = "Arcanist", level = 5 },
  { class = "Cleric", level = 5 },
  { class = "Oracle", level = 5 },
  { class = "Paladin", level = 3 },
  { class = "Sorcerer", level = 5 },
  { class = "Warpriest", level = 5 },
  { class = "Wizard", level = 5 },
]
casting_time = "1 standard action"
components = "V, S"
range = "personal"
effects = [
  { label = "Target", value = "you" },
]
duration = "1 minute/level (D)"
saving_throw = "none"
spell_resistance = "no"
+++

::: statblock
title = "Spell statistics"
School: transmutation
Level: 3: Paladin\
5: Arcanist, Cleric, Oracle, Sorcerer, Warpriest, Wizard
Casting time: 1 standard action
Components: V, S
Range: personal
Duration: 1 minute/level (D)
Saving throw: none
Spell resistance: no
Target: you
Descriptors: good
:::

### Angelic Aspect

This spell functions like [lesser angelic aspect](ref/spell/angelic-aspect-lesser), except you gain
[low-light vision](ref/rule/low-light-vision), [darkvision](ref/rule/darkvision) 60, resistance to
acid 10, resistance to cold 10, and DR 5/evil, and you sprout white feathered wings allowing you to
fly at a speed of 30 feet with average maneuverability. In addition, your natural weapons and any
weapons you wield are considered good-aligned for the purpose of overcoming
[damage reduction](ref/rule/damage-reduction).
