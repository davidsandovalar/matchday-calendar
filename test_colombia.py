import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import Mock

import colombia
from main import norm, merge


def payload(date='2026-11-21T01:40Z', status='STATUS_SCHEDULED', valid=True):
    return {'events': [{'competitions': [{'date': date, 'timeValid': valid,
             'status': {'type': {'name': status}},
             'group': {'name': 'Semifinals - Group B'},
             'competitors': [{'type': 'team', 'homeAway': 'home', 'team': {'displayName': 'Deportivo Cali'}},
                             {'type': 'team', 'homeAway': 'away', 'team': {'displayName': 'Millonarios'}}]}]}]}


class ColombianScheduleTests(unittest.TestCase):
    def test_utc_time_and_quadrangular_label(self):
        entry = colombia.parse_scoreboard(payload(), norm)[0]
        self.assertEqual(entry['start'].astimezone(colombia.BOGOTA).isoformat(), '2026-11-20T20:40:00-05:00')
        self.assertIn('Cuadrangulares', entry['description'])
        self.assertEqual(entry['teams'], ('deportivo cali', 'millonarios'))
        self.assertTrue(entry['publish'])

    def test_new_time_replaces_old_without_duplicate(self):
        entry = colombia.parse_scoreboard(payload(), norm)[0]
        old = dict(entry, start=entry['start'] - timedelta(hours=3), source='old ICS')
        output = colombia.reconcile([old], [entry])
        self.assertEqual(output, [entry])
        self.assertEqual(merge(output)[1], 0)

    def test_postponement_and_unknown_time_suppress_stale_matches(self):
        for status, valid in [('STATUS_POSTPONED', True), ('STATUS_CANCELED', True),
                              ('STATUS_SCHEDULED', False)]:
            entry = colombia.parse_scoreboard(payload(status=status, valid=valid), norm)[0]
            old = dict(entry, publish=True)
            self.assertEqual(colombia.reconcile([old], [entry]), [])

    def test_return_fixture_and_cup_are_kept(self):
        entry = colombia.parse_scoreboard(payload(), norm)[0]
        reverse = dict(entry, teams=entry['teams'][::-1])
        cup = dict(entry, competition='Copa Colombia')
        self.assertEqual(len(colombia.reconcile([reverse, cup], [entry])), 3)

    def test_calendar_discovers_new_dates_and_live_reschedule_wins(self):
        now = datetime(2026, 11, 20, 12, tzinfo=timezone.utc)
        seed = {'leagues': [{'calendar': ['2026-11-22T08:00Z']}], 'events': []}
        live = payload(date='2026-11-23T01:40Z')
        session = Mock()
        session.get.side_effect = [Mock(json=lambda: seed), Mock(json=lambda: live)]
        notice = {'fixtures': [{'home': 'Deportivo Cali', 'away': 'Millonarios',
                  'start': '2026-11-20T20:40:00-05:00', 'round': 1, 'group': 'B', 'source': 'DIMAYOR'}]}
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'notices.json'
            path.write_text(json.dumps(notice))
            entries = colombia.get_entries(session, norm, now=now, supplement_path=path)
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]['start'].day, 23)
        self.assertEqual(session.get.call_count, 2)

    def test_all_16_official_fixtures_have_confirmed_times(self):
        fixtures = json.loads(Path('colombia_dimayor.json').read_text())['fixtures']
        self.assertEqual(len(fixtures), 16)
        self.assertEqual({f['round'] for f in fixtures}, {1, 2, 3, 4})
        self.assertEqual(len({(f['home'], f['away'], f['start']) for f in fixtures}), 16)
        for fixture in fixtures:
            self.assertIsNotNone(datetime.fromisoformat(fixture['start']).tzinfo)
            self.assertTrue(fixture['source'].startswith('https://dimayor.com.co/'))
        for a, b in [('Atlético Bucaramanga', 'Bucaramanga'), ('Águilas Doradas', 'Rionegro'),
                     ('Alianza', 'Alianza Petrolera'), ('Atlético Junior', 'Junior'),
                     ('Boyacá Chicó', 'Chicó'), ('Jaguares de Córdoba', 'Jaguares')]:
            self.assertEqual(norm(a), norm(b))

    def test_malformed_response_is_not_published_as_empty(self):
        with self.assertRaises(ValueError):
            colombia.parse_scoreboard({'error': 'temporarily unavailable'}, norm)


if __name__ == '__main__':
    unittest.main()
