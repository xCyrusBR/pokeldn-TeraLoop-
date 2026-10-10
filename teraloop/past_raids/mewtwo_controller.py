"""Protocol-neutral DPS action lifecycle, deliberately not a combat engine.

An adapter must supply complete, decoded outcomes and serialize them for Pia.
This module never treats an ACK, recorded batch, or HP increment as that outcome.
"""
from dataclasses import dataclass
from .mewtwo_team import BattleObservation, Decision, DpsPolicy


@dataclass(frozen=True)
class PlannedAction:
    token: int
    trainer: str
    state_revision: int
    decision: Decision


@dataclass(frozen=True)
class ResolvedAction:
    token: int
    trainer: str
    move: str
    succeeded: bool
    state_revision: int
    observation: BattleObservation


class MewtwoDpsController:
    """Owns independent PR/PR2/PR3 plans for one explicitly scoped session.

    Revision is an adapter's monotonic decoded-state revision, NOT a guessed
    wire counter. No fixed turn count and no autonomous physical-support action.
    Resolve is the only way to advance a policy; duplicate outcome is idempotent.
    """
    def __init__(self, *, event_identifier, species, difficulty, event_no):
        if (event_identifier, species, difficulty, event_no) != (20230901, 150, 7, 2023090101):
            raise ValueError('three DPS controllers are scoped to the Mewtwo event')
        self.policies = {name: DpsPolicy() for name in ('PR', 'PR2', 'PR3')}
        self.observations = {}
        self.pending = {}
        self.completed = {}
        self.next_token = 1

    def observe(self, trainer, revision, state):
        if trainer not in self.policies:
            raise ValueError('only PR/PR2/PR3 may be controlled')
        validate_state(state)
        if not isinstance(revision, int) or isinstance(revision, bool) or revision < 0:
            raise ValueError('invalid decoded-state revision')
        previous = self.observations.get(trainer)
        if previous and revision <= previous[0]:
            if revision == previous[0] and state == previous[1]:
                return False
            raise ValueError('stale or conflicting decoded state')
        self.observations[trainer] = revision, copy_state(state)
        return True

    def plan(self, trainer):
        if trainer not in self.policies:
            raise ValueError('only PR/PR2/PR3 may be controlled')
        observed = self.observations.get(trainer)
        if observed is None:
            return None
        revision, state = observed
        if not state.connected or not state.can_act or state.hp <= 0:
            return None
        if trainer in self.pending:
            return self.pending[trainer]
        decision = self.policies[trainer].decide(state)
        if decision.kind != 'move':
            return None
        plan = PlannedAction(self.next_token, trainer, revision, decision)
        self.next_token += 1
        self.pending[trainer] = plan
        return plan

    def resolve(self, result):
        if not isinstance(result, ResolvedAction):
            raise ValueError('explicit ResolvedAction required, not receipt/ACK')
        validate_state(result.observation)
        previous = self.completed.get(result.token)
        if previous is not None:
            if previous != result:
                raise ValueError('conflicting completed outcome')
            return False
        pending = self.pending.get(result.trainer)
        if pending is None or (pending.token, pending.decision.move) != (result.token, result.move):
            raise ValueError('outcome does not match pending trainer/action')
        if not isinstance(result.succeeded, bool):
            raise ValueError('outcome success must be decoded explicitly')
        current_revision = self.observations[result.trainer][0]
        if result.state_revision <= max(current_revision, pending.state_revision):
            raise ValueError('outcome requires a newer decoded state')
        self.observe(result.trainer, result.state_revision, result.observation)
        self.policies[result.trainer].resolved(result.move, succeeded=result.succeeded)
        del self.pending[result.trainer]
        self.completed[result.token] = ResolvedAction(
            result.token, result.trainer, result.move, result.succeeded,
            result.state_revision, copy_state(result.observation))
        return True


def copy_state(state):
    from dataclasses import replace
    return replace(state, move_pp=dict(state.move_pp))


def validate_state(state):
    if not isinstance(state, BattleObservation):
        raise ValueError('complete decoded BattleObservation required')
    for value in (state.hp, state.max_hp, state.attack_stage,
                  state.boss_sp_attack_stage, state.tera_charge):
        if not isinstance(value, int) or isinstance(value, bool):
            raise ValueError('decoded numeric fields must be integers')
    if any(not isinstance(v, bool) for v in (state.connected, state.can_act, state.terastallized)):
        raise ValueError('decoded flags must be explicit booleans')
    if state.max_hp <= 0 or not 0 <= state.hp <= state.max_hp:
        raise ValueError('invalid decoded HP')
    if not -6 <= state.attack_stage <= 6 or not -6 <= state.boss_sp_attack_stage <= 6:
        raise ValueError('invalid decoded stat stage')
    if not 0 <= state.tera_charge <= 3:
        raise ValueError('invalid decoded tera charge')
    if not isinstance(state.move_pp, dict) or any(
            not isinstance(v, int) or isinstance(v, bool) or v < 0 for v in state.move_pp.values()):
        raise ValueError('invalid decoded PP')
