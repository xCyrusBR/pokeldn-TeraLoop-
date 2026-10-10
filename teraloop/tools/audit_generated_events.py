"""Offline event PK9/RaidPoint audit. Does not claim console compatibility."""
import argparse
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--pkhex', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    if args.output.exists():
        raise ValueError('Fresh audit path required')
    os.environ.pop('POKELDN_RADIO', None)
    os.environ['POKELDN_PKHEX'] = str(args.pkhex.resolve())
    upstream = ROOT/'lab/upstream-pokeldn-92a5bd7'
    sys.path[:0] = [str(ROOT), str(upstream), str(upstream/'vendor/LDN')]
    from pokeldn import gen9, pokemon
    from pokeldn.sv import raid, raid_encounter, streams
    from past_raids.event_selector import catalog, selections
    from past_raids.event_generation import generate, raid_point
    from past_raids.upstream_mewtwo_capsule import native_bootstrap
    names = {r['id']: r['name'] for r in pokemon.SERVICE.species('sv')}
    pokemon.SERVICE.close()
    rows = []
    for event in catalog():
        key = Path(event['package']).name
        for selected in selections(key, gen9, names):
            try:
                version = 'scarlet' if selected.rule['RomVer'] == 1 else 'violet'
                found = generate(0x7885b54c, selected.package, selected.rule, raid_encounter,
                                 gen9, names, version=version)
                raw = raid.boss_record(found)
                checked = gen9.read(gen9.load(raw))
                for field, value in found.boss.items():
                    if checked[field] != value:
                        raise ValueError('PK9 roundtrip changed '+field)
                point = raid_point(found, raid, gen9)
                if len(point) != 1000:
                    raise ValueError('Wrong RaidPoint length')
                rows.append({'key': selected.key, 'boss': selected.boss, 'stars': found.stars,
                             'generated': True, 'rewards': len(found.rewards)})
            except Exception as error:
                rows.append({'key': selected.key, 'boss': selected.boss,
                             'generated': False, 'error': str(error)})
    mewtwo = next(s for e in catalog() if e['number'] == 29
                   for s in selections(Path(e['package']).name, gen9, names)
                   if s.species == 150)
    generated = generate(0x7885b54c, mewtwo.package, mewtwo.rule, raid_encounter, gen9, names)
    native = native_bootstrap(ROOT/'distribution/mewtwo-native-capsule.bin', raid, streams)
    boss_matches = raid.boss_record(generated) == native[1376:1720]
    if not boss_matches:
        raise ValueError('Source-generated Mewtwo differs from measured boss')
    report = {'encounters': rows, 'mewtwo_boss_matches_native_bytes': boss_matches,
              'live_event_coverage_verified': False, 'radio_opened': False}
    args.output.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({'encounters': len(rows), 'generated': sum(r['generated'] for r in rows),
        'mewtwo_boss_matches_native_bytes': boss_matches,
        'failures': [r for r in rows if not r['generated']]}))


if __name__ == '__main__':
    main()
