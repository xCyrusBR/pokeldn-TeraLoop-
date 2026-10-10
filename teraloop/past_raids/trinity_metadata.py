"""Bounded read-only FlatBuffer metadata used by SV's Trinity archives.

Layouts: pkNX FlatBuffers/SV/Trinity/Schemas. No decompression, game execution,
encrypted content writing or key management is performed here.
"""
import struct


def gf_hash(path):
    """Game Freak's FNV-1a variant (non-standard initial basis)."""
    value = 0xCBF29CE484222645
    for byte in path.encode('utf-8'):
        value = ((value ^ byte) * 0x100000001B3) & 0xFFFFFFFFFFFFFFFF
    return value


class FlatReader:
    def __init__(self, data):
        self.data = memoryview(data).toreadonly()

    def number(self, offset, fmt):
        size = struct.calcsize(fmt)
        if type(offset) is not int or offset < 0 or offset + size > len(self.data):
            raise ValueError('FlatBuffer numeric field outside input')
        return struct.unpack_from(fmt, self.data, offset)[0]

    def table(self, position=None):
        return FlatTable(self, self.number(0, '<I') if position is None else position)


class FlatTable:
    def __init__(self, reader, position):
        self.reader, self.position = reader, position
        self.vtable = position - reader.number(position, '<i')
        self.vsize = reader.number(self.vtable, '<H')
        self.size = reader.number(self.vtable + 2, '<H')
        if (self.vsize < 4 or self.vsize % 2 or self.size < 4 or
                position + self.size > len(reader.data) or
                self.vtable + self.vsize > len(reader.data)):
            raise ValueError('FlatBuffer table bounds are invalid')

    def field(self, index, width=4):
        if type(index) is not int or index < 0:
            raise ValueError('invalid FlatBuffer field index')
        slot = self.vtable + 4 + index * 2
        if slot + 2 > self.vtable + self.vsize:
            return None
        offset = self.reader.number(slot, '<H')
        if offset == 0:
            return None
        if offset < 4 or offset + width > self.size:
            raise ValueError('FlatBuffer field exceeds object')
        return self.position + offset

    def scalar(self, index, fmt, default=0):
        pointer = self.field(index, struct.calcsize(fmt))
        return default if pointer is None else self.reader.number(pointer, fmt)

    def vector(self, index, stride):
        if type(stride) is not int or stride <= 0:
            raise ValueError('invalid FlatBuffer vector stride')
        pointer = self.field(index)
        if pointer is None:
            return 0, 0
        start = pointer + self.reader.number(pointer, '<I')
        count = self.reader.number(start, '<I')
        if count > 16_000_000 or start + 4 + count * stride > len(self.reader.data):
            raise ValueError('FlatBuffer vector exceeds bounded input')
        return start + 4, count

    def vector_table(self, index, item):
        start, count = self.vector(index, 4)
        if type(item) is not int or not 0 <= item < count:
            raise ValueError('FlatBuffer table vector index out of range')
        pointer = start + item * 4
        return self.reader.table(pointer + self.reader.number(pointer, '<I'))

    def string(self, index, limit=4096):
        pointer = self.field(index)
        if pointer is None:
            return None
        start = pointer + self.reader.number(pointer, '<I')
        length = self.reader.number(start, '<I')
        end = start + 4 + length
        if length > limit or end >= len(self.reader.data) or self.reader.data[end] != 0:
            raise ValueError('FlatBuffer string exceeds bounds or lacks terminator')
        return bytes(self.reader.data[start + 4:end]).decode('utf-8', 'strict')

    def table(self, index):
        pointer = self.field(index)
        if pointer is None:
            raise ValueError('Required FlatBuffer table absent')
        return self.reader.table(pointer + self.reader.number(pointer, '<I'))


def pack_metadata(data):
    table = FlatReader(data).table()
    hashes, count = table.vector(0, 8)
    offsets, other_count = table.vector(1, 8)
    if count != other_count:
        raise ValueError('Trinity pack hashes and offsets differ in count')
    result = {}
    for i in range(count):
        key = table.reader.number(hashes + i * 8, '<Q')
        if key in result:
            raise ValueError('duplicate Trinity pack hash')
        result[key] = table.reader.number(offsets + i * 8, '<Q')
    return result


def packed_file_shapes(data):
    table = FlatReader(data).table()
    hashes, count = table.vector(0, 8)
    _, other_count = table.vector(1, 4)
    if count != other_count:
        raise ValueError('Trinity file hashes and entries differ in count')
    result = []
    for i in range(count):
        entry = table.vector_table(1, i)
        _, encoded_size = entry.vector(4, 1)
        result.append({'hash': table.reader.number(hashes + i * 8, '<Q'),
                       'compression': entry.scalar(1, '<B'),
                       'decoded_bytes': entry.scalar(3, '<Q'),
                       'encoded_bytes': encoded_size})
    return result


def packed_file_payload(data, index, max_bytes=16 * 1024 * 1024):
    """Return bounded encoded bytes; caller chooses its offline decoder."""
    shapes = packed_file_shapes(data)
    if type(index) is not int or not 0 <= index < len(shapes):
        raise ValueError('Trinity file index outside pack')
    shape = shapes[index]
    if not 0 <= shape['decoded_bytes'] <= max_bytes or shape['encoded_bytes'] > max_bytes:
        raise ValueError('Trinity subfile exceeds analysis limit')
    entry = FlatReader(data).table().vector_table(1, index)
    start, size = entry.vector(4, 1)
    return shape, bytes(entry.reader.data[start:start + size])


def raid_trainer_shape(data):
    """Structural candidate only; asset identity/semantics need independent proof."""
    root = FlatReader(data).table()
    _, count = root.vector(0, 4)
    if not 1 <= count <= 512:
        raise ValueError('Not a bounded RaidTrainerArray candidate')
    rows = []
    for i in range(count):
        entry = root.vector_table(0, i)
        info, label = entry.string(0), entry.string(2)
        preset = entry.scalar(1, '<i')
        if not info or not label or not 0 <= preset <= 4096:
            raise ValueError('Not a RaidTrainer schema candidate')
        rows.append({'trainer_info': info, 'preset_index': preset, 'name_label': label})
    return rows


def raid_assist_pokemon(data):
    """Read only raid_assist rows from the known TrDataMainArray schema."""
    root = FlatReader(data).table()
    _, count = root.vector(0, 4)
    if not 1 <= count <= 20000:
        raise ValueError('Trainer array count exceeds bound')
    rows = []
    for i in range(count):
        entry = root.vector_table(0, i)
        identity = entry.string(0)
        if not identity or not identity.startswith('raid_assist_NPC_'):
            continue
        poke = entry.table(8)
        rows.append({'trainer_info': identity, 'name_label': entry.string(1),
                     'trainer_type': entry.string(2),
                     'species_internal_id': poke.scalar(0, '<H'),
                     'form': poke.scalar(1, '<h'), 'level': poke.scalar(4, '<i'),
                     'moves': [poke.table(n).scalar(0, '<H') for n in range(7, 11)],
                     'ai_raid': bool(entry.scalar(18, '<B'))})
    return rows
