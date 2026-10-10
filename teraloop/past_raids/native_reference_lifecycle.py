"""Compare observations grouped by seed, never infer cross-capture identity."""
from past_raids.native_seed_comparison import seed_samples


def reference_samples(report):
    seed_samples(report)  # Apply the same read-only and native-shape guards.
    result = {}
    for candidate in report['candidates']:
        for shape in candidate.get('owner_shape_candidates', []):
            single = dict(report, candidates=[dict(candidate, owner_shape_candidates=[shape])])
            seeds = seed_samples(single)
            if not seeds or shape.get('reference_count_repeated_read_equal') is not True:
                continue
            count = shape.get('reference_count_raw_u32')
            if type(count) is not int or not 0 <= count < 1 << 32:
                raise ValueError('Reference count must be uint32')
            result.setdefault(seeds[0], []).append(count)
    return result


def compare_reference_lifecycle(battle, world, *, world_operator_confirmed=False):
    if not world_operator_confirmed or world.get('world_control_without_actor_requirement') is not True:
        raise ValueError('Explicit guarded world control and operator confirmation required')
    if battle.get('world_control_without_actor_requirement', False) is not False or battle.get('valid_actor_addresses', 0) <= 0:
        raise ValueError('Battle capture must contain guarded actor candidates')
    for field in ('event_number', 'event_array_sha256'):
        if field not in battle or battle[field] != world.get(field):
            raise ValueError('Same hash-verified event required')
    before, after = reference_samples(battle), reference_samples(world)
    if not before or not after:
        raise ValueError('Both captures need guarded repeated reference samples')
    rows = [{'seed': seed, 'battle_reference_samples': before.get(seed, []),
             'world_reference_samples': after.get(seed, [])}
            for seed in sorted(before.keys() | after.keys())]
    return {'event_number': battle['event_number'], 'event_array_sha256': battle['event_array_sha256'],
            'observations_grouped_by_seed': rows, 'world_operator_confirmed': True,
            'cross_capture_object_identity_proven': False,
            'active_configuration_owner_proven': False, 'host_integrated': False,
            'limitation': 'Counts are grouped by seed, not object identity; scan bounds, retained copies and seed collisions prevent an active-owner inference.'}
