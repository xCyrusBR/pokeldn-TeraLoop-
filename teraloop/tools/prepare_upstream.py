"""Fetch the exact tested upstream and optionally reuse public official assets."""
import argparse
from pathlib import Path
import shutil
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[1]
COMMIT = '92a5bd72445bed3cf260d9f7e6ff9149afe1adf2'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reference-release', type=Path)
    args = parser.parse_args()
    target = ROOT / 'lab/upstream-pokeldn-92a5bd7'
    if not target.exists():
        target.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(['git', 'init', str(target)], check=True)
        subprocess.run(['git', '-C', str(target), 'fetch', '--depth', '1',
                        'https://github.com/Decryptu/pokeldn.git', COMMIT], check=True)
        subprocess.run(['git', '-C', str(target), 'checkout', '--detach', 'FETCH_HEAD'], check=True)
    revision = subprocess.check_output(['git', '-C', str(target), 'rev-parse', 'HEAD'], text=True).strip()
    if revision != COMMIT:
        raise ValueError('Existing checkout differs; preserve it and use a fresh folder')
    subprocess.run(['git', '-C', str(target), 'diff', '--exit-code', 'HEAD', '--'], check=True)
    if args.reference_release:
        internal = args.reference_release.resolve() / '_internal'
        helper = internal / 'services/pkhex/dist/pokeldn-pkhex.exe'
        viewer_zip = internal / 'flet_desktop/app/flet-windows.zip'
        firmware = internal / 'gui/firmware'
        if not helper.is_file() or not viewer_zip.is_file() or not firmware.is_dir():
            raise ValueError('Reference must be an extracted official Windows release with helper/viewer/firmware')
        helper_target = target / 'services/pkhex/dist'
        helper_target.mkdir(parents=True, exist_ok=True)
        shutil.copy2(helper, helper_target / helper.name)
        shutil.copytree(firmware, target / 'gui/firmware', dirs_exist_ok=True)
        viewer = target / 'gui/client/windows'
        viewer.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(viewer_zip) as archive:
            if any(not (viewer/name).resolve().is_relative_to(viewer.resolve()) for name in archive.namelist()):
                raise ValueError('Unsafe viewer archive')
            archive.extractall(viewer)
        (viewer / 'pokeldn-drop').touch()
    print('Prepared upstream checkpoint:', COMMIT)


if __name__ == '__main__':
    main()
