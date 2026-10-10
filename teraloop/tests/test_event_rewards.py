import json
from pathlib import Path
import unittest
from past_raids.event_rewards import decode

ROOT = Path(__file__).resolve().parents[1]


class EventRewardsTests(unittest.TestCase):
    def test_mewtwo_exact_source_json(self):
        folder = ROOT/'source-materials/mewtwo-event'
        for kind in ('fixed', 'lottery'):
            name = kind+'_reward_item_array_1_3_0'
            expected = json.loads((folder/'Json'/ (name+'.json')).read_text(encoding='utf-8-sig'))
            observed = decode((folder/'Files'/name).read_bytes(), kind=kind)
            # Source JSON may retain only the active table subset.
            names = {row['TableName'] for row in expected['Table']}
            self.assertEqual({'Table': [r for r in observed['Table'] if r['TableName'] in names]}, expected)

    def test_charizard_exact_source_json(self):
        folder = ROOT/'artifacts/events-gallery-source/Released/Gen 9/SV/Raid Events/002 Charizard the Unrivaled'
        if not folder.is_dir():
            self.skipTest('Optional original gallery absent')
        for kind in ('fixed', 'lottery'):
            name = kind+'_reward_item_array'
            expected = json.loads((folder/'Json'/(name+'.json')).read_text(encoding='utf-8-sig'))
            self.assertEqual(decode((folder/'Files'/name).read_bytes(), kind=kind), expected)

    def test_invalid_schema_and_bounds(self):
        with self.assertRaises(ValueError):
            decode(bytes(20), kind='guess')
        for kind in ('fixed', 'lottery'):
            for data in (b'', bytes(4), bytes(64), b'\xff'*80):
                with self.assertRaises(ValueError):
                    decode(data, kind=kind)
