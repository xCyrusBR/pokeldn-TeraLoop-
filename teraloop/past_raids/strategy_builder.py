"""Build a recommendation locally, then verify its actual PK9 battle fields."""
import base64
from .strategy_defaults import TYPES


def build(entry, service, gen9, encounter, trainer, *, version='violet', keep=True, seed_file=None):
    version = {'scarlet': 'SL', 'violet': 'VL'}.get(version, version)
    sets = service.paste('sv', entry.showdown(), trainer, version=version)
    if len(sets) != 1 or sets[0].get('errors'):
        raise ValueError('Recommendation parse failed: ' + str(sets))
    requested = sets[0]
    # Use the service protocol without keeping an intermediate, incomplete file.
    reply = service.check('sv', str(seed_file)) if seed_file else service._ask({'cmd': 'make', 'game': 'sv',
        'species': requested['species_id'], 'level': 100, 'shiny': False,
        'nickname': '', 'trainer': trainer, 'version': version,
        'options': requested['options']})
    if not reply.get('legal'):
        raise ValueError('Recommendation is not legal: ' + reply.get('report', ''))
    plain = gen9.load(base64.b64decode(reply['data']))
    fields = gen9.read(plain)
    changes = {}
    if seed_file:
        # A prevalidated event Mew is a creation fallback, not a legality bypass.
        options = requested['options']
        changes.update(stat_nature=options['nature'],
                       evs=tuple(options['effort'].get(s, 0) for s in ('hp', 'atk', 'def', 'spe', 'spa', 'spd')),
                       moves=tuple(options['moves']) + (0,) * (4 - len(options['moves'])))
    # Upstream Showdown importer explicitly ignores Tera. Do NOT trust its preview.
    if entry.tera:
        changes['tera_type_override'] = TYPES.index(entry.tera)
    pp = encounter.tables()['move_pp']
    moves = changes.get('moves', fields['moves'])
    # A seed PK9's remaining PP belongs to its old moves, not their new slots.
    seed_pp = {m: fields['move_pp'][i] * 5 // (5 + fields['move_pp_ups'][i])
               for i, m in enumerate(fields['moves']) if m}
    if seed_file and any(m and str(m) not in pp and m not in seed_pp for m in moves):
        raise ValueError('No authoritative base PP for replacement seed move')
    changes['move_pp_ups'] = tuple(3 if m else 0 for m in moves)
    # The ordinary raid table lists only boss moves, not every support move.
    # A newly built/healed PK9 supplies the remaining moves' base PP.
    base_pp = tuple(int(pp[str(m)]) if str(m) in pp else seed_pp.get(m, 0)
                    for m in moves)
    changes['move_pp'] = tuple(base_pp[i] * 8 // 5 if m else 0
                              for i, m in enumerate(moves))
    modified = gen9.encrypt(gen9.write(plain, **changes))
    final = service.check_bytes('sv', modified)
    if not final.get('legal'):
        raise ValueError('Final recommendation is not legal: ' + final.get('report', ''))
    actual = gen9.read(gen9.load(base64.b64decode(final['data'])))
    wanted_evs = entry.effort()
    expected_evs = tuple(wanted_evs.get(s, 0) for s in ('HP', 'Atk', 'Def', 'Spe', 'SpA', 'SpD'))
    # gen9 uses HP/Atk/Def/Spe/SpA/SpD (check the schema; never swap special stats).
    if tuple(actual['evs']) != expected_evs:
        raise ValueError('Builder changed recommended EVs')
    if final['level'] != 100 or final['nature'] != entry.nature:
        raise ValueError('Builder changed level/nature')
    if final['moves'] != list(entry.moves) or final['held_item'] != entry.item:
        raise ValueError('Builder changed moves/item')
    if entry.ability and final['ability'] != entry.ability:
        raise ValueError('Builder changed ability')
    if entry.tera and actual['tera_type_override'] != TYPES.index(entry.tera):
        raise ValueError('Builder changed recommended Tera')
    if (tuple(actual['move_pp_ups']) != changes['move_pp_ups']
            or tuple(actual['move_pp']) != changes['move_pp']):
        raise ValueError('Builder changed max PP')
    final.update(source=entry.source, recommendation_role=entry.role,
                 strategy_scripted=False, tera=entry.tera or 'Unspecified')
    if keep:
        final['file'] = service.keep('sv', final)
    return final
