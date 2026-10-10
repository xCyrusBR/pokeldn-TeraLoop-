"""Mewtwo-only team plan and offline DPS decisions, not a Pia battle adapter."""
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from uuid import UUID, uuid5

MEWTWO_EVENT = 20230901
NAMESPACE = UUID("b9591980-877e-4bfc-a222-66aa3ac450ef")


@dataclass(frozen=True)
class SyntheticTrainer:
    name: str
    seat: int
    logical_player_id: str
    pokemon: Path


def load_team(manifest_path, event_identifier, boss):
    """Reject extra synthetic trainers for every other event/raid."""
    if (event_identifier, boss.species, boss.difficulty, boss.event_no) != (
            MEWTWO_EVENT, 150, 7, 2023090101):
        raise ValueError("PR2/PR3 are enabled only for this seven-star Mewtwo event")
    manifest_path = Path(manifest_path).resolve()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    rows = manifest["trainers"]
    if [(row["name"], row["battle_seat"]) for row in rows] != [("PR", 0), ("PR2", 2), ("PR3", 3)]:
        raise ValueError("expected PR/PR2/PR3 in independent seats 0/2/3")
    if manifest["physical_guest"] != {"battle_seat": 1, "role": "support"}:
        raise ValueError("physical support must retain seat 1")
    team = []
    for row in rows:
        pokemon = (manifest_path.parent / row["pokemon"]).resolve()
        if pokemon.parent != manifest_path.parent or pokemon.suffix != ".pk9":
            raise ValueError("Pokemon file must belong to this private team directory")
        data = pokemon.read_bytes()
        if len(data) != 344 or hashlib.sha256(data).hexdigest() != row["sha256"]:
            raise ValueError("team Pokemon differs from validated build manifest")
        # Logical UUIDs are not wire station IDs, trainer TID/SID or an admission.
        identity = uuid5(NAMESPACE, f"{MEWTWO_EVENT}:{row['name']}").hex
        team.append(SyntheticTrainer(row["name"], row["battle_seat"], identity, pokemon))
    return tuple(team)


@dataclass(frozen=True)
class BattleObservation:
    hp: int
    max_hp: int
    attack_stage: int
    boss_sp_attack_stage: int
    tera_charge: int
    terastallized: bool
    move_pp: dict
    can_act: bool = True
    connected: bool = True


@dataclass(frozen=True)
class Decision:
    kind: str
    move: str | None = None
    tera: bool = False
    reason: str = ""


class DpsPolicy:
    """One independent policy per trainer, advanced only by resolved moves.

    Neither a transport ACK nor selecting/sending a move completes an action.
    Missing decoded observation prevents issuing an instruction. Once the
    synthetic station disconnects this policy cannot control replacement AI.
    """
    def __init__(self):
        self.opening_bugs = 0
        self.reset_bugs = 0
        self.last_attack_stage = None
        self.pending = None

    def decide(self, state):
        if state is None:
            return Decision("wait", reason="decoded battle state unavailable")
        if not state.connected:
            return Decision("wait", reason="synthetic controller disconnected")
        if not state.can_act or state.hp <= 0:
            return Decision("wait", reason="cannot act")
        if state.max_hp <= 0 or not 0 <= state.hp <= state.max_hp:
            raise ValueError("invalid observed HP")
        if not -6 <= state.attack_stage <= 6 or not -6 <= state.boss_sp_attack_stage <= 6:
            raise ValueError("invalid observed stat stages")
        if self.pending is not None:
            return self.pending
        if self.last_attack_stage is not None and state.attack_stage < self.last_attack_stage:
            self.reset_bugs = 2
        self.last_attack_stage = state.attack_stage
        if state.hp * 2 <= state.max_hp:
            return Decision("wait", reason="await physical support heal")
        if self.opening_bugs < 3 or self.reset_bugs:
            move = "StruggleBug"
        elif state.attack_stage < 6:
            move = "SwordsDance"
        elif state.boss_sp_attack_stage > 0:
            move = "StruggleBug"
        else:
            move = "LeechLife"
        if state.move_pp.get(move, 0) <= 0:
            return Decision("wait", reason=f"no confirmed PP for {move}")
        self.pending = Decision("move", move, state.tera_charge >= 3 and not state.terastallized)
        return self.pending

    def resolved(self, move, succeeded=True):
        if self.pending is None or self.pending.move != move:
            raise ValueError("resolution does not match the outstanding action")
        if succeeded and move == "StruggleBug":
            if self.opening_bugs < 3:
                self.opening_bugs += 1
            elif self.reset_bugs:
                self.reset_bugs -= 1
        self.pending = None
