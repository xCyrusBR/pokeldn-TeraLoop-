import subprocess
import sys
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class StandardLayoutTests(unittest.TestCase):
    def test_flat_and_legacy_locations_remain_supported(self):
        script = r'''
from pathlib import Path
import sys,tempfile
r=Path(sys.argv[1])
with tempfile.TemporaryDirectory() as folder:
    flat=Path(folder)
    (flat/'CHECKPOINT.json').write_text('{}')
    sys._MEIPASS=str(flat)
    ns={'__name__':'layout_test','__file__':str(r/'tools/teraloop_pokeldn.py')}
    exec(compile((r/'tools/teraloop_pokeldn.py').read_text(encoding='utf-8'),ns['__file__'],'exec'),ns)
    assert ns['ROOT']==flat and ns['UPSTREAM']==flat
    del sys._MEIPASS
    ns={'__name__':'layout_test','__file__':str(flat/'tools/sv_upstream_handoff.py')}
    exec(compile((r/'tools/sv_upstream_handoff.py').read_text(encoding='utf-8'),ns['__file__'],'exec'),ns)
    assert ns['parser']().parse_args(['--pokemon','x','--pkhex','y']).upstream==flat
    ns={'__name__':'layout_test','__file__':str(r/'tools/sv_upstream_handoff.py')}
    exec(compile((r/'tools/sv_upstream_handoff.py').read_text(encoding='utf-8'),ns['__file__'],'exec'),ns)
    assert ns['parser']().parse_args(['--pokemon','x','--pkhex','y']).upstream==r/'lab/upstream-pokeldn-92a5bd7'
print('Flat portable and legacy paths resolve independently')
'''
        result = subprocess.run([sys.executable, '-c', script, str(ROOT)],
                                capture_output=True, text=True, timeout=30)
        self.assertEqual(0, result.returncode, result.stderr)
