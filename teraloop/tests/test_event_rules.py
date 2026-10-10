import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from distribution.build_release import ready_catalog
from past_raids.event import EventPackage
from past_raids.event_rules import decode_event_rules
from tools.audit_catalog_event_rules import audit

ROOT = Path(__file__).resolve().parents[1]
REFERENCE = ROOT / 'source-materials/mewtwo-event'


class EventRulesTests(unittest.TestCase):
    def test_mewtwo_exact_json_control(self):
        binary = (REFERENCE / 'Files/raid_enemy_array_1_3_0').read_bytes()
        reference = json.loads((REFERENCE / 'Json/raid_enemy_array_1_3_0.json').read_text(encoding='utf-8-sig'))
        decoded = decode_event_rules(binary)
        active = [r for r in decoded['Table'] if r['Info']['Rate'] > 0]
        self.assertEqual({'Table': active}, reference)

    def test_mewtwo_shield_and_startup_move(self):
        package = EventPackage.load(REFERENCE)
        info = next(r for r in package.native_rules if r['BossPokePara']['DevId'] == 150)
        self.assertEqual(info['BossDesc']['PowerChargeTrigerHp'], 99)
        self.assertEqual(info['BossDesc']['ExtraAction6'],
                         {'Timing': 1, 'Action': 3, 'Value': 100, 'Wazano': 347})
        self.assertEqual(info['TimeDesc']['GameLimit'], 900)

    def test_all_shipped_events_decode_and_load(self):
        events = ready_catalog()
        report = audit(events, ROOT / 'distribution')
        self.assertEqual(report['event_numbers'], list(range(1, 149)))
        self.assertEqual(report['catalog_entries'], len(events))
        self.assertFalse(report['radio_opened'])
        for event in events:
            with self.subTest(number=event['number'], package=event['package']):
                package = EventPackage.load(ROOT / 'distribution' / event['package'])
                self.assertTrue(package.bosses)
                self.assertEqual(len(package.bosses), len(package.native_rules))

    def test_bounds(self):
        for data in [b'', bytes(4), bytes(64), b'\xff' * 80]:
            with self.subTest(size=len(data)), self.assertRaises(ValueError):
                decode_event_rules(data)

    def test_available_original_json_references(self):
        gallery = ROOT / 'artifacts/events-gallery-source'
        if not gallery.is_dir():
            self.skipTest('Optional local original gallery absent')
        report = audit(ready_catalog(), ROOT / 'distribution', gallery)
        self.assertGreater(report['json_reference_exact_matches'], 0)
        for event in report['events']:
            if event.get('json_reference_available'):
                self.assertTrue(event['json_reference_exact_match'])

    def test_package_path_cannot_escape(self):
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaises(ValueError):
                audit([{'package': '../outside'}], folder)

    def test_hash_mismatch_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder)
            package = base / 'event'
            package.mkdir()
            (package / 'Identifier.txt').write_bytes(b'1')
            event = {'number': 1, 'package': 'event',
                     'files': {'Identifier.txt': hashlib.sha256(b'2').hexdigest()}}
            with self.assertRaisesRegex(ValueError, 'hash differs'):
                audit([event], base)


if __name__ == '__main__':
    unittest.main()
