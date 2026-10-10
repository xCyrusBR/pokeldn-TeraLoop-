"""Require the real console's Ready before starting; leave pinned upstream intact."""


def install(raid):
    original = raid.RaidHost
    if getattr(original, '_teraloop_ready_gate', False):
        return original

    class ReadyHost(original):
        _teraloop_ready_gate = True

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.guest_ready = False

        def on_message(self, payload, now):
            state = raid.state_of(bytes(payload))
            if 10 not in self.sent:
                if state == raid.STATE_READY:
                    self.guest_ready = True
                elif state == raid.STATE_IDLE or raid.pokemon_of(bytes(payload)) is not None:
                    self.guest_ready = False
            super().on_message(payload, now)

        def _ready(self, seq, now):
            if seq == 10 and not self.guest_ready:
                return False
            return super()._ready(seq, now)

    raid.RaidHost = ReadyHost
    return ReadyHost
