"""Metadata-only seed correlation; not a raid roster generator."""
import struct


def find_seed_offsets(body, seeds):
    if not isinstance(body, bytes) or len(body) > 1048576:
        raise ValueError('Bounded immutable message required')
    if not isinstance(seeds, (list, tuple)) or not 1 <= len(seeds) <= 256:
        raise ValueError('One to256 candidate seeds required')
    if any(type(s) is not int or not 0 <= s < 1 << 64 for s in seeds):
        raise ValueError('Seeds must be uint64')
    matches = []
    for seed in sorted(set(seeds)):
        needle = struct.pack('<Q', seed)
        offsets = []
        start = 0
        while True:
            offset = body.find(needle, start)
            if offset < 0:
                break
            offsets.append(offset)
            start = offset + 1
        if offsets:
            matches.append({'seed': seed, 'offsets': offsets})
    return matches
