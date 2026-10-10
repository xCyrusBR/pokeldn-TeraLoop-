"""Inspected coefficient-copy block only, NOT a battle-state generator.

SV 4.0.0 at 0x147febc..0x147ff0c copies an input record's seven
coefficient bytes to two actor field ranges. The producer, species bonuses,
event conversion and network serialization are deliberately not inferred here.
"""

INPUT_END = 0x2d
ACTOR_END = 0x3fb
SOURCE = 0x26
DESTINATIONS = (0x3ea, 0x3f4)


def project_actor_coefficient_fields(record, actor):
    """Return a copy; preserve all bytes outside the two inspected ranges."""
    if not isinstance(record, (bytes, bytearray)) or len(record) < INPUT_END:
        raise ValueError('Initialization record does not contain inspected fields')
    if not isinstance(actor, (bytes, bytearray)) or len(actor) < ACTOR_END:
        raise ValueError('Actor buffer does not contain inspected fields')
    result = bytearray(actor)
    coefficients = record[SOURCE:INPUT_END]
    for destination in DESTINATIONS:
        result[destination:destination + 7] = coefficients
    return bytes(result)
