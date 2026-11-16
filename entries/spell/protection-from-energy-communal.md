+++
id = "ref/spell/protection-from-energy-communal"
kind = "spell"
title = "Communal Protection from Energy"
aon = "SpellDisplay.aspx?ItemName=Protection%20from%20Energy%2C%20Communal"
source_ids = ["core-rulebook", "ultimate-combat"]
provenance = [
  { dataset = "pathfinder-data-1-e", record = "protection_from_energy_communal", path = "json/spells15.json" },
]
relations = [
  { kind = "variant", target = "ref/spell/protection-from-energy" },
]
[[sources]]
publication = "ultimate-combat"
page = "240"

[fields]
kind = "spell"
school = "abjuration"
levels = [
  { class = "Arcanist", level = 4 },
  { class = "Cleric", level = 4 },
  { class = "Druid", level = 4 },
  { class = "Hunter", level = 3 },
  { class = "Inquisitor", level = 4 },
  { class = "Oracle", level = 4 },
  { class = "Psychic", level = 4 },
  { class = "Ranger", level = 3 },
  { class = "Sorcerer", level = 4 },
  { class = "Summoner", level = 4 },
  { class = "Unchained Summoner", level = 4 },
  { class = "Warpriest", level = 4 },
  { class = "Wizard", level = 4 },
]
casting_time = "1 standard action"
components = "V, S, DF"
range = "touch"
effects = [
  { label = "Targets", value = "creatures touched" },
]
duration = "10 min./level or until discharged"
saving_throw = "Fortitude negates (harmless)"
spell_resistance = "yes (harmless)"
+++

::: statblock
title = "Spell statistics"
School: abjuration
Level: 3: Hunter, Ranger\
4: Arcanist, Cleric, Druid, Inquisitor, Oracle, Psychic, Sorcerer, Summoner, Unchained Summoner, Warpriest, Wizard
Casting time: 1 standard action
Components: V, S, DF
Range: touch
Duration: 10 min./level or until discharged
Saving throw: Fortitude negates (harmless)
Spell resistance: yes (harmless)
Targets: creatures touched
:::

### Communal Protection from Energy

This spell functions like [protection from energy](ref/spell/protection-from-energy), except you
divide the duration in 10-minute intervals among the creatures touched. Once the spell absorbs 12
points of energy damage per caster level (maximum 120 points) for a subject, the spell's effects end
for that subject.
