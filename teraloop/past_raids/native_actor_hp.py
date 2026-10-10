"""Literal native actor HP operations for offline analysis, not move resolution.

The native heal comparison truncates to 16 bits BEFORE clamping. Preserve that
behavior even for synthetic inputs that ordinary gameplay may never produce.
"""


def apply_hp(operation, maximum, current, amount=0):
    if operation not in ('damage', 'heal', 'zero'):
        raise ValueError('Unknown HP primitive')
    if any(type(x) is not int or not 0 <= x <= 65535 for x in (maximum, current, amount)):
        raise ValueError('HP primitive inputs must be unsigned 16-bit')
    if current > maximum:
        raise ValueError('Controlled current HP exceeds maximum')
    if operation == 'zero':
        return 0
    if operation == 'damage':
        return max(0, current - amount)
    return min(maximum, (current + amount) & 65535)
