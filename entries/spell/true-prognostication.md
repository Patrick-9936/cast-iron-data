+++
id = "ref/spell/true-prognostication"
kind = "spell"
title = "True Prognostication"
aon = "SpellDisplay.aspx?ItemName=True%20Prognostication"
source_ids = ["core-rulebook", "ultimate-intrigue"]
provenance = [
  { dataset = "pathfinder-data-1-e", record = "true_prognostication", path = "json/spells13.json" },
]
relations = [
  { kind = "variant", target = "ref/spell/divination" },
]
[[sources]]
publication = "ultimate-intrigue"
page = "228"

[fields]
kind = "spell"
school = "divination"
levels = [
  { class = "Cleric", level = 8 },
  { class = "Oracle", level = 8 },
  { class = "Psychic", level = 8 },
  { class = "Shaman", level = 8 },
  { class = "Witch", level = 8 },
]
casting_time = "1 week"
components = "V, S, M (rare incense and tonics worth 1,000 gp)"
range = "personal"
effects = [
  { label = "Target", value = "you" },
]
duration = "instantaneous"
saving_throw = "none"
spell_resistance = "no"
+++

::: statblock
title = "Spell statistics"
School: divination
Level: 8: Cleric, Oracle, Psychic, Shaman, Witch
Casting time: 1 week
Components: V, S, M (rare incense and tonics worth 1,000 gp)
Range: personal
Duration: instantaneous
Saving throw: none
Spell resistance: no
Target: you
:::

### True Prognostication

True prognostication functions as [divination](ref/spell/divination) except that the spell can see
up to 100 years into the future. Because of the extreme unpredictability of the far-distant future,
true prognostication is incredibly cryptic when used to learn about events on such large a scale.
