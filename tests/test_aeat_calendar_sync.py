import textwrap
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from unittest.mock import MagicMock

import pytest

from scripts.ingestion.sync_aeat_calendar import (
    AEATCalendarSync,
    parse_ical_datetime,
)


@pytest.fixture
def sample_html():
    return """
    <html>
      <body>
        <p><strong>Renta:</strong>
          <a href="https://www.google.com/calendar/ical/invitado2aeat%40gmail.com/public/basic.ics">
            renta
          </a>
        </p>
        <p><strong>IVA:</strong>
          <a href="https://www.google.com/calendar/ical/517mcuhcis0lldnp9b7c0nk2q8%40group.calendar.google.com/public/basic.ics">
            iva
          </a>
        </p>
      </body>
    </html>
    """


@pytest.fixture
def sample_ics():
    return textwrap.dedent(
        """
        BEGIN:VCALENDAR
        VERSION:2.0
        PRODID:-//AEAT//Calendar//ES
        BEGIN:VEVENT
        UID:event-1@example.com
        SUMMARY:Pagar Modelo 303
        DTSTART;TZID=Europe/Madrid:20250320T090000
        DTEND;TZID=Europe/Madrid:20250320T110000
        SEQUENCE:3
        STATUS:CONFIRMED
        LAST-MODIFIED:20250115T120000Z
        DESCRIPTION:Presentar el modelo 303 correspondiente al primer trimestre.
        END:VEVENT
        BEGIN:VEVENT
        UID:event-2@example.com
        SUMMARY:Declaración informativa 347
        DTSTART;VALUE=DATE:20250331
        DTEND;VALUE=DATE:20250401
        SEQUENCE:1
        STATUS:CANCELLED
        LAST-MODIFIED:20250120T080000Z
        END:VEVENT
        END:VCALENDAR
        """.strip()
    )


def test_fetch_calendar_sources(monkeypatch, sample_html):
    sync = AEATCalendarSync()

    def fake_get(url, timeout=10):
        class FakeResponse:
            def raise_for_status(self):
                pass

            @property
            def text(self):
                return sample_html

        return FakeResponse()

    monkeypatch.setattr(sync.session, "get", fake_get)

    sources = sync.fetch_calendar_sources()
    assert sources == {
        "renta": "https://www.google.com/calendar/ical/invitado2aeat%40gmail.com/public/basic.ics",
        "iva": "https://www.google.com/calendar/ical/517mcuhcis0lldnp9b7c0nk2q8%40group.calendar.google.com/public/basic.ics",
    }


def test_parse_events_from_ics(sample_ics):
    sync = AEATCalendarSync()

    events = sync.parse_ics(sample_ics, calendar_type="iva")
    assert len(events) == 2

    first, second = events
    assert first["uid"] == "event-1@example.com"
    assert first["summary"] == "Pagar Modelo 303"
    assert first["calendar_type"] == "iva"
    assert first["status"] == "CONFIRMED"
    assert first["dtstart"] == datetime(2025, 3, 20, 9, 0, tzinfo=ZoneInfo("Europe/Madrid"))
    assert first["dtend"] == datetime(2025, 3, 20, 11, 0, tzinfo=ZoneInfo("Europe/Madrid"))
    assert first["sequence"] == 3
    assert "description" in first
    assert first["is_active"] is True

    assert second["uid"] == "event-2@example.com"
    assert second["dtstart"] == datetime(2025, 3, 31, 0, 0, tzinfo=timezone.utc)
    assert second["dtend"] == datetime(2025, 4, 1, 0, 0, tzinfo=timezone.utc)
    assert second["status"] == "CANCELLED"
    assert second["is_active"] is False


@pytest.mark.parametrize(
    "value,params,expected",
    [
        ("20250320T090000", {"TZID": "Europe/Madrid"}, datetime(2025, 3, 20, 9, 0, tzinfo=ZoneInfo("Europe/Madrid"))),
        ("20250320T090000Z", {}, datetime(2025, 3, 20, 9, 0, tzinfo=timezone.utc)),
        ("20250320", {"VALUE": "DATE"}, datetime(2025, 3, 20, 0, 0, tzinfo=timezone.utc)),
    ],
)
def test_parse_ical_datetime(value, params, expected):
    assert parse_ical_datetime(value, params) == expected


def test_upsert_events(monkeypatch):
    sync = AEATCalendarSync()
    fake_cursor = MagicMock()
    fake_conn = MagicMock()
    fake_conn.cursor.return_value = fake_cursor

    events = [
        {
            "uid": "event-1",
            "calendar_type": "iva",
            "summary": "Evento 1",
            "dtstart": datetime(2025, 3, 20, 9, 0, tzinfo=timezone.utc),
            "dtend": datetime(2025, 3, 20, 11, 0, tzinfo=timezone.utc),
            "status": "CONFIRMED",
            "sequence": 1,
            "last_modified": datetime(2025, 1, 1, 10, 0, tzinfo=timezone.utc),
            "description": "Descripción",
            "location": None,
            "organizer": None,
            "is_active": True,
            "raw": "BEGIN:VEVENT...END:VEVENT",
        }
    ]

    sync.upsert_events(fake_conn, events)

    fake_conn.cursor.assert_called_once()
    fake_cursor.execute.assert_called_once()
    args, kwargs = fake_cursor.execute.call_args
    sql, params = args
    assert "ON CONFLICT (uid, calendar_type)" in sql
    assert params[0] == events[0]["uid"]
    assert params[1] == events[0]["calendar_type"]
    fake_conn.commit.assert_called_once()
