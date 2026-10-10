"""Measured initialization timer projection; not a running battle timer.

Reference Mewtwo/Charizard rosters place the active byte, three unconstrained
bytes, then six little-endian signed32 values before the boss descriptor.
The three bytes are preserved, not assumed to be a counter or zero padding.
No native object, packet, runtime or countdown is created here.
"""
import struct

INTEGER_FIELDS = ('GameLimit', 'ClientLimit', 'CommandLimit', 'PokeReviveTime',
                  'AiIntervalTime', 'AiIntervalRand')
SIZE = 28
OBSERVED_OFFSET = 1768


def encode(descriptor, *, reserved=b'\0\0\0'):
    if not isinstance(descriptor, dict) or type(descriptor.get('IsActive')) is not bool:
        raise ValueError('Boolean IsActive required')
    if not isinstance(reserved, bytes) or len(reserved) != 3:
        raise ValueError('Exactly three preserved bytes required')
    values = [descriptor.get(name) for name in INTEGER_FIELDS]
    if any(type(v) is not int or not -(1 << 31) <= v < (1 << 31) for v in values):
        raise ValueError('Six signed32 timer fields required')
    return bytes([int(descriptor['IsActive'])]) + reserved + struct.pack('<6i', *values)


def read(raw):
    if not isinstance(raw, bytes) or len(raw) != SIZE or raw[0] not in (0, 1):
        raise ValueError('Exact28-byte descriptor and canonical active byte required')
    return {'IsActive': bool(raw[0]), **dict(zip(INTEGER_FIELDS, struct.unpack_from('<6i', raw, 4)))}


def matches(raw, descriptor):
    return encode(descriptor, reserved=raw[1:4]) == raw and read(raw) == descriptor
