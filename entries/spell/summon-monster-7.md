+++
id = "ref/spell/summon-monster-7"
kind = "spell"
title = "Summon Monster VII"
aon = "SpellDisplay.aspx?ItemName=Summon%20Monster%207"
source_ids = ["core-rulebook", "monster-summoners-handbook"]
provenance = [
  { dataset = "pathfinder-data-1-e", record = "summon_monster_7", path = "json/spells16.json" },
]
relations = [
  { kind = "variant", target = "ref/spell/summon-monster-1" },
]
[[sources]]
publication = "core-rulebook"
page = "352"

[fields]
kind = "spell"
school = "conjuration"
subschools = ["Summoning"]
levels = [
  { class = "Arcanist", level = 7 },
  { class = "Cleric", level = 7 },
  { class = "Oracle", level = 7 },
  { class = "Psychic", level = 7 },
  { class = "Sorcerer", level = 7 },
  { class = "Summoner", level = 5 },
  { class = "Unchained Summoner", level = 6 },
  { class = "Witch", level = 7 },
  { class = "Wizard", level = 7 },
]
casting_time = "1 round"
components = "V, S, F/DF (a tiny bag and a small candle)"
range = "close (25 ft. + 5 ft./2 levels)"
effects = [
  { label = "Effect", value = "one summoned creature" },
]
duration = "1 round/level (D)"
saving_throw = "none"
spell_resistance = "no"
+++

::: statblock
title = "Spell statistics"
School: conjuration
Level: 5: Summoner\
6: Unchained Summoner\
7: Arcanist, Cleric, Oracle, Psychic, Sorcerer, Witch, Wizard
Casting time: 1 round
Components: V, S, F/DF (a tiny bag and a small candle)
Range: close (25 ft. + 5 ft./2 levels)
Duration: 1 round/level (D)
Saving throw: none
Spell resistance: no
Effect: one summoned creature
Subschool: Summoning
:::

### Summon Monster VII

This spell functions like [summon monster I](ref/spell/summon-monster-1), except that you can summon
one creature from the 7th-level list, 1d3 creatures of the same kind from the 6th-level list, or
1d4+1 creatures of the same kind from a lower-level list.

###### ^1^ {#footnote-1}

By a strict rules-as-written interpretation, regular casters can only apply the celestial or
fiendish templates, since this spell was written before the resolute and entropic templates existed.
_Bestiary 2_ introduced the resolute and entropic templates and said they could apply to summons,
but left no specifics. _Monster Summoner's Handbook_ added archetypes that could use the resolute
and entropic templates. However, Paizo's official open-content website cites _MSH_ and notes "summon
monster can be used to summon creatures with the entropic or resolute templates instead of the
celestial or fiendish template". In any event, only one template may be applied automatically to a
summoned creature: lawful good casters could choose celestial or resolute, but not both. Consult
your GM.

###### ^2^ {#footnote-2}

The original text was written before the entropic and resolute templates were created (see footnote
above), so the text generally refers to neutral on the good-evil axis only. However, a neutral good
caster could theoretically pick either resolute or entropic instead of the default celestial.
Consult your GM.
