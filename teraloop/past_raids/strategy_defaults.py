"""Source-linked Discord recommendations; builds are not an NPC action controller."""
from dataclasses import dataclass
import csv
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
SOURCE_BASE = 'https://discord.com/channels/894957576704368680/1107859936848924733/'
NATURES = frozenset('Hardy Lonely Brave Adamant Naughty Bold Docile Relaxed Impish Lax Timid Hasty Serious Jolly Naive Modest Mild Quiet Bashful Rash Calm Gentle Sassy Careful Quirky'.split())
TYPES = ('Normal', 'Fighting', 'Flying', 'Poison', 'Ground', 'Rock', 'Bug', 'Ghost',
         'Steel', 'Fire', 'Water', 'Grass', 'Electric', 'Psychic', 'Ice', 'Dragon', 'Dark', 'Fairy', 'Stellar')


@dataclass(frozen=True)
class StrategyDefault:
    boss: str
    stars: int
    boss_tera: str
    message_id: str
    pokemon: str
    nature: str
    ability: str
    tera: str
    item: str
    evs: str
    moves: tuple[str, ...]
    role: str

    @property
    def source(self):
        return SOURCE_BASE + self.message_id

    @property
    def key(self):
        return (self.boss, self.stars, self.boss_tera)

    def effort(self):
        result = {}
        for term in self.evs.split('/'):
            match = re.fullmatch(r'\s*(\d+)\s+(HP|Atk|Def|SpA|SpD|Spe)\s*', term)
            if not match or match[2] in result or not 0 <= int(match[1]) <= 252:
                raise ValueError('Invalid or repeated EV field: ' + term)
            result[match[2]] = int(match[1])
        if sum(result.values()) > 510:
            raise ValueError('EV total exceeds 510')
        return result

    def showdown(self):
        """Only documented fields; unspecified ability/Tera remain builder defaults.

        Level 100 is the application's raid policy, not a claim every post says it.
        Unspecified IVs stay at the builder's standard values. Never invent moves.
        """
        lines = [f'{self.pokemon} @ {self.item}', 'Level: 100']
        if self.ability:
            lines.append('Ability: ' + self.ability)
        if self.tera:
            lines.append('Tera Type: ' + self.tera)
        lines.extend(['EVs: ' + self.evs, self.nature + ' Nature'])
        lines.extend('- ' + move for move in self.moves)
        return '\n'.join(lines)


def load(path=ROOT/'distribution/strategy-defaults.tsv'):
    with Path(path).open(encoding='utf-8-sig', newline='') as stream:
        result = []
        keys = set()
        for row in csv.DictReader(stream, delimiter='\t'):
            row['stars'] = int(row['stars'])
            row['moves'] = tuple(row['moves'].split(';'))
            entry = StrategyDefault(**row)
            if entry.key in keys or entry.nature not in NATURES:
                raise ValueError('Duplicate strategy or invalid nature')
            if entry.stars not in (5, 7) or entry.role not in ('solo', 'support'):
                raise ValueError('Invalid recommendation role/stars')
            if entry.boss_tera not in TYPES + ('Random',) or entry.tera not in TYPES + ('',):
                raise ValueError('Invalid Tera type')
            if not entry.message_id.isascii() or not entry.message_id.isdigit():
                raise ValueError('Invalid source message')
            if not 1 <= len(entry.moves) <= 4 or len(set(entry.moves)) != len(entry.moves):
                raise ValueError('Invalid moveset')
            if any(not move or '\n' in move for move in entry.moves):
                raise ValueError('Invalid move name')
            entry.effort()
            keys.add(entry.key)
            result.append(entry)
    return tuple(result)


def find(boss, stars, tera, defaults=None):
    entries = load() if defaults is None else defaults
    return next((e for e in entries if e.boss == boss and e.stars == stars
                 and e.boss_tera in (tera, 'Random')), None)
