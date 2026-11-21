"""Live Colombian league schedule, supplemented by verified DIMAYOR notices."""
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

SCOREBOARD = 'https://site.api.espn.com/apis/site/v2/sports/soccer/col.1/scoreboard'
BOGOTA = ZoneInfo('America/Bogota')


def parse_scoreboard(payload, normalize):
    if not isinstance(payload.get('events'), list):
        raise ValueError('Respuesta de programación FPC inválida')
    entries = []
    for event in payload['events']:
        for game in event.get('competitions', []):
            sides = {side['homeAway']: side['team']['displayName']
                     for side in game.get('competitors', []) if side.get('type') == 'team'}
            if set(sides) != {'home', 'away'}:
                continue
            start = datetime.fromisoformat(game['date'].replace('Z', '+00:00'))
            if start.tzinfo is None:
                raise ValueError('Horario FPC sin zona horaria')
            start = start.astimezone(timezone.utc)
            status = game.get('status', event.get('status', {})).get('type', {}).get('name', '')
            publish = game.get('timeValid') is True and status not in {
                'STATUS_CANCELED', 'STATUS_CANCELLED', 'STATUS_POSTPONED', 'STATUS_DELAYED'}
            group = game.get('group', {}).get('name', '')
            description = 'Liga BetPlay. ' + group
            if 'semifinal' in group.lower():
                description = 'Cuadrangulares. ' + group
            entries.append(dict(start=start, end=start + timedelta(hours=2),
                                summary=sides['home'] + ' - ' + sides['away'],
                                teams=(normalize(sides['home']), normalize(sides['away'])),
                                competition='Liga Colombia', description=description,
                                source=SCOREBOARD + '?dates=' + start.astimezone(BOGOTA).strftime('%Y%m%d'),
                                publish=publish))
    return entries


def same_fixture(a, b):
    # Keep home/away order: the return fixture is a different match.
    return a['teams'] == b['teams'] and abs((a['start'] - b['start']).total_seconds()) <= 14 * 86400


def get_entries(session, normalize, now=None, supplement_path=None):
    now = now or datetime.now(timezone.utc)
    today = now.astimezone(BOGOTA).date()
    first, last = today - timedelta(days=30), today + timedelta(days=90)
    def download(day):
        response = session.get(SCOREBOARD, params={'dates': day.strftime('%Y%m%d')}, timeout=40)
        response.raise_for_status()
        return response.json()
    seed = download(today)
    if not seed.get('leagues'):
        raise ValueError('Falta calendario de fechas FPC')
    calendar = seed['leagues'][0].get('calendar')
    if not isinstance(calendar, list):
        raise ValueError('Calendario de fechas FPC inválido')
    days = {datetime.fromisoformat(day.replace('Z', '+00:00')).date() for day in calendar}
    entries = parse_scoreboard(seed, normalize)
    for day in sorted(d for d in days if first <= d <= last and d != today):
        entries.extend(parse_scoreboard(download(day), normalize))
    # A live confirmed schedule supersedes these notices when the provider catches up.
    path = supplement_path or Path(__file__).with_name('colombia_dimayor.json')
    notices = json.loads(Path(path).read_text(encoding='utf-8'))['fixtures']
    for fixture in notices:
        start = datetime.fromisoformat(fixture['start']).astimezone(timezone.utc)
        if not first <= start.astimezone(BOGOTA).date() <= last:
            continue
        item = dict(start=start, end=start + timedelta(hours=2),
                    summary=fixture['home'] + ' - ' + fixture['away'],
                    teams=(normalize(fixture['home']), normalize(fixture['away'])),
                    competition='Liga Colombia', description=f"Cuadrangulares, fecha {fixture['round']}, grupo {fixture['group']}.",
                    source=fixture['source'], publish=True)
        if not any(same_fixture(item, live) for live in entries):
            entries.append(item)
    return entries


def reconcile(existing, authoritative):
    """Replace stale league times and suppress canceled fixtures before dedupe."""
    kept = [entry for entry in existing if not (
        entry.get('competition') in (None, 'Liga Colombia') and
        any(same_fixture(entry, fresh) for fresh in authoritative))]
    return kept + [entry for entry in authoritative if entry['publish']]
