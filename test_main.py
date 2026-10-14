import unittest
from unittest.mock import patch, Mock
from icalendar import Calendar, Event
from datetime import datetime, timedelta, timezone
from main import teams, merge, group_simultaneous, annotate_competitions, display_title, get_entries

class CalendarTests(unittest.TestCase):
    def fixture(self, n, competition='Champions League', hour=19):
        start = datetime(2026,10,14,hour,tzinfo=timezone.utc)
        title = f'Team {n} - Rival {n} [CL]'
        return dict(start=start,end=start+timedelta(hours=2),summary=title,teams=teams(title),competition=competition,source='test',description='')
    def test_duplicates_before_grouping(self):
        entries=[self.fixture(n) for n in range(8)]
        duplicate=dict(entries[0],summary='Team 0 - Rival 0',competition=None)
        chosen,count=merge(entries+[duplicate])
        result=group_simultaneous(chosen)
        self.assertEqual(count,1)
        self.assertEqual(len(result),1)
        self.assertEqual(result[0]['summary'],'Champions League ×8')
        self.assertEqual(len(result[0]['description'].splitlines()),9)
    def test_threshold_and_separate_competitions_and_times(self):
        entries=[self.fixture(n) for n in range(3)]
        entries += [self.fixture(n,'Copa Libertadores') for n in range(4)]
        entries += [self.fixture(n,hour=17) for n in range(4)]
        entries += [self.fixture(n,None) for n in range(4)]
        self.assertEqual(len(group_simultaneous(entries)),9)
    def test_group_uid_identity_does_not_depend_on_count(self):
        a=group_simultaneous([self.fixture(n) for n in range(4)])[0]
        b=group_simultaneous([self.fixture(n) for n in range(8)])[0]
        self.assertEqual(a['group_identity'],b['group_identity'])
    def test_competition_metadata_survives_dedupe(self):
        a=self.fixture(0)
        duplicate=dict(a,competition=None,start=a['start']-timedelta(minutes=5))
        result,count=merge([duplicate,a])
        self.assertEqual(count,1)
        self.assertEqual(result[0]['competition'],'Champions League')

class CompetitionTitleTests(unittest.TestCase):
    fixture = CalendarTests.fixture
    def test_readable_title_and_group_unchanged(self):
        fixture = self.fixture(0, 'Copa Sudamericana')
        fixture['summary'] = 'Atlético Mineiro - Torque [CS]'
        self.assertEqual(display_title(fixture), 'Atlético Mineiro - Torque · Sudamericana')
        group = group_simultaneous([self.fixture(n) for n in range(4)])[0]
        self.assertEqual(display_title(group), 'Champions ×4')

    def test_match_by_fixture_and_time_not_club(self):
        league = self.fixture(0, 'Liga Argentina')
        cup = self.fixture(0, 'Copa Argentina', hour=22)
        unknown = self.fixture(0, None, hour=22)
        result = annotate_competitions([unknown], [league, cup])
        self.assertEqual(result[0]['competition'], 'Copa Argentina')
        self.assertIsNone(unknown['competition'])
        self.assertEqual(result[0]['teams'], unknown['teams'])
        self.assertEqual(result[0]['summary'], unknown['summary'])

    def test_unknown_or_ambiguous_not_guessed(self):
        unknown = self.fixture(0, None)
        result = annotate_competitions([unknown], [self.fixture(0, 'League'), self.fixture(0, 'Cup')])
        self.assertIsNone(result[0]['competition'])
        self.assertEqual(display_title(result[0]), unknown['summary'])
        self.assertIsNone(annotate_competitions([unknown], [self.fixture(1)])[0]['competition'])

class ShortNameTests(unittest.TestCase):
    fixture = CalendarTests.fixture

    def test_requested_names_and_original_identity(self):
        for original, short in [('Inter Miami CF', 'Inter Miami'),
                                ('New York City FC', 'New York City'),
                                ('LASK Linz', 'LASK'), ('FC Barcelona', 'Barcelona'),
                                ('Atlanta United FC', 'Atlanta United'),
                                ('RC Strasbourg', 'Strasbourg'),
                                ('Paris Saint-Germain', 'PSG')]:
            with self.subTest(team=original):
                fixture = self.fixture(0)
                fixture['summary'] = original + ' - Liverpool [CL]'
                identity = fixture['teams']
                self.assertEqual(display_title(fixture), short + ' - Liverpool · Champions')
                self.assertEqual(fixture['summary'], original + ' - Liverpool [CL]')
                self.assertEqual(fixture['teams'], identity)

    def test_fpc_and_group_notes(self):
        fixture = self.fixture(0, 'Liga Colombia')
        self.assertTrue(display_title(fixture).endswith(' · FPC'))
        entries = [self.fixture(n) for n in range(4)]
        entries[0]['summary'] = 'FC Barcelona - Paris Saint-Germain [CL]'
        group = group_simultaneous(entries)[0]
        self.assertIn('Barcelona - PSG [CL]', group['description'])
        self.assertEqual(display_title(group), 'Champions ×4')
        self.assertEqual(group['group_identity'], 'group|Champions League|' + group['start'].isoformat())

class IncompleteFixtureTests(unittest.TestCase):
    def test_provider_placeholders_are_excluded_before_grouping(self):
        cal = Calendar()
        for title in ['... - ... [CL]', 'Finals', 'TBD - River Plate',
                      'Sarmiento - ...', 'Sarmiento - River Plate']:
            event = Event()
            event.add('summary', title)
            event.add('dtstart', datetime(2026, 10, 14, 18, tzinfo=timezone.utc))
            cal.add_component(event)
        response = Mock(content=cal.to_ical())
        with patch('main.read_calendar_url', return_value='https://example.test/feed.ics'), \
             patch('main.SESSION.get', return_value=response):
            entries = get_entries('https://example.test/feed.ics', 'Libertadores')
        self.assertEqual([e['summary'] for e in entries], ['Sarmiento - River Plate'])
        self.assertEqual(len(group_simultaneous(entries)), 1)
        self.assertNotIn('group_identity', group_simultaneous(entries)[0])

if __name__=='__main__':unittest.main()
