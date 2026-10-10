import unittest
from dataclasses import replace
from past_raids.strategy_defaults import load, find


class StrategyDefaultsTests(unittest.TestCase):
    def test_exactly_one_default_per_encounter(self):
        entries = load()
        self.assertEqual(64, len(entries))
        self.assertEqual(len(entries), len({e.key for e in entries}))
        self.assertTrue(all(e.source.startswith('https://discord.com/channels/') for e in entries))

    def test_image_ursaluna(self):
        e = find('Gimmighoul', 5, 'Psychic')
        self.assertEqual(('Ursaring', 'Ground', 'Guts', 'Toxic Orb'),
                         (e.pokemon, e.tera, e.ability, e.item))
        self.assertEqual(4, e.effort()['SpD'])

    def test_primarina_index_mislabeled_link_resolved_by_content(self):
        self.assertEqual('Vaporeon', find('Primarina', 7, 'Fairy').pokemon)

    def test_form_star_and_tera_are_part_of_match(self):
        self.assertIsNone(find('Decidueye', 7, 'Grass'))
        self.assertIsNotNone(find('Decidueye-Hisui', 7, 'Grass'))
        self.assertIsNone(find('Eevee', 5, 'Normal'))

    def test_mewtwo_support_not_claimed_solo(self):
        e = find('Mewtwo', 7, 'Psychic')
        self.assertEqual('support', e.role)
        self.assertIn('- Life Dew', e.showdown())
        self.assertEqual(508, sum(e.effort().values()))

    def test_no_silent_fill_of_missing_moves_or_tera(self):
        e = find('Mismagius', 5, 'Ghost')
        self.assertEqual(2, e.showdown().count('\n- '))
        self.assertNotIn('Tera Type:', e.showdown())
        self.assertNotIn('Ability:', find('Magikarp', 7, 'Dragon').showdown())

    def test_ev_bounds(self):
        e = load()[0]
        for invalid in ('253 HP', '252 HP / 252 SpA / 252 Def', '4 HP / 8 HP'):
            with self.assertRaises(ValueError):
                replace(e, evs=invalid).effort()


if __name__ == '__main__':
    unittest.main()
