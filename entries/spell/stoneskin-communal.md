+++
id = "ref/spell/stoneskin-communal"
kind = "spell"
title = "Communal Stoneskin"
aon = "SpellDisplay.aspx?ItemName=Stoneskin%2C%20Communal"
source_ids = ["ultimate-combat"]
provenance = [
  { dataset = "pathfinder-data-1-e", record = "stoneskin_communal", path = "json/spells9.json" },
]
relations = [
  { kind = "variant", target = "ref/spell/stoneskin" },
]
[[sources]]
publication = "ultimate-combat"
page = "245"

[fields]
kind = "spell"
school = "abjuration"
levels = [
  { class = "Alchemist", level = 5 },
  { class = "Arcanist", level = 5 },
  { class = "Druid", level = 6 },
  { class = "Hunter", level = 6 },
  { class = "Inquisitor", level = 5 },
  { class = "Investigator", level = 5 },
  { class = "Occultist", level = 5 },
  { class = "Psychic", level = 5 },
  { class = "Sorcerer", level = 5 },
  { class = "Summoner", level = 4 },
  { class = "Unchained Summoner", level = 5 },
  { class = "Wizard", level = 5 },
]
casting_time = "1 standard action"
components = "V, S, M (granite and diamond dust worth 250 gp per creature affected)"
range = "touch"
effects = [
  { label = "Targets", value = "creatures touched" },
]
duration = "10 min./level or until discharged"
saving_throw = "Will negates (harmless)"
spell_resistance = "yes (harmless)"
+++

::: statblock
title = "Spell statistics"
School: abjuration
Level: 4: Summoner\
5: Alchemist, Arcanist, Inquisitor, Investigator, Occultist, Psychic, Sorcerer, Unchained Summoner, Wizard\
6: Druid, Hunter
Casting time: 1 standard action
Components: V, S, M (granite and diamond dust worth 250 gp per creature affected)
Range: touch
Duration: 10 min./level or until discharged
Saving throw: Will negates (harmless)
Spell resistance: yes (harmless)
Targets: creatures touched
:::

### Communal Stoneskin

This spell functions like [stoneskin](ref/spell/stoneskin), except you divide the duration in 10
minute intervals among the creatures touched. Once the spell has prevented 10 points of damage per
caster level (maximum 150 points) for a subject, the spell's effects end for that subject.
