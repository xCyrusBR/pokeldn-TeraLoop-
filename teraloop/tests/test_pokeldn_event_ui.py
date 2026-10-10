import subprocess
import sys
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class EventUIOrderTests(unittest.TestCase):
    def test_extension_preserves_game_order_original_tools_and_icons(self):
        script = r'''
import os,sys,hashlib
from pathlib import Path
r=Path(sys.argv[1]);u=r/'lab/upstream-pokeldn-92a5bd7'
os.environ.pop('POKELDN_RADIO',None)
sys.path[:0]=[str(r/'lab/teraloop-gui-deps'),str(u),str(u/'vendor/LDN')]
from pokeldn.app import catalog
before=catalog.GAMES
from past_raids.pokeldn_event_ui import install
tool=install(r/'unused-helper.exe')
after=catalog.GAMES
assert [g.key for g in after]==[g.key for g in before]
assert [g.key for g in after]==['frlg','lgpe','swsh','bdsp','pla','sv','za']
for old,new in zip(before,after):
    assert (old.name,old.short,old.doc)==(new.name,new.short,new.doc)
    if old.key=='sv':
        assert new.tools[:-1]==old.tools and new.tools[-1] is tool
    else:
        assert new is old
assert (u/'gui/assets/games/sv.png').is_file()
assert (u/'gui/assets/icon.ico').read_bytes()[:4]==bytes.fromhex('00000100')
print('Original game order, tools and icon assets preserved')
'''
        result = subprocess.run([sys.executable, '-c', script, str(ROOT)],
                                capture_output=True, text=True, timeout=30)
        self.assertEqual(0, result.returncode, result.stderr)
