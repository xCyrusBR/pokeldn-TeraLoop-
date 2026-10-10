"""One editable build per event encounter, with explicit recommendation provenance.

Archive matches win. Missing guides use a resistance/sustainability heuristic
among the already validated archive builds, NOT a claim of a tested solo strategy.
"""
from dataclasses import replace
from functools import cache

from .event_generation import personal, move_data
from .strategy_defaults import TYPES, load

# Modern type chart: attack -> (super-effective, resisted, immune) defence types.
CHART = {
 'Normal': ('', 'Rock Steel', 'Ghost'),
 'Fighting': ('Normal Rock Steel Ice Dark', 'Flying Poison Bug Psychic Fairy', 'Ghost'),
 'Flying': ('Fighting Bug Grass', 'Rock Steel Electric', ''),
 'Poison': ('Grass Fairy', 'Poison Ground Rock Ghost', 'Steel'),
 'Ground': ('Poison Rock Steel Fire Electric', 'Bug Grass', 'Flying'),
 'Rock': ('Flying Bug Fire Ice', 'Fighting Ground Steel', ''),
 'Bug': ('Grass Psychic Dark', 'Fighting Flying Poison Ghost Steel Fire Fairy', ''),
 'Ghost': ('Ghost Psychic', 'Dark', 'Normal'),
 'Steel': ('Rock Ice Fairy', 'Steel Fire Water Electric', ''),
 'Fire': ('Bug Steel Grass Ice', 'Rock Fire Water Dragon', ''),
 'Water': ('Ground Rock Fire', 'Water Grass Dragon', ''),
 'Grass': ('Ground Rock Water', 'Flying Poison Bug Steel Fire Grass Dragon', ''),
 'Electric': ('Flying Water', 'Grass Electric Dragon', 'Ground'),
 'Psychic': ('Fighting Poison', 'Steel Psychic', 'Dark'),
 'Ice': ('Flying Ground Grass Dragon', 'Steel Fire Water Ice', ''),
 'Dragon': ('Dragon', 'Steel', 'Fairy'),
 'Dark': ('Ghost Psychic', 'Fighting Dark Fairy', ''),
 'Fairy': ('Fighting Dragon Dark', 'Poison Steel Fire', ''),
}
ATTACKS = frozenset(('Drain Punch', 'Rage Fist', 'Draining Kiss', 'Moonblast', 'Apple Acid',
    'Giga Drain', 'Parabolic Charge', 'Torch Song', 'Flamethrower', 'Bitter Blade',
    'Sacred Sword', 'Leech Life', 'Horn Leech', 'Liquidation', 'Shadow Ball', 'Body Press',
    'Tera Blast', 'Leaf Storm', 'Surf', 'Thunderbolt', 'Earth Power', 'Avalanche'))


def effectiveness(attack, defenders):
    if attack == 'Stellar':
        return 1.0
    weak, resist, immune = (part.split() for part in CHART[attack])
    result = 1.0
    for defence in set(defenders):
        result *= 0 if defence in immune else 2 if defence in weak else .5 if defence in resist else 1
    return result


def _immune(ability, attack, defenders):
    if (ability == 'Levitate' and attack == 'Ground'
            or ability in ('Water Absorb', 'Storm Drain') and attack == 'Water'
            or ability in ('Flash Fire', 'Well-Baked Body') and attack == 'Fire'
            or ability == 'Earth Eater' and attack == 'Ground'):
        return 0.0
    result = effectiveness(attack, defenders)
    if ability == 'Heatproof' and attack == 'Fire':
        result *= .5
    return result


def candidates(service):
    out = []
    trainer = {'ot': 'Chronos', 'tid': 12345, 'sid': 1234, 'language': 2, 'gender': 0}
    move_types = move_data()['type']
    for entry in load():
        if entry.role != 'solo' or entry.item not in ('Shell Bell', 'Metronome'):
            continue
        parsed = service.paste('sv', entry.showdown(), trainer, version='VL')[0]
        options = parsed['options']
        species, form = parsed['species_id'], options.get('form', 0)
        types = tuple(TYPES[t] for t in personal(species, form)[1])
        attacks = [(TYPES[move_types[m]], n) for m, n in zip(options['moves'], entry.moves)
                   if n in ATTACKS]
        if not attacks:
            continue
        out.append((entry, types, attacks))
    return tuple(out)


def choose(selected, service, *, pool=None, seed=0xBD13FB43):
    if selected.recommendation:
        return selected.recommendation, {'kind': 'discord-guide',
            'source': selected.recommendation.source,
            'note': 'One selected archive build. Read the guide; no AI strategy is scripted.'}
    pool = pool if pool is not None else candidates(service)
    p = selected.rule['BossPokePara']
    move_types = move_data()['type']
    threats = [TYPES[move_types[p[f'Waza{i}']['WazaId']]] for i in range(1, 5)
               if p[f'Waza{i}']['WazaId']]
    if selected.tera == 'Random':
        from pokeldn.sv.raid_encounter import Xoroshiro
        rand = Xoroshiro(seed)
        gem = p['GemType']
        actual = rand.next_int(18) if gem == 1 else personal(selected.species, p['FormId'])[1][rand.next_int(2)]
        boss_types = (TYPES[actual],)
    else:
        boss_types = (selected.tera,)
    def score(candidate):
        entry, types, attacks = candidate
        offensive = max(effectiveness(a, boss_types)*(1.5 if a in types else 1)
                        for a, _ in attacks)
        resistance = sum(_immune(entry.ability, a, types) for a in threats)/max(1, len(threats))
        sustain = .5 if entry.item == 'Shell Bell' else .3 if any(
            n in ('Drain Punch', 'Draining Kiss', 'Giga Drain', 'Parabolic Charge',
                  'Bitter Blade', 'Horn Leech') for _, n in attacks) else 0
        setup = .25 if any(n in entry.moves for n in ('Bulk Up', 'Calm Mind', 'Iron Defense',
                                                      'Swords Dance', 'Nasty Plot')) else 0
        return offensive - 2*resistance + sustain + setup
    entry, _, _ = max(pool, key=score)
    recommendation = replace(entry, boss=selected.boss, stars=selected.rule['Difficulty'],
                             boss_tera=selected.tera)
    return recommendation, {'kind': 'teraloop-suggestion', 'source': entry.source,
        'note': 'No matching archive guide. Suggested from validated builds by type resistance, '
                'offensive coverage and healing. Boss scripts, NPCs and win rate are not validated.'}
