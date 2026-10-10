"""Package the additive event UI without modifying the pinned source or keys.

Reuses a local, official PokéLDN release's legal helper and Flet viewer. Never
copies its keys, settings, saves or captures. No .NET/Flutter compilation or
Windows security mitigation changes are performed.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
UPSTREAM = ROOT/'lab/upstream-pokeldn-92a5bd7'


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--reference-release', type=Path, required=True)
    p.add_argument('--name', default='PokeLDN-TeraLoop',
                   help='Release folder/executable name; use a new name to preserve a running build')
    p.add_argument('--standard-layout', action='store_true',
                   help='Put upstream bin/gui/services/vendor directly in _internal, like the official release')
    args = p.parse_args()
    if not args.name or any(c not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_' for c in args.name):
        raise ValueError('Unsafe release name')
    sys.path[:0] = [str(ROOT), str(UPSTREAM), str(UPSTREAM/'vendor/LDN')]
    from tools.sv_upstream_handoff import validate_checkpoint, COMMIT
    validate_checkpoint(UPSTREAM)
    from pokeldn.sv import raid, streams
    from past_raids.upstream_mewtwo_capsule import native_bootstrap, PUBLIC_CAPSULE_SHA
    stage = ROOT/'artifacts/stage-pokeldn-events-20261010'
    stage.mkdir(parents=True, exist_ok=True)
    snapshot = stage/'lab/upstream-pokeldn-92a5bd7'
    tracked = subprocess.check_output(['git', '-C', str(UPSTREAM), 'ls-files', '-z']).decode().split('\0')
    hashes = {}
    for name in filter(None, tracked):
        source = UPSTREAM/name
        if not source.is_file():
            continue
        target = snapshot/name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        hashes[name] = hashlib.sha256(source.read_bytes()).hexdigest()
    (snapshot/'CHECKPOINT.json').write_text(json.dumps({'commit': COMMIT, 'files': hashes}, indent=2))
    shutil.copytree(ROOT/'past_raids', stage/'past_raids', dirs_exist_ok=True,
                    ignore=shutil.ignore_patterns('__pycache__'))
    (stage/'tools').mkdir(exist_ok=True)
    for name in ('sv_upstream_handoff.py', 'teraloop_pokeldn.py', 'audit_generated_events.py',
                 'audit_event_recommendations.py', 'verify_strategy_builds.py'):
        shutil.copy2(ROOT/'tools'/name, stage/'tools'/name)
    # Catalogue only, not older installer state or private release directories.
    dist = stage/'distribution'
    dist.mkdir(exist_ok=True)
    for name in ('catalog-ready.json', 'event-calendar.json', 'strategy-defaults.tsv', 'gen9-personal-data.json', 'gen9-move-data.json'):
        shutil.copy2(ROOT/'distribution'/name, dist/name)
    shutil.copytree(ROOT/'distribution/events', dist/'events', dirs_exist_ok=True)
    measured = native_bootstrap(ROOT/'distribution/mewtwo-native-capsule.bin', raid, streams)[1376:]
    assert len(measured) == 1344 and hashlib.sha256(measured).hexdigest() == PUBLIC_CAPSULE_SHA
    (dist/'mewtwo-native-capsule.bin').write_bytes(measured)
    shutil.copytree(ROOT/'source-materials/mewtwo-event', stage/'source-materials/mewtwo-event', dirs_exist_ok=True)
    shutil.copy2(ROOT/'lab/host-mew.pk9', stage/'lab/host-mew.pk9')
    helper = args.reference_release/'_internal/services/pkhex/dist/pokeldn-pkhex.exe'
    if not helper.is_file():
        raise ValueError('Official release PKHeX helper missing')
    (snapshot/'services/pkhex/dist').mkdir(parents=True, exist_ok=True)
    shutil.copy2(helper, snapshot/'services/pkhex/dist/pokeldn-pkhex.exe')
    # Existing official radio assets; installer does not run during packaging.
    shutil.copytree(args.reference_release/'_internal/gui/firmware', snapshot/'gui/firmware', dirs_exist_ok=True)
    viewer = snapshot/'gui/client/windows'
    viewer.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(args.reference_release/'_internal/flet_desktop/app/flet-windows.zip') as archive:
        if any(not (viewer/name).resolve().is_relative_to(viewer.resolve()) for name in archive.namelist()):
            raise ValueError('Unsafe viewer archive')
        archive.extractall(viewer)
    (viewer/'pokeldn-drop').touch()
    shutil.copy2(ROOT/'docs/PAST-EVENTS-20261010.md', snapshot/'docs/teraloop-events.md')
    params = [sys.executable, '-m', 'PyInstaller', '--noconfirm', '--onedir', '--console',
              '--hide-console=hide-early', '--name', args.name,
              '--icon', str(UPSTREAM/'gui/assets/icon.ico'),
              '--distpath', str(ROOT/'artifacts/releases'),
              '--workpath', str(ROOT/'artifacts/build-pokeldn-events-20261010'),
              '--specpath', str(ROOT/'artifacts/build-pokeldn-events-20261010'),
              '--paths', str(ROOT), '--paths', str(ROOT/'lab/teraloop-gui-deps'),
              '--paths', str(UPSTREAM), '--paths', str(UPSTREAM/'vendor/LDN'),
              '--add-data', f'{snapshot / "config"};config',
              '--collect-all', 'pokeldn', '--collect-all', 'gui',
              '--collect-all', 'flet', '--collect-all', 'flet_desktop', '--collect-all', 'esptool',
              '--collect-submodules', 'ldn', '--collect-submodules', 'past_raids',
              '--exclude-module', 'flet_cli', '--exclude-module', 'flet_web',
              '--exclude-module', 'PyInstaller', '--exclude-module', 'pytest',
              '--add-data', f'{args.reference_release / "_internal/flet_desktop/app"};flet_desktop/app',
              str(ROOT/'tools/teraloop_pokeldn.py')]
    if args.standard_layout:
        # Flatten only at packaging time: no second heavy staging tree, no
        # edits or moves of the pinned source or the validated old release.
        extra_data = ['--add-data', f'{snapshot};.']
        for folder in ('past_raids', 'tools', 'distribution', 'source-materials'):
            extra_data.extend(['--add-data', f'{stage/folder};{folder}'])
        extra_data.extend(['--add-data', f'{stage/"lab/host-mew.pk9"};lab'])
        params[-1:-1] = extra_data
    else:
        params[-1:-1] = ['--add-data', f'{stage};.']
    env = dict(os.environ)
    env.pop('POKELDN_RADIO', None)
    env['PYTHONPATH'] = os.pathsep.join(map(str, (ROOT, ROOT/'lab/teraloop-gui-deps',
                                               UPSTREAM, UPSTREAM/'vendor/LDN')))
    subprocess.run(params, check=True, cwd=ROOT, env=env)
    output = ROOT/'artifacts/releases'/args.name
    readme = 'STANDARD-RELEASE-LAYOUT-20261010.md' if args.standard_layout else 'PAST-EVENTS-20261010.md'
    shutil.copy2(ROOT/'docs'/readme, output/'README.md')
    print('PACKAGED', output, flush=True)


if __name__ == '__main__':
    main()
