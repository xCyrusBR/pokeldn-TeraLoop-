"""Experimental source-generated event bosses and RaidPoints; no battle replay.

RNG ordering follows PKHeX Encounter9RNG / Tera-Finder EncounterTF9RNG.
Only event records selected explicitly from a hash-verified delivery are used.
Untraced RaidPoint words remain zero, as in the reviewed upstream generator.
Generated events require console validation; the measured Mewtwo capsule is kept.
"""
import json
import struct
from pathlib import Path
from functools import cache

from .event_rewards import decode
from .native_boss_descriptor import encode as boss_descriptor
from .native_time_descriptor import encode as time_descriptor
from .save_injector import VERSION_SUFFIXES

ROOT = Path(__file__).resolve().parents[1]
STAT_NAMES = ('HP', 'ATK', 'DEF', 'SPE', 'SPA', 'SPD')


@cache
def move_data():
    return json.loads((ROOT/'distribution/gen9-move-data.json').read_text(encoding='utf-8'))


@cache
def personal(species, form=0):
    data = json.loads((ROOT/'distribution/gen9-personal-data.json').read_text(encoding='utf-8'))
    e = data['personal'][f'{species}/{form}']
    return tuple(e[:6]), tuple(e[6:8]), e[8], e[9], e[10], tuple(e[11:14])


def size(kind, value, rand):
    if kind == 0:
        return rand.next_int(0x81) + rand.next_int(0x80)
    if kind == 6 and 0 <= value <= 255:
        return value
    ranges = {1: (16, 0), 2: (32, 16), 3: (160, 48), 4: (32, 208), 5: (16, 240)}
    if kind not in ranges:
        raise ValueError('Unsupported event size rule')
    maximum, low = ranges[kind]
    return low + rand.next_int(maximum)


