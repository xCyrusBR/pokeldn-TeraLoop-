"""Bounded read-only decoder for native event rules, not a battle executor.

Field layouts: pkNX SV RaidEnemyInfo and Shared PokeDataBattle schemas.
Values retain native units/enums (including internal species and GemType).
"""
from .trinity_metadata import FlatReader


def scalars(table, names, formats):
    return {name: table.scalar(i, fmt) for i, (name, fmt) in enumerate(zip(names, formats))}


def pokemon_rules(table):
    fields = ['DevId', 'FormId', 'Sex', 'Item', 'Level', 'BallId', 'WazaType']
    result = scalars(table, fields, ['<H', '<h', '<i', '<i', '<i', '<i', '<i'])
    for i in range(4):
        move = table.table(7 + i)
        result[f'Waza{i + 1}'] = scalars(move, ['WazaId', 'PointUp'], ['<H', '<b'])
    for i, name in enumerate(['GemType', 'Seikaku', 'Tokusei', 'TalentType'], 11):
        result[name] = table.scalar(i, '<i')
    result['TalentValue'] = scalars(table.table(15), ['HP', 'ATK', 'DEF', 'SPA', 'SPD', 'SPE'], ['<i'] * 6)
    result['TalentVnum'] = table.scalar(16, '<b')
    result['EffortValue'] = scalars(table.table(17), ['HP', 'ATK', 'DEF', 'SPA', 'SPD', 'SPE'], ['<i'] * 6)
    result['RareType'] = table.scalar(18, '<i')
    result['ScaleType'] = table.scalar(19, '<i')
    result['ScaleValue'] = table.scalar(20, '<h')
    return result


def boss_rules(table):
    names = ['HpCoef', 'PowerChargeTrigerHp', 'PowerChargeTrigerTime',
             'PowerChargeLimitTime', 'PowerChargeCancelDamage', 'PowerChargePenaltyTime',
             'PowerChargePenaltyAction', 'PowerChargeDamageRate', 'PowerChargeGemDamageRate',
             'PowerChargeChangeGemDamageRate']
    result = scalars(table, names, ['<h', '<b', '<b', '<h', '<b', '<h', '<H', '<b', '<b', '<b'])
    for i in range(6):
        result[f'ExtraAction{i + 1}'] = scalars(table.table(10 + i),
             ['Timing', 'Action', 'Value', 'Wazano'], ['<h', '<h', '<h', '<H'])
    for i, name in enumerate(['DoubleActionTriggerHp', 'DoubleActionTriggerTime', 'DoubleActionRate'], 16):
        result[name] = table.scalar(i, '<b')
    return result


def decode_event_rules(data):
    if len(data) > 32 * 1024 * 1024:
        raise ValueError('Event rule input exceeds analysis bound')
    root = FlatReader(data).table()
    _, count = root.vector(0, 4)
    if not 1 <= count <= 10000:
        raise ValueError('Event rule count is outside bounds')
    rows = []
    for i in range(count):
        info = root.vector_table(0, i).table(0)
        result = scalars(info, ['RomVer', 'No', 'DeliveryGroupID', 'Difficulty', 'Rate',
             'DropTableFix', 'DropTableRandom', 'CaptureRate', 'CaptureLv'],
             ['<h', '<i', '<b', '<i', '<b', '<Q', '<Q', '<b', '<b'])
        result['BossPokePara'] = pokemon_rules(info.table(9))
        result['BossPokeSize'] = scalars(info.table(10),
             ['HeightType', 'HeightValue', 'WeightType', 'WeightValue', 'ScaleType', 'ScaleValue'],
             ['<i', '<h', '<i', '<h', '<i', '<h'])
        result['BossDesc'] = boss_rules(info.table(11))
        result['TimeDesc'] = scalars(info.table(12), ['IsActive', 'GameLimit', 'ClientLimit',
             'CommandLimit', 'PokeReviveTime', 'AiIntervalTime', 'AiIntervalRand'], ['<?'] + ['<i'] * 6)
        rows.append({'Info': result})
    return {'Table': rows}
