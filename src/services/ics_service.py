"""
MeetSmart AI — iCalendar (.ics) file generator.
Uses the `icalendar` library to produce RFC 5545 compliant VEVENT files.
"""

import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from icalendar import Calendar, Event, vText, vCalAddress

from src.utils.config import settings


def build_ics(
    meeting_id: int,
    title: str,
    description: str,
    start_time: datetime,
    end_time: datetime,
    organizer_name: str,
    organizer_email: str,
    participants: List[dict],  # [{"name": ..., "email": ...}]
    location: str = "Google Meet / Teams",
    save_path: Optional[Path] = None,
) -> Path:
    """
    Build an .ics calendar invite file and return the path.
    
    Args:
        participants: list of dicts with 'name' and 'email' keys
        save_path: optional custom save location; defaults to samples/
    """
    cal = Calendar()
    cal.add("prodid", "-//MeetSmart AI//ThinkPalm//EN")
    cal.add("version", "2.0")
    cal.add("calscale", "GREGORIAN")
    cal.add("method", "REQUEST")

    event = Event()
    event.add("summary", title)
    event.add("description", description)
    event.add("dtstart", start_time)
    event.add("dtend", end_time)
    event.add("dtstamp", datetime.utcnow())
    event.add("uid", f"meetsmart-{meeting_id}-{uuid.uuid4().hex[:8]}@thinkpalm.com")
    event.add("location", location)
    event.add("status", "CONFIRMED")
    event.add("sequence", 0)

    # Organizer
    org = vCalAddress(f"MAILTO:{organizer_email}")
    org.params["CN"] = vText(organizer_name)
    org.params["ROLE"] = vText("CHAIR")
    event.add("organizer", org)

    # Attendees
    for p in participants:
        attendee = vCalAddress(f"MAILTO:{p['email']}")
        attendee.params["CN"] = vText(p["name"])
        attendee.params["ROLE"] = vText("REQ-PARTICIPANT")
        attendee.params["PARTSTAT"] = vText("NEEDS-ACTION")
        attendee.params["RSVP"] = vText("TRUE")
        event.add("attendee", attendee, encode=0)

    cal.add_component(event)

    # Determine save path
    if save_path is None:
        samples_dir = Path("samples")
        samples_dir.mkdir(exist_ok=True)
        safe_title = "".join(c if c.isalnum() or c in "_ -" else "_" for c in title)
        save_path = samples_dir / f"meeting_{meeting_id}_{safe_title[:30]}.ics"

    save_path.parent.mkdir(parents=True, exist_ok=True)
    with open(save_path, "wb") as f:
        f.write(cal.to_ical())

    return save_path


def build_sample_ics() -> Path:
    """Generate a sample .ics for demo/documentation purposes."""
    from datetime import timedelta
    now = datetime(2026, 6, 20, 10, 0, 0)
    return build_ics(
        meeting_id=1,
        title="Q3 Product Roadmap Review",
        description="Quarterly review of product roadmap priorities and resource allocation.\n\nAgenda:\n1. Review Q2 deliverables\n2. Discuss Q3 priorities\n3. Resource planning",
        start_time=now,
        end_time=now + timedelta(hours=1),
        organizer_name="Priya Nair",
        organizer_email="priya.nair@thinkpalm.com",
        participants=[
            {"name": "Arjun Sharma", "email": "arjun.sharma@thinkpalm.com"},
            {"name": "Sanjay Pillai", "email": "sanjay.pillai@thinkpalm.com"},
            {"name": "Divya Krishnan", "email": "divya.krishnan@thinkpalm.com"},
        ],
        location="Conference Room B / Google Meet",
        save_path=Path("samples/sample_meeting.ics"),
    )
