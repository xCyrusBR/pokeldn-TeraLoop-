"""Read-only Paldea den seed audit; never guesses battle RNG/wire fields.

Layout source: PKHeX RaidSpawnList9.cs. A seed is input to encounter generation,
not an operation-21 result, a transport nonce, or an executable battle engine.
"""
import struct
from .save_injector import KEY_TERA_RAID_PALDEA, decode_save, verify_round_trip


def read_raid_seed_block(data):
    if len(data) < 16 or (len(data)-16) % 32 not in (0, 8):
        raise ValueError('Invalid Paldea raid seed block layout')
    current, tomorrow = struct.unpack_from('<QQ', data)
    count = (len(data)-16)//32
    active = []
    for index in range(count):
        offset = 16 + index*32
        enabled, area, group, point, seed, unused, content, claimed = struct.unpack_from('<8I', data, offset)
        if enabled:
            active.append({'index': index, 'seed': f'{seed:08X}', 'content': content,
                           'area': area, 'group': group, 'point': point})
    return {'current_daily_seed': f'{current:016X}', 'tomorrow_daily_seed': f'{tomorrow:016X}',
            'active_crystals': active, 'entry_capacity': count,
            'uninterpreted_tail_bytes': len(data)-16-count*32,
            'battle_rng_identified': False,
            'synthetic_battle_ready': False}


def audit_save(raw):
    verify_round_trip(raw)
    blocks = decode_save(raw)
    matches = [b for b in blocks if b.key == KEY_TERA_RAID_PALDEA]
    if len(matches) != 1:
        raise ValueError('Expected exactly one Paldea raid block')
    return read_raid_seed_block(matches[0].data)
