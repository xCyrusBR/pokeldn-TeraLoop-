"""Offline target lookup for the inspected mode2 context only.

Context mode/variant and current actor groups must be supplied explicitly.
These groups are not trainer IDs, PK9 ownership or lobby-seat numbers.
No wire publication or damage calculation is performed.
"""
from .sv_command_projection import _uint

MODE2_GROUPS = (0, 2, 3, 4, 1, 1, 1, 1, 1, 1, 5)


def target_position(code, *, mode, variant):
    _uint(code, 8, 'target code')
    if type(mode) is not int or mode != 2:
        raise ValueError('only inspected mode2 target context supported')
    if type(variant) is not int or variant not in range(4):
        raise ValueError('only inspected variants0..3 supported')
    def group(value):
        if value > 10 or 1 <= value < 4 - variant:
            return 5
        return MODE2_GROUPS[value]
    selected = group(code)
    if selected == 5:
        return 5, 0
    return selected, sum(group(previous) == selected for previous in range(code))


class TargetContext:
    """Private copy of a caller's current actor table; no inferred ownership."""
    def __init__(self, *, mode, variant, actor_groups):
        target_position(0, mode=mode, variant=variant)
        groups = tuple(tuple(group) for group in actor_groups)
        if len(groups) != 5:
            raise ValueError('five explicit actor groups required')
        for group in groups:
            if len(group) > 7:
                raise ValueError('actor group exceeds inspected bound')
            for actor in group:
                _uint(actor, 32, 'actor identifier')
        self.mode, self.variant = mode, variant
        self._groups = groups

    def resolve(self, code, context_group):
        _uint(context_group, 8, 'context group')
        if context_group > 4:
            raise ValueError('context group outside inspected range')
        group, index = target_position(code, mode=self.mode, variant=self.variant)
        if group == 5 or index >= len(self._groups[group]):
            return 0
        return self._groups[group][index]

    def __repr__(self):
        return f'TargetContext(mode={self.mode}, variant={self.variant}, actors=private)'
