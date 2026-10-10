import subprocess
import sys
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class ReadyGateTests(unittest.TestCase):
    def test_waits_for_ready_and_selection_invalidates_confirmation(self):
        script = r'''
import os,sys
from pathlib import Path
r=Path(sys.argv[1]); u=r/'lab/upstream-pokeldn-92a5bd7'
os.environ.pop('POKELDN_RADIO',None)
sys.path[:0]=[str(u),str(u/'vendor/LDN')]
from pokeldn import gen9
from pokeldn.sv import raid
from past_raids.ready_gate import install
original=raid.RaidHost
cls=install(raid)
assert install(raid) is cls
host=cls.__new__(cls)
host.guest_ready=False; host.sent={9:1.}; host.seen={'guest_lobby':0.};host.accepted_at=0.
host.guest=None
pk=(r/'lab/host-mew.pk9').read_bytes()
host.on_message(raid.pokemon(1,pk),1.)
assert not host._ready(10,60.)
host.on_message(raid.state(2,raid.STATE_READY),60.)
assert host._ready(10,60.)
host.on_message(raid.pokemon(3,pk),61.)
assert not host._ready(10,61.)
host.on_message(raid.state(4,raid.STATE_READY),62.)
host.on_message(raid.state(5,raid.STATE_IDLE),63.)
assert not host._ready(10,63.)
host.on_message(raid.state(6,raid.STATE_READY),64.)
assert host._ready(10,64.)
host.sent[10]=64.
host.on_message(raid.state(7,raid.STATE_STARTED),65.)
assert 'guest_start' in host.seen
assert raid.RaidHost is not original
print('Ready is required, changes clear Ready, start transition unchanged')
'''
        result = subprocess.run([sys.executable, '-c', script, str(ROOT)],
                                capture_output=True, text=True, timeout=30)
        self.assertEqual(0, result.returncode, result.stderr)
