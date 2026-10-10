"""Observed packed boss-descriptor scalar fields, not a full configuration.

Native 16-bit setter family 0x1a15090..0x1a16228. The similarly named
32-bit resource setters and separate override object are NOT this layout.
Unknown extra-action bytes are preserved; no casts, RNG or packets generated.
"""
import struct

SCALAR_FIELDS = (
    ('HpCoef', 0), ('PowerChargeTrigerHp', 2), ('PowerChargeTrigerTime', 4),
    ('PowerChargeLimitTime', 6), ('PowerChargeCancelDamage', 8),
    ('PowerChargePenaltyTime', 10), ('PowerChargePenaltyAction', 12),
    ('PowerChargeDamageRate', 14), ('PowerChargeGemDamageRate', 16),
    ('PowerChargeChangeGemDamageRate', 18), ('DoubleActionTriggerHp', 68),
    ('DoubleActionTriggerTime', 70), ('DoubleActionRate', 72))


def project_boss_scalars(template, descriptor):
    if not isinstance(template, bytes) or len(template) != 74:
        raise ValueError('Native boss descriptor must be exactly 74 bytes')
    values = [descriptor[name] for name, _ in SCALAR_FIELDS]
    if any(type(value) is not int or not -32768 <= value <= 65535 for value in values):
        raise ValueError('Native event scalar outside bounded 16-bit conversion')
    result = bytearray(template)
    for (name, offset), value in zip(SCALAR_FIELDS, values):
        struct.pack_into('<H', result, offset, value & 65535)
    return bytes(result)


def matches_boss_scalars(candidate, descriptor):
    return candidate == project_boss_scalars(candidate, descriptor)
