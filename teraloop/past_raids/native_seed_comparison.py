"""Compare guarded configuration seed observations, not an RNG implementation."""


def seed_samples(report):
    if (report.get('read_only') is not True or report.get('radio_opened') is not False
            or report.get('host_integrated') is not False
            or not isinstance(report.get('candidates'), list)):
        raise ValueError('A guarded read-only configuration report is required')
    samples = []
    for candidate in report['candidates']:
        if (candidate.get('all_13_scalars_match') is not True or
                candidate.get('repeated_read_equal') is not True):
            continue
        for shape in candidate.get('owner_shape_candidates', []):
            if (shape.get('embedding_hypothesis') != 'runtime_default_config' or
                    shape.get('vtable_offset') != '0x44ff070' or
                    shape.get('relocated_method_verified') is not True or
                    shape.get('hp_refresh_branch_flag_bit2') is not True or
                    shape.get('seed_repeated_read_equal') is not True):
                continue
            seed = shape.get('configuration_seed_raw_u64')
            if type(seed) is not int or not 0 <= seed < 1 << 64:
                raise ValueError('Configuration seed must be uint64')
            samples.append(seed)
    return samples


def compare_seed_reports(before, after, *, separate_sessions_confirmed=False):
    if not separate_sessions_confirmed:
        raise ValueError('Separate game sessions must be confirmed by the operator')
    for field in ('event_number', 'event_array_sha256'):
        if field not in before or before[field] != after.get(field):
            raise ValueError('Same hash-verified event required for seed comparison')
    first, second = seed_samples(before), seed_samples(after)
    if not first or not second:
        raise ValueError('Both reports need a guarded runtime-shaped seed candidate')
    a, b = sorted(set(first)), sorted(set(second))
    unambiguous = len(a) == len(b) == 1
    return {'event_number': before['event_number'],
            'event_array_sha256': before['event_array_sha256'],
            'before_seed_samples': first, 'after_seed_samples': second,
            'before_distinct_seeds': a, 'after_distinct_seeds': b,
            'one_distinct_seed_per_capture': unambiguous,
            'observed_seed_changed': a[0] != b[0] if unambiguous else None,
            'new_seed_values': sorted(set(b) - set(a)),
            'separate_sessions_operator_confirmed': True,
            'active_configuration_owner_proven': False,
            'every_session_reseeds_proven': False, 'npc_rng_decoded': False,
            'network_seed_encoding_verified': False, 'host_integrated': False,
            'limitation': 'Two user-confirmed sessions and structural native candidates; not proof of active-owner identity, RNG algorithm or a universal reseeding rule.'}
