"""Bounded projection of the inspected SV 4.0.0 action-record consumer.

Evidence: producer 0x10e1ef8..0x10e1f08 copies 8+4 bytes into a
16-byte slot; converter 0x11461b4..0x11464ac reads no input beyond byte11.
This does not authorize clearing padding on the wire or resolving a move.
Actor identifiers remain private and are never returned by public metadata.
"""
from dataclasses import dataclass, field
import struct


@dataclass(frozen=True)
class ActionRecord:
    kind: int
    actor_identifier: int = field(repr=False)
    target_code: int | None = None
    move_id: int | None = None
    flag_bit25: int | None = None
    cheer_selector: int | None = None
    consumer_bytes: bytes = field(default=b'', repr=False)

    def metadata(self):
        return {key: value for key, value in (
            ('kind', self.kind), ('target_code', self.target_code),
            ('move_id', self.move_id), ('flag_bit25', self.flag_bit25),
            ('cheer_selector', self.cheer_selector)) if value is not None}


def decode(record):
    record = bytes(record)
    if len(record) != 16:
        raise ValueError('complete 16-byte slot required')
    word, _, actor = struct.unpack_from('<III', record)
    kind = word & 15
    if kind == 1:
        return ActionRecord(kind, actor, (word >> 4) & 15,
                            (word >> 8) & 65535, (word >> 25) & 1,
                            consumer_bytes=record[:12])
    if kind == 9:
        return ActionRecord(kind, actor, cheer_selector=(word >> 4) & 255,
                            consumer_bytes=record[:12])
    raise ValueError('only inspected move and cheer projections supported')


def consumer_equivalent(first, second):
    """Conservative 12-byte equality for kind1/9, not outcome equality.

    Even unused bits inside these12 bytes remain significant here, so this
    cannot silently merge different flags, targets, actors or record kinds.
    """
    a, b = decode(first), decode(second)
    return a.consumer_bytes == b.consumer_bytes
