"""Build one deduplicated Apple Calendar subscription from Fixtur.es feeds."""
import hashlib
import json
import logging
import re
import unicodedata
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from icalendar import Calendar, Event

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
LOG = logging.getLogger("matchday")
USER_AGENT = "MatchdayCalendar/1.0 (personal fixture subscriber)"
SESSION = requests.Session()
SESSION.headers.update({"User-Agent": USER_AGENT})

ALIASES = {
    "barcelona": "barcelona", "barca": "barcelona", "f c barcelona": "barcelona",
    "atletico madrid": "atletico madrid", "atletico de madrid": "atletico madrid",
    "real betis seville": "real betis", "real betis sevilla": "real betis",
    "paris saint germain": "psg", "paris sg": "psg",
    "bayern munchen": "bayern munich", "bayern munchen": "bayern munich", "bayern munich": "bayern munich",
    "borussia dortmund": "dortmund", "bvb": "dortmund",
    "inter milano": "inter milan", "internazionale": "inter milan", "inter": "inter milan",
    "ac milan": "milan", "as roma": "roma", "ssc napoli": "napoli",
    "sporting cp": "sporting", "sporting portugal": "sporting", "sl benfica": "benfica",
    "como 1907": "como", "milllionarios": "millonarios",
    "santa fe": "independiente santa fe", "boca juniors": "boca", "river plate": "river",
    "se palmeiras": "palmeiras", "vasco da gama": "vasco da gama",
}

def norm(value):
    value = unicodedata.normalize("NFKD", value or "")
    value = "".join(c for c in value if not unicodedata.combining(c))
    value = re.sub(r"\b(?:fc|cf|sc|afc|ssc)\b", " ", value.lower())
    value = re.sub(r"[^a-z0-9]+", " ", value).strip()
    return ALIASES.get(value, value)

def teams(summary):
    """Try extracting opposing team names from a fixture headline."""
    s = re.sub(r"(?i)\s*\((?:[0-9]+\s*[-:]\s*[0-9]+)\)\s*$", "", summary)
    s = re.sub(r"(?i)^\s*(?:⚽|football:|soccer:|champions league:|premier league:)\s*", "", s).strip()
    pieces = re.split(r"\s+(?:vs\.?|v\.?|–|—|-)\s+", s, maxsplit=1, flags=re.IGNORECASE)
    if len(pieces) != 2:
        return None
    pieces = [re.sub(r"\s*\[[^]]+\]", "", x) for x in pieces]
    a, b = [norm(x) for x in pieces]
    return (a, b) if a and b else None

def is_calendar(data):
    return b"BEGIN:VCALENDAR" in data[:1500]

def read_calendar_url(page_url):
    """Best-effort extraction of public calendar subscription from provider's page."""
    response = SESSION.get(page_url, timeout=35)
    response.raise_for_status()
    if is_calendar(response.content):
        return response.url
    soup = BeautifulSoup(response.text, "html.parser")
    candidates = []
    for anchor in soup.select("a[href]"):
        href = anchor.get("href", "").strip()
        label = anchor.get_text(" ", strip=True).lower()
        score = 0
        if href.startswith("webcal:"):
            score += 10
            href = re.sub(r"^webcal:", "https:", href, flags=re.I)
        if ".ics" in href.lower():
            score += 8
        if "apple" in label or "ical" in label:
            score += 5
        if "google" in label or "outlook" in label:
            score -= 10
        if score > 0 and not href.startswith("javascript:"):
            candidates.append((score, urljoin(page_url, href)))
    # Some providers render the subscription url as a literal in embedded scripts.
    for match in re.findall(r"(?:webcal:|https?:)[^\s\"'<>]+?\.ics(?:\?[^\s\"'<>]*)?", response.text):
        candidates.append((6, match.replace("webcal:", "https:", 1)))
    if not candidates:
        raise ValueError("No se encontró enlace ICS en el HTML: " + page_url)
    for _, candidate in sorted(candidates, reverse=True):
        try:
            res = SESSION.get(candidate, timeout=35)
            res.raise_for_status()
            if is_calendar(res.content):
                return candidate
        except requests.RequestException:
            pass
    raise ValueError("Ningún enlace obtenido devolvió un calendario ICS: " + page_url)