def boss_fields(seed, rule, encounter, gen9, names):
    if not 0 <= seed <= 0xffffffff:
        raise ValueError('Event seed must fit uint32')
    p = rule['BossPokePara']
    species, form = gen9.national(p['DevId']), p['FormId']
    base, types, ratio, _friendship, growth, abilities = personal(species, form)
    rand = encounter.Xoroshiro(seed)
    ec, fake_id, pid = rand.next_int(), rand.next_int(), rand.next_int()
    xor = (fake_id & 65535) ^ (fake_id >> 16) ^ (pid & 65535) ^ (pid >> 16)
    if p['RareType'] == 1 and xor < 16:
        pid ^= 0x10000000
    elif p['RareType'] == 2:
        # Guaranteed shiny keeps the low word, changing the high word to xor=0.
        pid = (pid & 65535) | (((fake_id & 65535) ^ (fake_id >> 16) ^ (pid & 65535)) << 16)
    elif p['RareType'] not in (0, 1, 2):
        raise ValueError('Unknown event shiny rule')
    draw_names = ('HP', 'ATK', 'DEF', 'SPA', 'SPD', 'SPE')
    if p['TalentType'] == 2:
        iv_draw = [p['TalentValue'][s] for s in draw_names]
    elif p['TalentType'] == 1:
        iv_draw = [-1] * 6
        if not 0 <= p['TalentVnum'] <= 6:
            raise ValueError('Invalid guaranteed IV count')
        for _ in range(p['TalentVnum']):
            i = rand.next_int(6)
            while iv_draw[i] != -1:
                i = rand.next_int(6)
            iv_draw[i] = 31
    else:
        raise ValueError('Unknown event IV rule')
    iv_draw = [rand.next_int(32) if v == -1 else v for v in iv_draw]
    if any(not 0 <= v <= 31 for v in iv_draw):
        raise ValueError('Invalid event IV')
    ability = {0: lambda: rand.next_int(2), 1: lambda: rand.next_int(3),
               2: lambda: 0, 3: lambda: 1, 4: lambda: 2}[p['Tokusei']]()
    # Sex is the native 0=random, 1=male, 2=female, 3=genderless enum.
    if rule['Difficulty'] == 7 and p['Sex'] in (1, 2, 3):
        ratio = {1: 0, 2: 254, 3: 255}[p['Sex']]
    gender = (2 if ratio == 255 else 1 if ratio == 254 else 0 if ratio == 0
              else int(rand.next_int(100) < encounter.GENDER_CUTOFF[ratio]))
    if p['Seikaku']:
        nature = p['Seikaku'] - 1
    elif species == encounter.TOXTRICITY:
        allowed = encounter.TOXTRICITY_NATURES[form]
        nature = allowed[rand.next_int(len(allowed))]
    else:
        nature = rand.next_int(25)
    if not 0 <= nature < 25:
        raise ValueError('Invalid event nature')
    height = rand.next_int(0x81) + rand.next_int(0x80)
    weight = rand.next_int(0x81) + rand.next_int(0x80)
    scale = size(p['ScaleType'], p['ScaleValue'], rand)
    ivs = tuple(dict(zip(draw_names, iv_draw))[s] for s in STAT_NAMES)
    evs = tuple(p['EffortValue'][s] for s in STAT_NAMES)
    if any(not 0 <= v <= 252 for v in evs) or sum(evs) > 510:
        raise ValueError('Invalid event effort')
    level = p['Level']
    stats = encounter.stats(base, ivs, level, nature, evs)
    moves = tuple(p[f'Waza{i}']['WazaId'] for i in range(1, 5))
    ups = tuple(p[f'Waza{i}']['PointUp'] for i in range(1, 5))
    pp = move_data()['pp']
    if any(not 0 <= m < len(pp) for m in moves) or any(not 0 <= u <= 3 for u in ups):
        raise ValueError('Unsupported event moves')
    gem = p['GemType']
    tera = (gem-2 if 2 <= gem <= 19 else encounter.Xoroshiro(seed).next_int(18)
            if gem == 1 else types[encounter.Xoroshiro(seed).next_int(2)] if gem == 0 else None)
    if tera is None:
        raise ValueError('Invalid event Tera rule')
    return dict(species=species, form=form, level=level, met_level=level,
        experience=encounter.experience(level, growth), encryption_constant=ec,
        trainer_id=fake_id & 65535, secret_id=fake_id >> 16, pid=pid,
        ability=abilities[ability], ability_number=1 << ability, gender=gender,
        nature=nature, stat_nature=nature, ivs=ivs, evs=evs,
        height_scalar=height, weight_scalar=weight, scale=scale,
        held_item=p['Item'], tera_type_original=tera,
        tera_type_override=encounter.TERA_NONE, moves=moves, move_pp_ups=ups,
        move_pp=tuple(pp[m]*(5+u)//5 for m, u in zip(moves, ups)),
        current_hp=stats[0], stats=stats, nickname=names[species], language=2,
        affixed_ribbon=-1)


def source_table(package, kind, key):
    prefix = 'fixed_reward_item_array' if kind == 'fixed' else 'lottery_reward_item_array'
    path = next((package.root/'Files'/(prefix+s) for s in VERSION_SUFFIXES
                 if (package.root/'Files'/(prefix+s)).is_file()), None)
    if path is None:
        raise ValueError('Event reward source missing')
    tables = decode(path.read_bytes(), kind=kind)['Table']
    selected = [t for t in tables if t['TableName'] == key]
    if len(selected) != 1:
        raise ValueError('Event reward table is missing or ambiguous')
    return [value for field, value in selected[0].items() if field != 'TableName']


def rewards(seed, package, rule, boss, encounter):
    fixed = source_table(package, 'fixed', rule['DropTableFix'])
    lottery = source_table(package, 'lottery', rule['DropTableRandom'])
    def resolved(r):
        item = r['ItemID']
        if not item and r['Category'] == 1:
            item = int(encounter.tables()['material_items'].get(str(boss['species']), 0))
            # Tera-Finder GetMaterial explicitly returns 0 for paradox species.
            if not item and r['Num'] and boss['species'] not in (
                    984, 985, 986, 987, 988, 989, 1005, 1009, 1020, 1021,
                    990, 991, 992, 993, 994, 995, 1006, 1010, 1022, 1023):
                raise ValueError('Missing authoritative boss material item')
        elif not item and r['Category'] == 2:
            item = encounter.TERA_SHARDS[boss['tera_type_original']]
        if r['Num'] < 0 or r['Category'] not in (0, 1, 2):
            raise ValueError('Unsupported event reward category/quantity')
        return item, r['Num'], r.get('SubjectType', 0)
    out = [resolved(r) for r in fixed if r['Num']]
    active = [r for r in lottery if r['Rate'] > 0]
    total = sum(r['Rate'] for r in active)
    if total:
        rand = encounter.Xoroshiro(seed)
        count_rows = (*encounter.REWARD_SLOTS, encounter.REWARD_SLOTS[-1])
        roll = rand.next_int(100)
        count = count_rows[rule['Difficulty']-1][sum(roll >= edge for edge in encounter.REWARD_COLUMNS)]
        for _ in range(count):
            threshold = rand.next_int(total)
            for r in active:
                if threshold < r['Rate']:
                    out.append(resolved(r))
                    break
                threshold -= r['Rate']
    return tuple(r for r in out if r[0] and r[1])


def generate(seed, package, rule, encounter, gen9, names, *, version='violet'):
    if rule not in package.native_rules or rule['RomVer'] not in (0, 1 if version == 'scarlet' else 2):
        raise ValueError('Encounter not available in selected event/version')
    boss = boss_fields(seed, rule, encounter, gen9, names)
    reward_rows = rewards(seed, package, rule, boss, encounter)
    row = {'identifier': rule['No'], 'capture_level': rule['CaptureLv'],
           'boss_desc': list(struct.unpack('<37I', boss_descriptor(rule['BossDesc'], word_bits=32))),
           'event_rule': rule, 'event_rewards': reward_rows}
    return encounter.Raid(seed, version, 'paldea', '6star', 'event', rule['Difficulty'],
        row, boss, tuple((i, q) for i, q, _ in reward_rows))


def raid_point(found, raid, gen9, *, name=None):
    rule = found.row['event_rule']
    out = bytearray(raid.POINT_SIZE)
    encoded = (name or raid.POINT_NAME).encode('ascii')
    if not encoded.startswith(b'RaidPoint_') or len(encoded) > 23:
        raise ValueError('Invalid event RaidPoint name')
    out[:len(encoded)] = encoded
    out[0x18] = 0x40
    # Native Mewtwo: mighty crystal=2, capture rule=2, event content=4.
    struct.pack_into('<4I', out, 0x20, found.stars, 2 if found.stars == 7 else 0,
                     rule['CaptureRate'], rule['CaptureLv'])
    out[0x30:0x4c] = time_descriptor(rule['TimeDesc'])
    out[0x4c:0xe0] = boss_descriptor(rule['BossDesc'], word_bits=32)
    rows = found.row['event_rewards']
    if len(rows) > raid.REWARD_ROWS:
        raise ValueError('Too many event reward rows')
    for i, (item, quantity, subject) in enumerate(rows):
        struct.pack_into('<4I', out, raid.POINT_REWARDS+i*16, item, quantity, 0, subject)
    struct.pack_into('<7I', out, raid.POINT_SUMMARY, found.stars,
        gen9.internal_index(found.species), found.boss['form'], found.boss['gender'],
        found.boss['level'], 0, found.tera_type)
    struct.pack_into('<I', out, 0x3e0, 4 if found.stars == 7 else 3)
    return bytes(out)


def install(found, raid, encounter, gen9):
    """Process-local adapter; the pinned upstream source remains unchanged."""
    original_generate, original_point = encounter.generate, raid.raid_point
    def selected(seed, version='violet', map_name='paldea', progress='4star', content='standard'):
        if (seed, version) != (found.seed, found.version) or map_name != 'paldea':
            raise ValueError('Selected event context changed')
        return found
    def point(candidate, rewards=None, name=raid.POINT_NAME):
        if candidate is not found:
            return original_point(candidate, rewards, name)
        if rewards is not None:
            raise ValueError('Custom rewards are not allowed for original event deliveries')
        return raid_point(found, raid, gen9, name=name)
    encounter.generate, raid.raid_point = selected, point
    return original_generate, original_point
