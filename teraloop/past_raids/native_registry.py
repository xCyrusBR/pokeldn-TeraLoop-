"""Literal translation of pinned SV4.0.0 helper0xc9c090.

Inputs are native context fields, NOT station count/lobby slots. Index10 is
returned by unmatched inputs; its game semantics remain unestablished.
"""
TABLE_A = (2, 2, 2, 0, 2)
TABLE_B = (3, 3, 3, 3, 5)


def active_registry_index(mode, variant, group, slot):
    if type(mode) is not int or not 0 <= mode <= 3:
        raise ValueError('Only inspected context modes0..3 are supported')
    if any(type(x) is not int or not 0 <= x <= 255 for x in (variant, group, slot)):
        raise ValueError('Native variant/group/slot must be byte inputs')
    current = slot
    selectors = [0 if mode < 3 else 5,
                 (2 if variant else 5) if mode == 2 else (1 if mode in (0, 1) else 5),
                 (3 if variant >= 2 else 5) if mode == 2 else
                    (TABLE_A[variant - 1] if 1 <= variant <= 5 else 0) if mode == 1 else 5,
                 (4 if variant >= 3 else 5) if mode == 2 else
                    (TABLE_B[variant - 1] if 1 <= variant <= 5 else 1) if mode == 1 else 5]
    for index, selector in enumerate(selectors):
        if selector == group:
            if current & 255 == 0:
                return index
            current = (current - 1) & 0xFFFFFFFF
    last_group = 1 if mode == 2 else 5
    if last_group != group:
        return 10
    remaining = current & 255
    if remaining < 4:
        return (current + 4) & 0xFFFFFFFF
    if remaining == 4:
        return 8
    current = (current - 5) & 0xFFFFFFFF
    return 9 if current & 255 == 0 else 10
