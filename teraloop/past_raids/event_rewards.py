"""Bounded source reward decoder, not random selection or reward generation.

Schemas: kwsch/pkNX d191cd0e5c05f2af81d9a41c1f1d82e6621b351a,
FlatBuffers/SV/Raid/Schemas/Raid{Fixed,Lottery}RewardItem{Array,Info}.fbs.
Category, SubjectType and ItemID are int32; Num is signed byte.
"""
from .trinity_metadata import FlatReader


def decode(data, *, kind):
    if kind not in ('fixed', 'lottery'):
        raise ValueError('Fixed or lottery schema required')
    if not isinstance(data, bytes) or len(data) > 32*1024*1024:
        raise ValueError('Bounded binary reward source required')
    root = FlatReader(data).table()
    _, count = root.vector(0, 4)
    if not 1 <= count <= 10000:
        raise ValueError('Bounded nonempty table vector required')
    tables = []
    fields = (('Category', '<i'), ('SubjectType', '<i'), ('ItemID', '<i'), ('Num', '<b')) if kind == 'fixed' else (
        ('Category', '<i'), ('ItemID', '<i'), ('Num', '<b'), ('Rate', '<i'), ('RareItemFlag', '<?'))
    for i in range(count):
        table = root.vector_table(0, i)
        name = table.scalar(0, '<Q')
        # Native delivery arrays contain repeated placeholder hash keys.
        # Preserve every row; an active table lookup must demand uniqueness.
        row = {'TableName': name}
        for j in range(15 if kind == 'fixed' else 30):
            item = table.table(j+1)
            row[f'RewardItem{j:02}'] = {key: item.scalar(k, fmt) for k, (key, fmt) in enumerate(fields)}
        tables.append(row)
    return {'Table': tables}
