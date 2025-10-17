"""
Synchronization utilities for AEAT public iCalendar feeds.

Steps covered:
- Discover calendar .ics URLs from the official instructions page.
- Download and parse VEVENT entries.
- Upsert events into Supabase with conflict keys (uid, calendar_type).
"""

from __future__ import annotations

import logging
import re
import textwrap
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, Iterable, List, Optional, Tuple
from unicodedata import normalize

import requests
from bs4 import BeautifulSoup
from zoneinfo import ZoneInfo

from app.services.supabase_service import SupabaseService

logger = logging.getLogger(__name__)

INSTRUCTIONS_URL = (
    "https://sede.agenciatributaria.gob.es/Sede/ayuda/calendario-contribuyente/icalendar/"
    "instrucciones-integrar-calendario.html"
)


def slugify(label: str) -> str:
    """Convert a human readable calendar title into a lowercase slug."""
    label = label.strip().lower().rstrip(":")
    normalized = normalize("NFKD", label).encode("ascii", "ignore").decode("ascii")
    normalized = re.sub(r"[^a-z0-9]+", "_", normalized)
    return normalized.strip("_")


def unfold_ics(ics_text: str) -> List[str]:
    """Unfold folded ICS lines according to RFC 5545."""
    lines: List[str] = []
    current: Optional[str] = None

    for raw in ics_text.splitlines():
        if not raw:
            if current is not None:
                lines.append(current)
                current = None
            continue

        if raw.startswith((" ", "\t")) and current is not None:
            current += raw[1:]
        else:
            if current is not None:
                lines.append(current)
            current = raw

    if current is not None:
        lines.append(current)

    return lines


def parse_property(line: str) -> Tuple[str, Dict[str, str], str]:
    """Parse an ICS property line into name, params and value."""
    line = line.strip()
    if ":" not in line:
        return line.upper(), {}, ""
    prop_part, value = line.split(":", 1)
    segments = prop_part.split(";")
    name = segments[0].upper()
    params: Dict[str, str] = {}
    for segment in segments[1:]:
        if "=" in segment:
            key, val = segment.split("=", 1)
            params[key.upper()] = val
        else:
            params[segment.upper()] = ""
    return name, params, value


def parse_ical_datetime(value: str, params: Dict[str, str]) -> datetime:
    """Parse iCalendar datetime/date strings into aware datetimes."""
    tzid = params.get("TZID")
    tzinfo = None

    if tzid:
        try:
            tzinfo = ZoneInfo(tzid)
        except Exception:  # pragma: no cover - fallback to UTC
            logger.warning("Unknown TZID %s, falling back to UTC", tzid)
            tzinfo = timezone.utc

    if value.endswith("Z"):
        tzinfo = timezone.utc
        dt = datetime.strptime(value, "%Y%m%dT%H%M%SZ")
        return dt.replace(tzinfo=tzinfo)

    if "T" in value:
        dt = datetime.strptime(value, "%Y%m%dT%H%M%S")
        return dt.replace(tzinfo=tzinfo or timezone.utc)

    # Assume DATE value
    dt = datetime.strptime(value, "%Y%m%d")
    return dt.replace(tzinfo=tzinfo or timezone.utc)


@dataclass
class CalendarEvent:
    uid: str
    calendar_type: str
    summary: Optional[str]
    dtstart: Optional[datetime]
    dtend: Optional[datetime]
    status: Optional[str]
    sequence: Optional[int]
    last_modified: Optional[datetime]
    description: Optional[str]
    location: Optional[str]
    organizer: Optional[str]
    is_active: bool
    raw: str

    def as_tuple(self) -> Tuple:
        return (
            self.uid,
            self.calendar_type,
            self.summary,
            self.dtstart,
            self.dtend,
            self.status,
            self.sequence,
            self.last_modified,
            self.description,
            self.location,
            self.organizer,
            self.is_active,
            self.raw,
        )


