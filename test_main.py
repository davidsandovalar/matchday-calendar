import unittest
from datetime import datetime, timedelta, timezone
from main import teams, merge, group_simultaneous

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

if __name__=='__main__':unittest.main()
