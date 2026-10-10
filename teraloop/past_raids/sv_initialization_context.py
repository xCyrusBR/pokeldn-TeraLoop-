"""Structurally verified SV4.0.0 property16, format4.

Arguments are intentionally unnamed: their game semantics are not established.
This implements the bounded serializer's truncation, NOT a raid/NPC generator.
"""


def pack_property16(first, second, third, fourth):
    values = (first, second, third, fourth)
    if any(type(v) is not int or not 0 <= v <= 0xFFFFFFFF for v in values):
        raise ValueError('four uint32 serializer arguments required')
    word = ((first & 31) << 27) | ((second & 7) << 24) | ((third & 255) << 16) | (fourth & 65535)
    return word.to_bytes(4, 'big')


def unpack_property16(payload):
    if not isinstance(payload, (bytes, bytearray, memoryview)) or len(payload) != 4:
        raise ValueError('property16 requires exactly four bytes')
    word = int.from_bytes(payload, 'big')
    return (word >> 27, (word >> 24) & 7, (word >> 16) & 255, word & 65535)
