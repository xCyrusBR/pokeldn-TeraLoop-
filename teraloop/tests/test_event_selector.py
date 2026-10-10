import unittest
from past_raids.event_selector import catalog, package, selections, select, event_options
from past_raids.event_recommendation import effectiveness


class FakeGen9:
    @staticmethod
    def national(species):
        return species  # Tests use a Gen1 event, where the mapping is identical.


class EventSelectorTests(unittest.TestCase):
    def test_only_catalogued_events_in_chronological_order(self):
        events = catalog()
        self.assertEqual(152, len(events))
        self.assertEqual(148, len({e['number'] for e in events}))
        self.assertEqual(sorted(e['start'] for e in events), [e['start'] for e in events])
        self.assertTrue(all('2022-01-01' <= e['start'] <= '2026-12-31' for e in events))

    def test_unknown_paths_cannot_be_selected(self):
        for value in ('../lab', 'standard', '', '999-999'):
            with self.assertRaises(ValueError):
                package(value)

    def test_reruns_use_historical_dates_not_reused_identifiers(self):
        by_number = {e['number']: e for e in catalog()}
        self.assertEqual('2022-12-02', by_number[2]['start'])
        self.assertEqual('2024-03-13', by_number[49]['start'])
        self.assertEqual('2026-01-16', by_number[117]['start'])
        self.assertEqual('2023-12-25', by_number[39]['start'])
        self.assertEqual('2024-04-26', by_number[53]['start'])
        self.assertEqual('2025-05-30', by_number[98]['start'])
        self.assertEqual('2026-09-04', by_number[148]['start'])
        options = event_options()
        self.assertEqual(161, len(options))
        self.assertEqual(len(options), len({key for key, label in options}))
        self.assertEqual(sorted(label[:10] for key, label in options), [label[:10] for key, label in options])
        entry, _ = package('002-002@2022-12-16')
        self.assertEqual('2022-12-16', entry['start'])
        with self.assertRaisesRegex(ValueError, 'date window'):
            package('002-002@2026-01-16')

    def test_featured_boss_selected_before_side_encounter(self):
        result = select('002-002', FakeGen9, {6: 'Charizard'})
        self.assertEqual((6, 7, 'Dragon'), (result.species, result.rule['Difficulty'], result.tera))
        self.assertEqual('Flutter Mane', result.recommendation.pokemon)

    def test_selecting_wrong_index_fails(self):
        with self.assertRaises(ValueError):
            select('002-002', FakeGen9, {}, index=999)

    def test_type_chart_includes_immunities_and_double_types(self):
        self.assertEqual(0, effectiveness('Fighting', ('Ghost', 'Steel')))
        self.assertEqual(4, effectiveness('Ground', ('Steel', 'Rock')))
        self.assertEqual(.25, effectiveness('Grass', ('Fire', 'Flying')))