def get_entries(page_url, competition=None, only_team=None):
    calendar_url = read_calendar_url(page_url)
    response = SESSION.get(calendar_url, timeout=40)
    response.raise_for_status()
    cal = Calendar.from_ical(response.content)
    entries = []
    for component in cal.walk("VEVENT"):
        start = component.decoded("DTSTART", None)
        if not isinstance(start, datetime):
            # Exclude all-day events; they may be announcements rather than fixtures.
            continue
        if start.tzinfo is None:
            # Do not make a potentially incorrect assumption about a floating time.
            continue
        dt = start.astimezone(timezone.utc)
        title = str(component.get("SUMMARY", "")).strip()
        if not title:
            continue
        matchup = teams(title)
        # Provider feeds include timed stage markers and unresolved fixtures.
        # Publish only matches with two identifiable teams.
        placeholders = {"tbd", "tbc", "unknown", "to be determined", "to be confirmed"}
        if not matchup or any(team in placeholders for team in matchup):
            continue
        end = component.decoded("DTEND", None)
        duration = timedelta(hours=2)
        if isinstance(end, datetime):
            duration = end.astimezone(timezone.utc) - dt
        if duration <= timedelta(0) or duration > timedelta(hours=5):
            duration = timedelta(hours=2)
        if only_team and norm(only_team) not in matchup:
            continue
        entries.append({"competition": competition, "start": dt, "end": dt + duration, "summary": title, "teams": matchup, "description": str(component.get("DESCRIPTION", "")), "source": page_url})
    LOG.info("%s: %s partidos", page_url, len(entries))
    return entries

