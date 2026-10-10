"""Analysis-only supplied-pool projection; not native entity/network generation."""
from past_raids.native_seed_state import npc_pool_indices


def project_npc_roster(seed, rows):
    if not isinstance(rows, (list, tuple)):
        raise ValueError('An ordered supplied pool is required')
    identities = [r['trainer_info'] for r in rows]
    if len(set(identities)) != len(identities):
        raise ValueError('Supplied pool trainer identities must be unique')
    selection = npc_pool_indices(seed, len(rows))
    return {**selection, 'seed': seed, 'pool_length': len(rows),
            'selected_rows': [dict(rows[i]) for i in selection['selected_pool_indices']],
            'native_entity_generation_verified': False, 'wire_encoding_verified': False}


def compare_visible_species(predictions, visible_species):
    if len(visible_species) != 3 or any(type(s) is not int or not 1 <= s <= 65535 for s in visible_species):
        raise ValueError('Three visible National Dex species IDs required')
    # Keep all exact matches; do not pick the highest seed or first candidate.
    return [p for p in predictions if p['predicted_national_species'] == list(visible_species)]
