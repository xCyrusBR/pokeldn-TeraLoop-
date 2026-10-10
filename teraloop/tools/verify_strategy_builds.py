"""Offline PKHeX validation; never opens a radio or writes an emulator save."""
import argparse
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--upstream', type=Path, default=ROOT/'lab/upstream-pokeldn-92a5bd7')
    p.add_argument('--pkhex', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--boss', default='')
    args = p.parse_args()
    if args.output.exists():
        raise ValueError('Use a fresh report path')
    os.environ.pop('POKELDN_RADIO', None)
    os.environ['POKELDN_PKHEX'] = str(args.pkhex.resolve())
    os.environ['POKELDN_DATA'] = str(ROOT/'artifacts/strategy-build-user-data')
    sys.path[:0] = [str(ROOT), str(args.upstream), str(args.upstream/'vendor/LDN')]
    from pokeldn import pokemon, gen9
    from pokeldn.sv import raid_encounter
    from past_raids.strategy_defaults import load
    from past_raids.strategy_builder import build
    rows = []
    for entry in load():
        if args.boss and entry.boss != args.boss:
            continue
        try:
            result = build(entry, pokemon.SERVICE, gen9, raid_encounter,
                {'ot': 'Chronos', 'tid': 12345, 'sid': 1234, 'language': 2, 'gender': 0}, keep=False,
                seed_file=ROOT/'lab/host-mew.pk9' if entry.pokemon == 'Mew' else None)
            row = {'boss': entry.boss, 'stars': entry.stars, 'legal': True,
                   'source': entry.source, 'pokemon': result['species'],
                   'form': result['form'], 'level': result['level'], 'tera': result['tera']}
        except Exception as error:
            row = {'boss': entry.boss, 'stars': entry.stars, 'legal': False, 'error': str(error)}
        rows.append(row)
        print(json.dumps(row), flush=True)
    pokemon.SERVICE.close()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps({'recommendations': rows, 'radio_opened': False,
        'live_event_coverage_verified': False}, indent=2)+'\n', encoding='utf-8')
    return int(any(not row['legal'] for row in rows))


if __name__ == '__main__':
    raise SystemExit(main())
