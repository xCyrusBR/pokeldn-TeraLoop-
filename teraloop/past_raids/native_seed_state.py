"""Pinned native seed/state restoration math; not NPC or raid generation."""
MASK64 = (1 << 64) - 1
INITIAL_SECOND_WORD = 0x82A2B175229D6A5B


def step_state(first, second):
    if any(type(x) is not int or not 0 <= x <= MASK64 for x in (first, second)):
        raise ValueError('State words must be uint64')
    mixed = first ^ second
    return ((((first >> 40) | (first << 24)) ^ mixed ^ (mixed << 16)) & MASK64,
            ((mixed >> 27) | (mixed << 37)) & MASK64)


def percentage_roll(first, second, counter, threshold):
    """Native114da8c: increment call counter ONCE, reject draws >=100.

    Threshold is uint32; this leaf does not clamp it. Offline loop bounded.
    Returned steps count underlying transitions, not recorded calls.
    """
    if type(counter) is not int or not 0 <= counter <= MASK64:
        raise ValueError('Counter must be uint64')
    if type(threshold) is not int or not 0 <= threshold < 1 << 32:
        raise ValueError('Threshold must be uint32')
    for steps in range(1, 4097):
        value = (first + second) & 127
        first, second = step_state(first, second)
        if value < 100:
            return value < threshold, (first, second), (counter + 1) & MASK64, steps
    raise ValueError('Percentage rejection exceeded offline step bound')


def bounded_roll(first, second, counter, bound):
    """Native11440f0: uint64 bounded draw, one recorded call per draw."""
    step_state(first, second)  # Validate widths even when no draw is required.
    if any(type(x) is not int or not 0 <= x <= MASK64 for x in (counter, bound)):
        raise ValueError('Counter/bound must be uint64')
    if bound < 2:
        return 0, (first, second), counter, 0
    mask = (1 << (bound - 1).bit_length()) - 1
    for steps in range(1, 4097):
        value = (first + second) & mask
        first, second = step_state(first, second)
        if value < bound:
            return value, (first, second), (counter + 1) & MASK64, steps
    raise ValueError('Bounded rejection exceeded offline step bound')


def inclusive_index_roll(first, second, maximum):
    """Raw state2aa1004, unsigned32 inclusive limit; no call-counter field."""
    if type(maximum) is not int or not 0 <= maximum < 1 << 32:
        raise ValueError('Inclusive limit must be uint32')
    if maximum == (1 << 32) - 1:
        value = (first + second) & 0xffffffff
        return value, step_state(first, second), 1
    value, state, _, steps = bounded_roll(first, second, 0, maximum + 1)
    return value, state, steps


def npc_pool_indices(seed, pool_length):
    """Lua9265: sample three indices without replacement from supplied pool.

    Does not resolve group, pool asset ordering or NPC Pokemon state.
    """
    if type(pool_length) is not int or not 3 <= pool_length <= 65535:
        raise ValueError('A supplied NPC pool must contain3..65535 entries')
    state = restore_state(seed, 0)
    available = list(range(pool_length))
    selected, transitions = [], []
    for _ in range(3):
        index, state, steps = inclusive_index_roll(*state, len(available) - 1)
        selected.append(available.pop(index))
        transitions.append(steps)
    return {'selected_pool_indices': selected, 'final_state_words': list(state),
            'transitions_per_draw': transitions, 'pool_ordering_verified': False,
            'live_selection_verified': False, 'host_integrated': False}


def restore_state(seed, advances):
    if type(seed) is not int or not 0 <= seed <= MASK64:
        raise ValueError('Seed must be uint64')
    if type(advances) is not int or not 0 <= advances <= 4096:
        raise ValueError('Offline restoration limited to 4096 advances')
    first, second = seed, INITIAL_SECOND_WORD
    for _ in range(advances):
        first, second = step_state(first, second)
    return first, second
