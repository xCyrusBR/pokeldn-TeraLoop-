"""Generate and verify one default per encounter, including clearly labelled suggestions."""
import argparse
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pkhex', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError('Fresh output required')
    os.environ.pop('POKELDN_RADIO', None)
    os.environ['POKELDN_PKHEX'] = str(args.pkhex.resolve())
    os.environ['POKELDN_DATA'] = str(ROOT/'artifacts/strategy-build-user-data')
    upstream = ROOT/'lab/upstream-pokeldn-92a5bd7'
    sys.path[:0] = [str(ROOT), str(upstream), str(upstream/'vendor/LDN')]
    from pokeldn import gen9, pokemon
    from pokeldn.sv import raid_encounter
    from past_raids.event_selector import catalog, selections
    from past_raids.event_recommendation import candidates, choose
    from past_raids.strategy_builder import build
    names = {r['id']: r['name'] for r in pokemon.SERVICE.species('sv')}
    pool = candidates(pokemon.SERVICE)
    rows, verified = [], {}
    for event in catalog():
        for selected in selections(Path(event['package']).name, gen9, names):
            try:
                entry, provenance = choose(selected, pokemon.SERVICE, pool=pool)
                unique = entry.showdown()
                if unique not in verified:
                    verified[unique] = build(entry, pokemon.SERVICE, gen9, raid_encounter,
                        {'ot': 'Chronos', 'tid': 12345, 'sid': 1234, 'language': 2, 'gender': 0},
                        keep=False, seed_file=ROOT/'lab/host-mew.pk9' if entry.pokemon == 'Mew' else None)
                rows.append({'key': selected.key, 'boss': selected.boss,
                    'stars': selected.rule['Difficulty'], 'tera': selected.tera,
                    'pokemon': entry.pokemon, 'build': unique, 'legal': True,
                    'provenance': provenance})
            except Exception as error:
                rows.append({'key': selected.key, 'legal': False, 'error': str(error)})
    pokemon.SERVICE.close()
    report = {'event_numbers': len({e['number'] for e in catalog()}),
        'packages': len(catalog()), 'encounters': rows, 'distinct_builds_checked': len(verified),
        'radio_opened': False, 'suggested_solos_not_battle_verified': True}
    args.output.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({'encounters': len(rows), 'legal': sum(r['legal'] for r in rows),
        'distinct_builds_checked': len(verified), 'failures': [r for r in rows if not r['legal']]}))
    return int(any(not r['legal'] for r in rows))


if __name__ == '__main__':
    raise SystemExit(main())