def merge(entries):
    """Deduplicate fixtures in near-linear time with 30-minute kickoff tolerance."""
    unique = []
    team_index = {}
    title_index = set()
    duplicates = 0
    for entry in sorted(entries, key=lambda e: (not bool(e.get("competition")), e["start"], e["summary"])):
        matchup = entry["teams"]
        key_title = (norm(entry["summary"]), entry["start"])
        matched = key_title in title_index
        if matchup and not matched:
            pair = tuple(sorted(matchup))
            # Check only kickoffs of the same teams, within the time window.
            # The bucket index is maintained in UTC to avoid timezone issues.
            minute_bucket = int(entry["start"].timestamp() // 1800)
            for bucket in (minute_bucket - 1, minute_bucket, minute_bucket + 1):
                for old in team_index.get((pair, bucket), ()):
                    if abs((entry["start"] - old["start"]).total_seconds()) <= 1800:
                        matched = True
                        break
                if matched:
                    break
        if matched:
            # Competition feeds are processed first at equal kickoffs. Preserve
            # their explicit identity when a team feed repeats the fixture.
            duplicates += 1
            continue
        unique.append(entry)
        title_index.add(key_title)
        if matchup:
            pair = tuple(sorted(matchup))
            minute_bucket = int(entry["start"].timestamp() // 1800)
            team_index.setdefault((pair, minute_bucket), []).append(entry)
    return unique, duplicates

def annotate_competitions(entries, references):
    """Match actual fixtures, never infer a tournament from club nationality."""
    index = defaultdict(list)
    for entry in references:
        if entry["teams"] and entry.get("competition"):
            pair = tuple(sorted(entry["teams"]))
            bucket = int(entry["start"].timestamp() // 1800)
            index[(pair, bucket)].append(entry)
    result = []
    for entry in entries:
        entry = dict(entry)
        if not entry.get("competition") and entry["teams"]:
            pair = tuple(sorted(entry["teams"]))
            bucket = int(entry["start"].timestamp() // 1800)
            matches = {ref["competition"] for b in (bucket - 1, bucket, bucket + 1)
                       for ref in index.get((pair, b), ())
                       if abs((ref["start"] - entry["start"]).total_seconds()) <= 1800}
            if len(matches) == 1:
                entry["competition"] = matches.pop()
        result.append(entry)
    return result


def display_title(item):
    if item.get("group_identity") or not item.get("competition"):
        return item["summary"]
    title = re.sub(r"\s*\[[^]]+\]", "", item["summary"]).strip()
    label = {"Copa Sudamericana": "Sudamericana", "Copa Libertadores": "Libertadores"}.get(
        item["competition"], item["competition"])
    return title + " · " + label


def group_simultaneous(entries, threshold=4):
    """Collapse only known competitions with exactly equal UTC kickoffs."""
    if threshold < 4:
        raise ValueError("El umbral mínimo es 4")
    buckets = defaultdict(list)
    result = []
    for entry in entries:
        if entry.get("competition"):
            buckets[(entry["competition"], entry["start"])].append(entry)
        else:
            result.append(entry)
    for (competition, start), fixtures in buckets.items():
        if len(fixtures) < threshold:
            result.extend(fixtures)
            continue
        fixtures = sorted(fixtures, key=lambda e: e["summary"])
        result.append({"start": start, "end": max(e["end"] for e in fixtures),
                       "summary": f"{competition} ×{len(fixtures)}", "teams": None,
                       "competition": competition,
                       "group_identity": "group|" + competition + "|" + start.isoformat(),
                       "description": "Partidos simultáneos:\n" + "\n".join(e["summary"] for e in fixtures),
                       "source": "\n".join(sorted({e["source"] for e in fixtures}))})
    return sorted(result, key=lambda e: (e["start"], e["summary"]))

def build():
    sources = json.loads(Path("sources.json").read_text(encoding="utf-8"))
    feeds = sources["feeds"]
    urls = [f["url"] for f in feeds]
    all_entries, failures = [], []
    references = []
    for feed in feeds:
        u = feed["url"]
        try:
            entries = get_entries(u, feed.get("competition"), feed.get("only_team"))
            if feed.get("allowed_opponents_source"):
                reference = get_entries(feed["allowed_opponents_source"])
                allowed = {t for e in reference for t in (e["teams"] or ())}
                entries = [e for e in entries if e["teams"] and all(t in allowed for t in e["teams"])]
            region = feed.get("region")
            if region:
                region_teams = {norm(t) for t in sources[region + "_teams"]}
                entries = [e for e in entries if e["teams"] and
                           all(t in region_teams for t in e["teams"])]
            all_entries.extend(entries)
        except (requests.RequestException, ValueError, KeyError) as e:
            failures.append((u, str(e)))
            LOG.warning("Fuente no disponible %s: %s", u, e)
    for feed in sources.get("competition_references", []):
        try:
            references.extend(get_entries(feed["url"], feed["competition"]))
        except (requests.RequestException, ValueError, KeyError) as e:
            failures.append((feed["url"], str(e)))
            LOG.warning("Referencia no disponible %s: %s", feed["url"], e)
    if failures:
        LOG.error("%s/%s fuentes fallaron", len(failures), len(urls))
        # Do not publish incomplete feeds as complete; retains last deployed feed.
        raise RuntimeError("No se publica un calendario incompleto. Fuentes fallidas: " + ", ".join(url for url, _ in failures))
    if len(all_entries) < 100:
        raise RuntimeError("Se recuperaron muy pocos eventos. No publicar calendario incompleto.")
    LOG.info("Comienza deduplicación de %s eventos", len(all_entries))
    # Limit calendar to a useful rolling window; reduces outdated history and
    # processing time. Keep recent fixtures for context, plus 18 months ahead.
    now = datetime.now(timezone.utc)
    window_start = now - timedelta(days=30)
    window_end = now + timedelta(days=550)
    all_entries = [e for e in all_entries if window_start <= e["start"] <= window_end]
    if not all_entries:
        raise RuntimeError("No hay partidos recientes o futuros en los feeds")
    all_entries = annotate_competitions(all_entries, references)
    chosen, duplicates = merge(all_entries)
    LOG.info("Deduplicados: %s partidos únicos, %s duplicados", len(chosen), duplicates)
    fixture_count = len(chosen)
    chosen = group_simultaneous(chosen, sources.get("group_threshold", 4))
    cal = Calendar()
    cal.add("prodid", "-//Matchday Personal Calendar//ES")
    cal.add("version", "2.0")
    cal.add("x-wr-calname", "⚽ Matchday")
    cal.add("x-wr-timezone", "America/Bogota")
    seen_uids = set()
    for item in chosen:
        ev = Event()
        # Stable ID for updates; avoid changing UID when the title is revised.
        matchup = item["teams"]
        identity = item.get("group_identity") or ("|".join(sorted(matchup)) if matchup else norm(item["summary"]))
        # Stable over minor kickoff changes; a same-day reschedule retains its UID.
        key = identity + "|" + item["start"].strftime("%Y-%m-%d")
        uid = hashlib.sha256(key.encode()).hexdigest()[:25] + "@matchday"
        # If same sides have two games on same date, distinguish via kickoff hour.
        if uid in seen_uids:
            uid = hashlib.sha256((key + "|" + item["start"].isoformat()).encode()).hexdigest()[:25] + "@matchday"
        seen_uids.add(uid)
        ev.add("uid", uid)
        ev.add("summary", "⚽ " + display_title(item))
        ev.add("dtstart", item["start"])
        ev.add("dtend", item["end"])
        ev.add("dtstamp", now)
        description = item.get("description", "")
        if not item.get("competition"):
            description = "Torneo sin confirmar en las fuentes disponibles.\n" + description
        ev.add("description", description + "\nFuente de calendario: " + item["source"])
        ev.add("transp", "TRANSPARENT")
        cal.add_component(ev)
    Path("public").mkdir(exist_ok=True)
    Path("public/matchday.ics").write_bytes(cal.to_ical())
    Path("public/index.html").write_text('<!doctype html><meta charset="utf-8"><title>Matchday</title><h1>⚽ Matchday</h1><p><a href="matchday.ics">Calendario para Apple Calendar</a></p>', encoding="utf-8")
    Path("public/status.json").write_text(json.dumps({"updated_utc": now.isoformat(), "sources": len(urls), "events": len(chosen), "fixtures": fixture_count, "groups": sum(bool(e.get("group_identity")) for e in chosen), "duplicates_removed": duplicates}, indent=2), encoding="utf-8")
    LOG.info("Hecho: %s partidos, %s duplicados eliminados", len(chosen), duplicates)

if __name__ == "__main__":
    build()
