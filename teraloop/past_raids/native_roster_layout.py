"""Pinned native copy layout, not generated Pokemon/NPC initialization."""
import hashlib
import struct

BODY_SIZE = 0xaa0
PK9_SIZE = 0x158
SCALAR_OFFSET = 5 * PK9_SIZE
OPAQUE_OFFSET = 0x6d8
OPAQUE_SIZE = 0x3c8
OBJECT_REGION_OFFSET = 0x58
OBJECT_REGION_SIZE = BODY_SIZE - SCALAR_OFFSET
OBSERVED_SEED_OFFSET = 2704


def inspect_body(raw):
    if not isinstance(raw, bytes) or len(raw) != BODY_SIZE:
        raise ValueError('Exact native2720-byte decompressed body required')
    return {'body_size': len(raw), 'pk9_offsets': [i * PK9_SIZE for i in range(5)],
        'scalar_block_offset': SCALAR_OFFSET, 'scalar_block_size': 32,
        'scalar_block_sha256': hashlib.sha256(raw[SCALAR_OFFSET:OPAQUE_OFFSET]).hexdigest(),
        'opaque_block_offset': OPAQUE_OFFSET, 'opaque_block_size': OPAQUE_SIZE,
        'opaque_block_sha256': hashlib.sha256(raw[OPAQUE_OFFSET:]).hexdigest(),
        'seed_candidate_offset': OBSERVED_SEED_OFFSET,
        'seed_candidate_u64_le': struct.unpack_from('<Q', raw, OBSERVED_SEED_OFFSET)[0],
        'source_object_seed_candidate_offset': OBJECT_REGION_OFFSET + OBSERVED_SEED_OFFSET - SCALAR_OFFSET,
        'scalar_semantics_verified': False, 'opaque_semantics_verified': False,
        'complete_initialization_generated': False, 'host_integrated': False}


def project_copy_fixture(pk9_regions, object_region):
    """Invented bytes only: model the copies, without validating/creating PK9."""
    if (not isinstance(pk9_regions, (tuple, list)) or len(pk9_regions) != 5
            or any(not isinstance(p, bytes) or len(p) != PK9_SIZE for p in pk9_regions)
            or not isinstance(object_region, bytes) or len(object_region) != OBJECT_REGION_SIZE):
        raise ValueError('Five344-byte regions and one1000-byte object region required')
    return b''.join(pk9_regions) + object_region
