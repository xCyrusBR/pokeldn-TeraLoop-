"""Launch PokéLDN with the additive TeraLoop past-event tool (no source edits)."""
import argparse
import json
import os
from pathlib import Path
import sys

ROOT = Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parents[1]))
UPSTREAM = ROOT if (ROOT/'CHECKPOINT.json').is_file() else ROOT/'lab/upstream-pokeldn-92a5bd7'


def main():
    sys.path[:0] = [str(ROOT), str(ROOT/'lab/teraloop-gui-deps'), str(UPSTREAM), str(UPSTREAM/'vendor/LDN')]
    os.environ.setdefault('POKELDN_DATA', str(Path(os.environ.get('APPDATA', Path.home()))/'TeraLoop-PokeLDN'))
    if getattr(sys, 'frozen', False):
        from pokeldn.app import paths
        paths.ROOT = str(UPSTREAM)
    if len(sys.argv) > 2 and sys.argv[1] in ('--run', '--module'):
        from pokeldn.app.runner import child
        child(sys.argv[1:])
        return 0
    os.environ.pop('POKELDN_RADIO', None)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pkhex', type=Path, default=os.environ.get('POKELDN_PKHEX'))
    parser.add_argument('--check-installation', action='store_true',
                        help='Check packaged GUI/catalogue/helper without opening a window or radio')
    args = parser.parse_args()
    from pokeldn import pokemon
    helper = args.pkhex or Path(pokemon._command()[-1])
    if not helper.is_file():
        raise ValueError('Choose an existing PKHeX helper with --pkhex')
    os.environ['POKELDN_PKHEX'] = str(helper.resolve())
    # These editable app settings are isolated from the user's original PokéLDN.
    from pokeldn.app import paths, runner
    from past_raids.pokeldn_event_ui import install
    install(helper)
    original_command = runner.command
    def child_command(*argv, bluetooth=False):
        if bluetooth:
            return original_command(*argv, bluetooth=bluetooth)
        if getattr(sys, 'frozen', False):
            return [sys.executable, *argv]
        return [sys.executable, '-u', str(Path(__file__).resolve()), *argv]
    runner.command = child_command
    from gui import main as gui
    # The fork must not replace itself with an unextended upstream update or
    # delete another Flet build's viewer cache on launch.
    gui.flet_client.prune_cache = lambda: []
    gui.App.check_update = lambda self: None
    viewer = UPSTREAM/'gui/client/windows/flet/flet.exe'
    if viewer.is_file():
        os.environ['FLET_VIEW_PATH'] = str(viewer.parent)
    from past_raids.keys_dialog import install as install_keys_dialog
    install_keys_dialog(gui)
    original_main = gui.main
    def page_main(page):
        original_main(page)
        page.title = 'PokéLDN + TeraLoop'
        page.window.icon = str(UPSTREAM/'gui/assets/icon.ico')
        page.update()
    gui.main = page_main
    if args.check_installation:
        from past_raids.event_selector import catalog
        from tools.sv_upstream_handoff import validate_checkpoint
        from pokeldn.app.catalog import GAMES
        validate_checkpoint(UPSTREAM)
        entries = catalog()
        assert any(t.key == 'sv-teraloop-host' for g in GAMES if g.key == 'sv' for t in g.tools)
        assert pokemon.SERVICE.check('sv', str(ROOT/'lab/host-mew.pk9'))['legal']
        print(json.dumps({'events': len({e['number'] for e in entries}), 'packages': len(entries),
                          'gui_imports': True, 'helper_legal_check': True, 'radio_opened': False}), flush=True)
        return 0
    gui.run()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