class AEATCalendarSync:
    def __init__(self, session: Optional[requests.Session] = None):
        self.session = session or requests.Session()

    def fetch_calendar_sources(self) -> Dict[str, str]:
        """Scrape the instructions page and build a {calendar_type: url} mapping."""
        response = self.session.get(INSTRUCTIONS_URL, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        sources: Dict[str, str] = {}
        pending_label: Optional[str] = None

        for paragraph in soup.find_all("p"):
            strong = paragraph.find("strong")
            link = paragraph.find("a", href=lambda h: h and h.endswith(".ics"))

            if strong and not link:
                pending_label = strong.get_text(" ", strip=True)
                continue

            label_text: Optional[str] = None
            if strong:
                label_text = strong.get_text(" ", strip=True)
                pending_label = label_text

            if link:
                label = label_text or pending_label or link.get_text(" ", strip=True)
                if not label:
                    continue
                slug = slugify(label)
                sources[slug] = link["href"]
                pending_label = None

        return sources

    def download_calendar(self, url: str) -> str:
        response = self.session.get(url, timeout=20)
        response.raise_for_status()
        return response.text

    def parse_ics(self, ics_text: str, calendar_type: str) -> List[Dict[str, object]]:
        normalized = textwrap.dedent(ics_text).strip()
        normalized = re.sub(r"\n[ \t]{2,}", "\n", normalized)
        lines = unfold_ics(normalized)
        events: List[Dict[str, object]] = []
        buffer: List[str] = []
        inside = False

        for line in lines:
            marker = line.strip().upper()
            if marker == "BEGIN:VEVENT":
                buffer = []
                inside = True
                continue
            if marker == "END:VEVENT":
                events.append(self._build_event(buffer, calendar_type))
                inside = False
                buffer = []
                continue
            if inside:
                buffer.append(line)

        return events

    def _build_event(self, lines: Iterable[str], calendar_type: str) -> Dict[str, object]:
        data: Dict[str, object] = {
            "uid": None,
            "summary": None,
            "dtstart": None,
            "dtend": None,
            "status": None,
            "sequence": None,
            "last_modified": None,
            "description": None,
            "location": None,
            "organizer": None,
            "calendar_type": calendar_type,
            "is_active": True,
            "raw": "\n".join(lines),
        }

        for raw_line in lines:
            name, params, value = parse_property(raw_line)
            value = value.strip()

            if name == "UID":
                data["uid"] = value
            elif name == "SUMMARY":
                data["summary"] = value
            elif name == "DTSTART":
                data["dtstart"] = parse_ical_datetime(value, params)
            elif name == "DTEND":
                data["dtend"] = parse_ical_datetime(value, params)
            elif name == "SEQUENCE":
                try:
                    data["sequence"] = int(value)
                except ValueError:
                    data["sequence"] = None
            elif name == "STATUS":
                data["status"] = value.upper()
                if value.upper() == "CANCELLED":
                    data["is_active"] = False
            elif name == "LAST-MODIFIED":
                data["last_modified"] = parse_ical_datetime(value, params)
            elif name == "DESCRIPTION":
                data["description"] = value
            elif name == "LOCATION":
                data["location"] = value
            elif name == "ORGANIZER":
                data["organizer"] = value

        if not data.get("uid"):
            raise ValueError("ICS event missing UID")

        return data

    def upsert_events(self, connection, events: Iterable[Dict[str, object]]) -> None:
        if not events:
            return

        cursor = connection.cursor()
        sql = """
            INSERT INTO calendar_events (
                uid,
                calendar_type,
                summary,
                dtstart,
                dtend,
                status,
                sequence,
                last_modified,
                description,
                location,
                organizer,
                is_active,
                raw,
                updated_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
            ON CONFLICT (uid, calendar_type) DO UPDATE SET
                summary = EXCLUDED.summary,
                dtstart = EXCLUDED.dtstart,
                dtend = EXCLUDED.dtend,
                status = EXCLUDED.status,
                sequence = EXCLUDED.sequence,
                last_modified = EXCLUDED.last_modified,
                description = EXCLUDED.description,
                location = EXCLUDED.location,
                organizer = EXCLUDED.organizer,
                is_active = EXCLUDED.is_active,
                raw = EXCLUDED.raw,
                updated_at = NOW()
        """

        for event in events:
            cursor.execute(
                sql,
                (
                    event["uid"],
                    event["calendar_type"],
                    event.get("summary"),
                    event.get("dtstart"),
                    event.get("dtend"),
                    event.get("status"),
                    event.get("sequence"),
                    event.get("last_modified"),
                    event.get("description"),
                    event.get("location"),
                    event.get("organizer"),
                    event.get("is_active"),
                    event.get("raw"),
                ),
            )

        connection.commit()


def sync_all_calendars():
    """High level helper to run the full synchronization."""
    sync = AEATCalendarSync()
    supabase = SupabaseService()
    if not supabase.connect():
        raise RuntimeError("Unable to connect to Supabase")

    try:
        sources = sync.fetch_calendar_sources()
        logger.info("Found %d calendar sources", len(sources))

        for calendar_type, url in sources.items():
            logger.info("Syncing calendar %s", calendar_type)
            ics_text = sync.download_calendar(url)
            events = sync.parse_ics(ics_text, calendar_type)
            sync.upsert_events(supabase.connection, events)
            logger.info("Upserted %d events for %s", len(events), calendar_type)
    finally:
        if supabase.connection:
            supabase.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    sync_all_calendars()
