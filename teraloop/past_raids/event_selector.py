"""Hash-verified past-event catalogue; never includes ordinary raid tables."""
from dataclasses import dataclass
from functools import cache
import hashlib
import json
from pathlib import Path

from .event import EventPackage
from .strategy_defaults import TYPES, find

ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class Selection:
    key: str
    package: EventPackage
    catalog: dict
    index: int
    rule: dict
    species: int
    boss: str
    tera: str

    @property
    def label(self):
        p = self.rule['BossPokePara']
        version = {0: '', 1: ' · Scarlet', 2: ' · Violet'}[self.rule['RomVer']]
        return f"{self.boss} · {self.rule['Difficulty']}★ · {self.tera}{version} · #{self.rule['No']}"

    @property
    def recommendation(self):
        return find(self.boss, self.rule['Difficulty'], self.tera)


@cache
def catalog():
    data = json.loads((ROOT/'distribution/catalog-ready.json').read_text(encoding='utf-8'))
    keys = [Path(r['package']).name for r in data]
    if len(keys) != len(set(keys)):
        raise ValueError('Duplicate event package key')
    return tuple(sorted(data, key=lambda r: (r['start'], r['number'], r['package'])))


def package(key):
    base, _, window = key.partition('@')
    entry = next((r for r in catalog() if Path(r['package']).name == base), None)
    if entry is None:
        raise ValueError('Unknown past-event package')
    if window:
        if window not in entry.get('starts', [entry['start']]):
            raise ValueError('Unknown event date window')
        entry = dict(entry, start=window)
    distribution = (ROOT/'distribution').resolve()
    root = (distribution/entry['package']).resolve()
    if not root.is_relative_to(distribution):
        raise ValueError('Event path outside distribution')
    for name, expected in entry['files'].items():
        source = (root/name).resolve()
        if not source.is_relative_to(root) or not source.is_file():
            raise ValueError('Event file missing/outside package')
        if hashlib.sha256(source.read_bytes()).hexdigest() != expected:
            raise ValueError('Event package hash differs: '+name)
    return entry, EventPackage.load(root)


def event_options():
    """Every sourced scheduling window; preserve canonical package keys."""
    out = []
    for entry in catalog():
        base = Path(entry['package']).name
        name = entry['name']
        if entry['number'] == 2:
            name += ' · Round 1'
        elif entry['number'] == 49:
            name += ' · Round 2'
        dates = entry.get('starts', [entry['start']])
        for index, start in enumerate(dates):
            key = base if start == entry['start'] else base+'@'+start
            window_name = name.replace('Round 1', 'Round 2') if entry['number'] == 13 and index else name
            label = f"{start} · #{entry['number']:03d} · {window_name}"
            if len(dates) > 1:
                label += f' · Window {index+1}'
            out.append((start, entry['number'], key, label))
    return tuple((key, label) for _, _, key, label in sorted(out))


def selections(key, gen9, names):
    entry, source = package(key)
    out = []
    for index, rule in enumerate(source.native_rules):
        p = rule['BossPokePara']
        species = gen9.national(p['DevId'])
        name = names.get(species, f'Species {species}')
        if (species, p['FormId']) in ((724, 1), (503, 1), (157, 1)):
            name += '-Hisui'
        elif p['FormId']:
            name += f" (form {p['FormId']})"
        tera = TYPES[p['GemType']-2] if 2 <= p['GemType'] <= 19 else 'Random'
        out.append(Selection(f'{key}:{index}', source, entry, index, rule, species, name, tera))
    return tuple(out)


def select(key, gen9, names, *, version='violet', index=None):
    rows = selections(key, gen9, names)
    compatible = [s for s in rows if s.rule['RomVer'] in (0, 1 if version == 'scarlet' else 2)]
    if index is not None:
        matches = [s for s in compatible if s.index == index]
        if len(matches) != 1:
            raise ValueError('Selected encounter is not available in this event/version')
        return matches[0]
    if not compatible:
        raise ValueError('Event has no encounter for selected game version')
    # The featured highest-star encounter comes first, not a spotlight side raid.
    return max(compatible, key=lambda s: (s.rule['Difficulty'], -s.index))
