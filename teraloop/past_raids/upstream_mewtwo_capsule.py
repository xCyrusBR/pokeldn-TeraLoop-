"""Measured Mewtwo encounter capsule for the isolated upstream handoff.

Reuses only native boss PK9 and RaidPoint, not participants or battle snapshots.
Event generation/random seeds remain unresolved. Never relabel another event.
"""
import hashlib
import json
import struct
from pathlib import Path

from .event import EventPackage
from .native_boss_descriptor import encode as boss_descriptor
from .native_time_descriptor import matches as timer_matches

REFERENCE_SHA = '97a83e311702b89f1506edaabfc56f547317319fbc7d94de7dde148803e177c9'
EVENT_SHA = '1686e7fc6106728d1df9f200f05e31244c34e7c45fa15d3f0d37d3e855670609'
PUBLIC_CAPSULE_SHA = '8af8280edde3eea3ca5b5421b45fcf0f11978e3b16085a34d19a4e596c726383'


def native_bootstrap(path, raid, streams):
    raw = Path(path).read_bytes()
    # Portable release contains only the boss and RaidPoint, no participants,
    # trainer identities, network addresses or captured battle traffic.
    if len(raw) == 1344 and hashlib.sha256(raw).hexdigest() == PUBLIC_CAPSULE_SHA:
        return bytes(1376) + raw
    if hashlib.sha256(raw).hexdigest() != REFERENCE_SHA:
        raise ValueError('Mewtwo reference differs from measured capsule')
    fragments = {}
    for line in raw.decode('utf-8').splitlines():
        row = json.loads(line)
        if row.get('event') != 'proxy' or row.get('source_ip') != '192.168.1.1':
            continue
        if row.get('authenticated') is not True:
            raise ValueError('Native reference must be authenticated')
        for msg in row.get('messages', ()):
            rel = msg.get('reliable') or {}
            if ((msg.get('protocol'), msg.get('port')) != (128, 0)
                    or rel.get('is_ack') or not rel.get('payload')):
                continue
            flags, seq = int(rel['flags']), int(rel['sequence_id'])
            data = bytes.fromhex(rel['payload'])
            if flags & 16:
                data = streams.decompress(data)
            value = (flags & ~16, data)
            if fragments.setdefault(seq, value) != value:
                raise ValueError('Conflicting native fragments')
    candidates = []
    for seq, (flags, data) in sorted(fragments.items()):
        if flags & 2 and data[:3] == bytes.fromhex('80332f'):
            parts = [data]
            while not flags & 4:
                seq += 1
                if seq not in fragments:
                    raise ValueError('Incomplete native bootstrap')
                flags, data = fragments[seq]
                if flags & 2:
                    raise ValueError('Unexpected start inside native bootstrap')
                parts.append(data)
            candidates.append(raid.payload_of(b''.join(parts)))
    if len(candidates) != 1 or len(candidates[0]) != 2720:
        raise ValueError('Exactly one measured2720-byte bootstrap required')
    return candidates[0]


def install(raid, encounter, gen9, streams, *, reference, event_root, version, map_name, progress):
    source = Path(event_root)/'Files/raid_enemy_array_1_3_0'
    if hashlib.sha256(source.read_bytes()).hexdigest() != EVENT_SHA:
        raise ValueError('Mewtwo event source differs')
    package = EventPackage.load(event_root)
    rules = [rule for rule in package.native_rules
             if rule['BossPokePara']['DevId'] == 150 and rule['Difficulty'] == 7]
    if len(rules) != 1:
        raise ValueError('Unique Mewtwo7-star rule required')
    rule = rules[0]
    original = native_bootstrap(reference, raid, streams)
    boss_raw, point = original[1376:1720], original[1720:]
    boss = gen9.read(gen9.load(boss_raw))
    p = rule['BossPokePara']
    expected = {'species': 150, 'form': p['FormId'], 'level': p['Level'],
                'moves': tuple(p[f'Waza{i}']['WazaId'] for i in range(1, 5)),
                'tera_type_original': p['GemType']-2}
    if any(boss[key] != value for key, value in expected.items()):
        raise ValueError('Measured boss differs from original Mewtwo encounter')
    if point[0x4c:0xe0] != boss_descriptor(rule['BossDesc'], word_bits=32):
        raise ValueError('Native shield/action descriptor differs from event source')
    if not timer_matches(point[48:76], rule['TimeDesc']):
        raise ValueError('Native timer differs from event source')
    summary = struct.unpack_from('<7I', point, 0x3b8)
    if summary != (7, 150, boss['form'], boss['gender'], boss['level'], 0, boss['tera_type_original']):
        raise ValueError('Native boss summary mismatch')
    rewards = tuple((item, quantity) for item, quantity, _, _ in
                    struct.iter_unpack('<4I', point[0xe4:0x3b4]) if item and quantity)
    row = {'identifier': rule['No'], 'capture_level': rule['CaptureLv'],
           'boss_desc': list(struct.unpack_from('<37I', point, 0x4c))}
    # Seed32 recovered from boss EC is metadata, NOT randomized event generation.
    boss_seed = (boss['encryption_constant']-0x229d6a5b) & 0xffffffff
    found = encounter.Raid(boss_seed, version, map_name, progress, 'event', 7,
                           row, boss, rewards)
    old_generate, old_point, old_boss = encounter.generate, raid.raid_point, raid.boss_record
    def event_generate(seed, version='violet', map_name='paldea', progress='4star', content='standard'):
        if (seed, version, map_name, progress, content) != (boss_seed, found.version, found.map_name, found.progress, 'standard'):
            raise ValueError('Measured event capsule context differs; no random event seeds')
        return found
    def event_point(selected, rewards=None, name=raid.POINT_NAME):
        if selected is found:
            if rewards is not None or name != raid.POINT_NAME:
                raise ValueError('Native event capsule cannot replace rewards/point name')
            return point
        return old_point(selected, rewards, name)
    def event_boss(selected):
        return boss_raw if selected is found else old_boss(selected)
    encounter.generate, raid.raid_point, raid.boss_record = event_generate, event_point, event_boss
    return found, {'event': 29, 'boss_source': 'hash-pinned native PK9',
                   'point_sha256': hashlib.sha256(point).hexdigest(),
                   'seed_configurable': False, 'battle_snapshots_replayed': False,
                   'boss_descriptor_matches_source': True, 'timer_matches_source': True}
