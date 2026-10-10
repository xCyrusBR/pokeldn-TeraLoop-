import subprocess
import sys
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class KeysDialogTests(unittest.TestCase):
    def test_local_path_success_folder_failure_and_browser_no_upload(self):
        script = r'''
import os, sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch
r=Path(sys.argv[1]);sys.path[:0]=[str(r/'lab/teraloop-gui-deps'),str(r/'lab/upstream-pokeldn-92a5bd7')]
os.environ['POKELDN_GUI_WEB']='8771'
from past_raids.keys_dialog import install
gui=SimpleNamespace();install(gui)
settings=SimpleNamespace(keys='',save=Mock())
page=SimpleNamespace(show_dialog=Mock(),pop_dialog=Mock())
app=SimpleNamespace(settings=settings,page=page,picker=Mock())
gui.welcome(app)
dialog=page.show_dialog.call_args.args[0]
field=dialog.content.content.controls[2]
status=dialog.content.content.controls[3]
assert dialog.actions[1].disabled is True
with patch.object(type(status),'update'):
    field.value=str(r)
    dialog.actions[-1].on_click(None)
    assert not settings.keys and not settings.save.called and not page.pop_dialog.called
    assert 'File not found' in status.value
    # A harmless existing source file stands in for a locally selected path.
    field.value=str(r/'tests/test_keys_dialog.py')
    dialog.actions[-1].on_click(None)
    assert settings.keys==field.value and settings.save.called and page.pop_dialog.called
    assert 'successfully' in page.show_dialog.call_args.args[0].content.value
assert not app.picker.called
print('local path setup verified')
'''
        outcome = subprocess.run([sys.executable, '-c', script, str(ROOT)],
                                 capture_output=True, text=True, timeout=30)
        self.assertEqual(0, outcome.returncode, outcome.stderr)
