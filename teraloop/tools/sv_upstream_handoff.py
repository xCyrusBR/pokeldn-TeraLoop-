"""Isolated upstream host: ordinary raids or opt-in measured Mewtwo capsule."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import runpy
import subprocess
import sys
import threading
import _thread

ROOT = Path(__file__).resolve().parents[1]
COMMIT = '92a5bd72445bed3cf260d9f7e6ff9149afe1adf2'


def validate_checkpoint(upstream):
    if (upstream/'.git').exists():
        revision = subprocess.check_output(['git', '-C', str(upstream), 'rev-parse', 'HEAD'], text=True).strip()
        if revision != COMMIT:
            raise ValueError('Upstream revision differs from reviewed checkpoint')
        subprocess.run(['git', '-C', str(upstream), 'diff', '--exit-code', 'HEAD', '--'],
                       check=True, stdout=subprocess.DEVNULL)
        return
    manifest = json.loads((upstream/'CHECKPOINT.json').read_text(encoding='utf-8'))
    if manifest.get('commit') != COMMIT or not manifest.get('files'):
        raise ValueError('Packaged checkpoint differs')
    for name, digest in manifest['files'].items():
        path = (upstream/name).resolve()
        if not path.is_relative_to(upstream.resolve()) or hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            raise ValueError('Packaged upstream file differs: '+name)


def parser():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--upstream', type=Path,
                   default=ROOT if (ROOT/'CHECKPOINT.json').is_file() else ROOT/'lab/upstream-pokeldn-92a5bd7')
    p.add_argument('--pokemon', type=Path, required=True)
    p.add_argument('--pkhex', type=Path, required=True)
    p.add_argument('--seed', default='BD13FB43')
    p.add_argument('--version', choices=('scarlet', 'violet'), default='violet')
    p.add_argument('--map', choices=('paldea', 'kitakami', 'blueberry'), default='paldea')
    p.add_argument('--progress', choices=('beginning', 'tera', '3star', '4star', '5star', '6star'), default='4star')
    p.add_argument('--content', choices=('standard', 'black'), default='standard')
    p.add_argument('--event', type=int, choices=(29,), help='experimental measured Mewtwo capsule; no random event seeds')
    p.add_argument('--event-key', help='hash-verified past-event package key, e.g. 002-002')
    p.add_argument('--encounter', type=int, help='active encounter index within the selected event')
    p.add_argument('--experimental-generated', action='store_true',
                   help='allow source-generated events not yet verified on a physical console')
    p.add_argument('--code', default='6316')
    p.add_argument('--port', default='COM4')
    p.add_argument('--keys', type=Path)
    p.add_argument('--capture', type=Path)
    p.add_argument('--stop-file', type=Path)
    p.add_argument('--seconds', type=int, default=420)
    p.add_argument('--dry-run', action='store_true')
    return p


# The PokéLDN options inspector uses this public parser name.
build_parser = parser


def validate(args):
    if len(args.code) != 4 or not args.code.isascii() or not args.code.isdigit():
        raise ValueError('Local raid code must contain four ASCII digits')
    seed = int(args.seed, 16)
    if args.event and (args.seed != 'BD13FB43' or args.content != 'standard'):
        raise ValueError('Measured event capsule does not support custom seed/content')
    if args.event_key and args.event:
        raise ValueError('Use only one event selector')
    if args.encounter is not None and not args.event_key:
        raise ValueError('Encounter index requires a past event')
    if args.event_key and (args.map != 'paldea' or args.content != 'standard'):
        raise ValueError('Past events use their own delivery configuration')
    if not 0 <= seed <= 0xffffffff:
        raise ValueError('Seed must fit uint32')
    if not 30 <= args.seconds <= 1200:
        raise ValueError('Trial duration must be30..1200 seconds')
    for path in (args.pokemon, args.pkhex):
        if not path.is_file():
            raise ValueError('Pokemon/helper file missing: '+str(path))
    validate_checkpoint(args.upstream)
    if not args.dry_run:
        if not args.keys or not args.keys.is_file() or not args.capture or not args.stop_file:
            raise ValueError('Live test requires own keys, fresh capture and stop-file paths')
        if args.capture.exists() or args.stop_file.exists():
            raise ValueError('Never reuse an existing capture/stop path')
    return seed


def command(args):
    return [str(args.upstream/'bin/sv_host.py'), '--raid-seed', args.seed,
            '--raid-pokemon', str(args.pokemon.resolve()), '--raid-version', args.version,
            '--raid-map', args.map, '--raid-progress', args.progress, '--raid-content', args.content,
            '--channel', '6', '--scene-id', '7', '--max-participants', '4', '--code', args.code,
            '--scarlet-response', '--session-flags', '0', '--session-packet-id', '1',
            '--no-session-ack', '--join-seq', '0', '--update-seq', '0', '--update-delay', '0.02',
            '--rtt-probe', '--clock', '--net-stations', '4', '--record-delay', '0.1',
            '--record-spacing', '0.003', '--host-player-id', '00000000000000010000000000000000',
            '--host-player-name', 'Chronos', '--seconds', str(args.seconds),
            '--keys', str(args.keys.resolve()), '--capture', str(args.capture.resolve())]


def main():
    args = parser().parse_args()
    seed = validate(args)
    inherited_radio = os.environ.get('POKELDN_RADIO', '')
    if args.port == 'auto' and inherited_radio.startswith('esp32:'):
        args.port = inherited_radio[len('esp32:'):]
    os.environ.pop('POKELDN_RADIO', None)
    os.environ.pop('POKELDN_ESP32_TRACE', None)
    os.environ['POKELDN_PKHEX'] = str(args.pkhex.resolve())
    os.environ.setdefault('POKELDN_DATA', str(Path(os.environ.get('APPDATA', Path.home()))/'TeraLoop-PokeLDN'))
    # Source only: do not import the release's Python313 DLLs into Python314.
    sys.path = [str(args.upstream), str(args.upstream/'vendor/LDN')] + [
        path for path in sys.path if 'pokeldn-research' not in path
        and (getattr(sys, 'frozen', False) or '_internal' not in path)]
    from pokeldn import pokemon as service, gen9
    from pokeldn.sv import raid, raid_encounter
    sys.path.insert(0, str(ROOT))
    from past_raids.ready_gate import install as install_ready_gate
    install_ready_gate(raid)
    # Legality check does not rewrite the input PK9 or open the serial port.
    checked = service.SERVICE.check_bytes('sv', args.pokemon.read_bytes())
    if not checked.get('legal'):
        raise ValueError('Host Pokemon did not pass upstream PKHeX legality check')
    metadata = {}
    selected = None
    if args.event_key:
        sys.path.insert(0, str(ROOT))
        from past_raids.event_selector import select
        names = {row['id']: row['name'] for row in service.SERVICE.species('sv')}
        selected = select(args.event_key, gen9, names, version=args.version, index=args.encounter)
        if selected.catalog['number'] == 29 and selected.species == 150:
            if args.seed != 'BD13FB43':
                raise ValueError('Validated Mewtwo checkpoint uses its measured seed')
            args.event = 29
        elif not args.dry_run and not args.experimental_generated:
            raise ValueError('Generated event requires experimental opt-in until console validation')
    if args.event:
        sys.path.insert(0, str(ROOT))
        from past_raids.upstream_mewtwo_capsule import install
        from pokeldn.sv import streams
        reference = ROOT/'distribution/mewtwo-native-capsule.bin'
        if not reference.exists():
            reference = ROOT/'lab/eden-exact-ironhands-actions-decoded-20260930.jsonl'
        found, metadata = install(raid, raid_encounter, gen9, streams,
            reference=reference,
            event_root=ROOT/'source-materials/mewtwo-event', version=args.version,
            map_name=args.map, progress=args.progress)
        seed = found.seed
        args.seed = f'{seed:08X}'
    elif selected is not None:
        from past_raids.event_generation import generate, install
        found = generate(seed, selected.package, selected.rule, raid_encounter, gen9, names,
                         version=args.version)
        install(found, raid, raid_encounter, gen9)
        metadata = {'event_key': args.event_key, 'encounter': selected.index,
                    'boss_source': 'source-generated event PK9', 'seed_configurable': True,
                    'live_verified': False, 'unknown_point_words_zero': True,
                    'battle_snapshots_replayed': False}
    else:
        found = raid_encounter.generate(seed, args.version, args.map, args.progress, args.content)
    host = args.pokemon.read_bytes()
    # The player's current selection is read by RaidHost; no captured scene/snapshot.
    stage = raid.RaidHost(found, host)
    whole = raid.bootstrap(found, (host,))
    assert len(whole) == 2720 and stage.guest is None
    print(json.dumps({'upstream': COMMIT, 'seed': f'{seed:08X}', 'species': found.species,
                      'stars': found.stars, 'bootstrap_bytes': len(whole), 'host_legal': True,
                      'past_event_generation_supported': True, 'all_events_live_verified': False,
                      'radio_opened': False,
                      'experimental_capsule': metadata}), flush=True)
    if args.dry_run:
        return 0
    os.environ['POKELDN_RADIO'] = 'esp32:'+args.port
    # Keep the installed universal firmware's conservative serial rate; no flash.
    os.environ['POKELDN_ESP32_BAUD'] = '115200'
    stop_event = threading.Event()
    def watch_stop():
        while not stop_event.wait(0.25):
            if args.stop_file.exists():
                print('[upstream trial] stop requested', flush=True)
                _thread.interrupt_main()
                return
    threading.Thread(target=watch_stop, daemon=True).start()
    sys.argv = command(args)
    try:
        runpy.run_path(sys.argv[0], run_name='__main__')
    finally:
        stop_event.set()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
