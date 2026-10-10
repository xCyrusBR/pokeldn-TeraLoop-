"""Offline projection of the inspected kind1/9 command converter.

Internal 0x8c-byte commands are NOT Pia messages, snapshots, or results.
Target resolution requires caller-supplied current game context. Nothing here
opens a radio, computes damage, schedules actors, or marks an action resolved.
"""
from dataclasses import dataclass, field
import struct
from .sv_action_record import decode


def _uint(value, bits, name):
    if type(value) is not int or not 0 <= value < 1 << bits:
        raise ValueError(f'{name} must be an unsigned {bits}-bit integer')
    return value


@dataclass(frozen=True)
class CommandProjection:
    internal_kind: int
    context_group: int
    assigned_counter: int
    next_counter: int
    internal_bytes: bytes = field(repr=False)

    def metadata(self):
        return dict(internal_kind=self.internal_kind, context_group=self.context_group,
                    assigned_counter=self.assigned_counter, next_counter=self.next_counter,
                    internal_bytes=len(self.internal_bytes), wire_message=False,
                    resolved_outcome=False)


def project(record, *, context_group, counter, resolve_target=None):
    """Project only the inspected converter fields, without executing them.

    `context_group` is the snapshot group passed as w3, NOT a lobby seat.
    Move target lookup is mandatory; never infer an actor from target code4.
    A returned target of zero is permitted by the inspected lookup path.
    Counter is supplied by context, independent of padding and reliable IDs.
    """
    action = decode(record)
    _uint(context_group, 8, 'context group')
    if context_group > 4:
        raise ValueError('only inspected snapshot contexts0..4 supported')
    _uint(counter, 32, 'counter')
    assigned = counter or 1
    out = bytearray(0x8c)
    struct.pack_into('<I', out, 0, action.actor_identifier)
    struct.pack_into('<I', out, 0x54, assigned)
    struct.pack_into('<I', out, 0x58, 0x20)
    struct.pack_into('<I', out, 0x84, 0x5400000)
    out[0x88] = context_group
    if action.kind == 1:
        if not callable(resolve_target):
            raise ValueError('move requires explicit context-aware target resolver')
        target = _uint(resolve_target(action.target_code, context_group), 32, 'target actor')
        internal_kind = 1
        struct.pack_into('<I', out, 0xc, target)
        struct.pack_into('<H', out, 0x10, action.move_id)
        out[8] = action.target_code
        out[0x12] = action.flag_bit25
    else:
        internal_kind = 10
        out[0x25] = action.cheer_selector
    struct.pack_into('<I', out, 4, internal_kind)
    return CommandProjection(internal_kind, context_group, assigned,
                             (assigned + 1) & 0xffffffff, bytes(out))
