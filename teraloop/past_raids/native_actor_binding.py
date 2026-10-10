"""Read-only projection of the inspected property16 actor-slot permutation.

SV4.0.0 0x114e7ec calls 0x114e98c before serializing key0x16.
0x114ea98 swaps pointer slots when destination != source. This projection
does NOT execute the actor's virtual methods or subsequent registry updates.
It must not be mistaken for a complete first-scene state executor.
"""
from dataclasses import dataclass
from .sv_initialization_context import unpack_property16


@dataclass(frozen=True)
class ActorBinding:
    group: int
    destination_slot: int
    source_slot: int
    unresolved_value: int

    @classmethod
    def read(cls, payload):
        return cls(*unpack_property16(payload))


def project_slot_order(payload, groups):
    """Return the slot permutation only, leaving every supplied group untouched.

The inspected context has five group arrays at stride0x38, six pointer slots
per group. Values are opaque tokens supplied by the analysis caller, not PK9
bytes or actor IDs. The final 16-bit field is deliberately not executed.
"""
    binding = ActorBinding.read(payload)
    if len(groups) != 5 or any(len(row) != 6 for row in groups):
        raise ValueError('Projection requires five groups of six opaque slots')
    if binding.group >= 5 or binding.destination_slot >= 6 or binding.source_slot >= 6:
        raise ValueError('Binding addresses a slot outside the inspected context')
    result = [list(row) for row in groups]
    row = result[binding.group]
    dst, src = binding.destination_slot, binding.source_slot
    row[dst], row[src] = row[src], row[dst]
    return tuple(tuple(row) for row in result)
