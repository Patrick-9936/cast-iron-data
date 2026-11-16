+++
id = "ref/spell/protection-from-arrows-communal"
kind = "spell"
title = "Communal Protection from Arrows"
aon = "SpellDisplay.aspx?ItemName=Protection%20from%20Arrows%2C%20Communal"
source_ids = ["core-rulebook", "ultimate-combat"]
provenance = [
  { dataset = "pathfinder-data-1-e", record = "protection_from_arrows_communal", path = "json/spells15.json" },
]
relations = [
  { kind = "variant", target = "ref/spell/protection-from-arrows" },
]
[[sources]]
publication = "ultimate-combat"
page = "240"

[fields]
kind = "spell"
school = "abjuration"
levels = [
  { class = "Alchemist", level = 3 },
  { class = "Arcanist", level = 3 },
  { class = "Investigator", level = 3 },
  { class = "Psychic", level = 3 },
  { class = "Sorcerer", level = 3 },
  { class = "Summoner", level = 3 },
  { class = "Unchained Summoner", level = 3 },
  { class = "Wizard", level = 3 },
]
casting_time = "1 standard action"
components = "V, S, F (a piece of tortoiseshell or turtle shell)"
range = "touch"
effects = [
  { label = "Targets", value = "creatures touched" },
]
duration = "1 hour/level or until discharged"
saving_throw = "Will negates (harmless)"
spell_resistance = "yes (harmless)"
+++

::: statblock
title = "Spell statistics"
School: abjuration
Level: 3: Alchemist, Arcanist, Investigator, Psychic, Sorcerer, Summoner, Unchained Summoner, Wizard
Casting time: 1 standard action
Components: V, S, F (a piece of tortoiseshell or turtle shell)
Range: touch
Duration: 1 hour/level or until discharged
Saving throw: Will negates (harmless)
Spell resistance: yes (harmless)
Targets: creatures touched
:::

### Communal Protection from Arrows

This spell functions like [protection from arrows](ref/spell/protection-from-arrows), except you
divide the duration in 1-hour intervals among the creatures touched. Once the spell absorbs 10
points of damage per caster level (maximum 100 points) for a subject, the spell's effects end for
that subject.
