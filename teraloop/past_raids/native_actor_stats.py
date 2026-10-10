"""Native stat coefficient arithmetic, not encounter generation or move logic.

Observed HP/stat coefficients are tenths. The native destination is unsigned
16-bit, so preserve truncation rather than silently applying a gameplay clamp.
"""


def scaled_actor_stat(base, coefficient, *, hp=False):
    limit = 65535 if hp else 255
    if (type(base) is not int or not 0 <= base <= 65535 or
            type(coefficient) is not int or not 0 <= coefficient <= limit):
        raise ValueError('Native stat/coefficient outside inspected input width')
    return (base * coefficient // 10) & 65535


def write_stat_coefficient(fields, native_stat_id, value):
    """Literal 0x171cac8 field write, not its caller's HP/stat refresh logic.

    Native selector uses low eight bits; values above five are a no-op.
    HP is uint16 and other coefficients uint8. No Pokemon/event inference.
    """
    if not isinstance(fields, (bytes, bytearray)) or len(fields) != 7:
        raise ValueError('Coefficient field block must be seven bytes')
    if any(type(v) is not int or not 0 <= v <= 0xffffffff
           for v in (native_stat_id, value)):
        raise ValueError('Native selector/value must be unsigned 32-bit')
    result = bytearray(fields)
    selector = native_stat_id & 255
    if selector == 0:
        result[:2] = (value & 65535).to_bytes(2, 'little')
    elif selector <= 5:
        result[selector + 1] = value & 255
    return bytes(result)


def runtime_hp_scale_to_coefficient(raw_scale):
    """0xf9ffb4 arithmetic only; caller skips its update when raw scale is zero.

    Source is a runtime uint16 field. Binding it to an event schema still
    requires proving the upstream producer, not guessing from matching values.
    """
    if type(raw_scale) is not int or not 0 <= raw_scale <= 65535:
        raise ValueError('Runtime HP scale must be unsigned 16-bit')
    return raw_scale // 10


def project_coefficient_refresh(fields, native_stat_id, value, base_hp, maximum, current):
    """Literal 0x2899cec wrapper with inspected HP callbacks, offline only.

    base_hp substitutes the entity's stat getter; generating that entity is
    NOT implemented here. Non-HP writes deliberately do not refresh HP.
    """
    if any(type(v) is not int or not 0 <= v <= 65535 for v in (base_hp, maximum, current)):
        raise ValueError('Base/current/maximum HP must be unsigned 16-bit')
    if current > maximum:
        raise ValueError('Current HP exceeds maximum')
    updated = write_stat_coefficient(fields, native_stat_id, value)
    if native_stat_id & 255:
        return updated, maximum, current
    coefficient = int.from_bytes(updated[:2], 'little')
    new_maximum = scaled_actor_stat(base_hp, coefficient, hp=True)
    if new_maximum > maximum:
        from .native_actor_hp import apply_hp
        current = apply_hp('heal', new_maximum, current, new_maximum - maximum)
    elif new_maximum < maximum and current > new_maximum:
        # Wrapper stores the new maximum BEFORE damage. Its transient current
        # may exceed that maximum, outside apply_hp's ordinary input contract.
        current = new_maximum
    return updated, new_maximum, current
