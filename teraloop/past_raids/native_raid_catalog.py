"""Join locally inspected native raid tables. Does not select RNG or start a raid.

No copyrighted asset bytes are included here. The report is generated locally by
tools/inventory_native_sv_romfs.py using the user's own game files.
"""
from past_raids.trinity_metadata import gf_hash


def npc_pools_from_inventory(report):
    packs = report['candidate_pack_metadata']
    pokemon = {}
    for pack in packs:
        for row in pack.get('raid_assist_pokemon', []):
            identity = row['trainer_info']
            if identity in pokemon and pokemon[identity] != row:
                raise ValueError('Conflicting native NPC Pokemon rows')
            pokemon[identity] = row
    pools = {}
    for number in range(1, 4):
        path = f'world/data/raid/raid_trainer_{number:02d}/raid_trainer_{number:02d}_array.bin'
        matching = [pack for pack in packs if pack['candidate'] == path]
        if len(matching) != 1:
            raise ValueError('Native NPC pool path not uniquely verified')
        tables = [table for table in matching[0].get('raid_trainer_structural_candidates', [])
                  if table['file_hash'] == gf_hash(path)]
        if len(tables) != 1:
            raise ValueError('Native NPC pool hash not uniquely verified')
        rows, identities = [], set()
        for trainer in tables[0]['rows']:
            identity = trainer['trainer_info']
            if identity in identities or identity not in pokemon:
                raise ValueError('Native NPC pool has duplicate or missing Pokemon')
            identities.add(identity)
            poke = pokemon[identity]
            if not poke['ai_raid'] or trainer['name_label'] != poke['name_label']:
                raise ValueError('Native NPC trainer/Pokemon link disagrees')
            rows.append({**poke, 'preset_index': trainer['preset_index']})
        pools[number] = rows
    return pools
