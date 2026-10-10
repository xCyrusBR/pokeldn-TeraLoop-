"""Measured37-field boss descriptor representations, not full raid generation.

The six native action records put Action BEFORE Timing; the event table's
dictionary order is different. No enum execution or move scheduling is implied.
"""
import struct
from past_raids.native_event_config import SCALAR_FIELDS

FIELD_PATHS = (tuple(name for name, _ in SCALAR_FIELDS[:10]) +
    tuple(f'ExtraAction{i}.{name}' for i in range(1, 7)
          for name in ('Action', 'Timing', 'Value', 'Wazano')) +
    tuple(name for name, _ in SCALAR_FIELDS[10:]))


def values(descriptor):
    if not isinstance(descriptor, dict):
        raise ValueError('Descriptor dictionary required')
    result = []
    for path in FIELD_PATHS:
        parts = path.split('.')
        value = descriptor
        for name in parts:
            if not isinstance(value, dict) or name not in value:
                raise ValueError('Missing descriptor field: '+path)
            value = value[name]
        if type(value) is not int:
            raise ValueError('Integer descriptor field required: '+path)
        result.append(value)
    return result


def encode(descriptor, *, word_bits):
    if word_bits not in (16, 32) or type(word_bits) is not int:
        raise ValueError('Measured16/32-bit representations only')
    raw = values(descriptor)
    if any(not -(1 << (word_bits-1)) <= v < 1 << word_bits for v in raw):
        raise ValueError('Descriptor field outside measured word width')
    mask = (1 << word_bits)-1
    return struct.pack('<37'+('H' if word_bits == 16 else 'I'), *(v & mask for v in raw))


def read_unsigned(raw, *, word_bits):
    if word_bits not in (16, 32) or type(word_bits) is not int:
        raise ValueError('Measured16/32-bit representations only')
    if not isinstance(raw, bytes) or len(raw) != 37*word_bits//8:
        raise ValueError('Exact descriptor byte length required')
    return dict(zip(FIELD_PATHS, struct.unpack('<37'+('H' if word_bits == 16 else 'I'), raw)))
