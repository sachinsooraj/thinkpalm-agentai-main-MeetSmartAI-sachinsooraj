"""
MeetSmart AI — Invite Agent.
Generates iCalendar (.ics) meeting invites and emails them to all participants.
"""

import logging
from pathlib import Path
from typing import Optional

from sqlalchemy.orm import Session

from src.db.models import Meeting
from src.services.ics_service import build_ics
from src.services.email_service import send_email, meeting_invite_html

logger = logging.getLogger(__name__)


class InviteAgent:
    """
    Responsible for:
      1. Generating an .ics invite file for a booked meeting.
      2. Sending it to all participants via email (with .ics attachment).
    """

    def generate_and_send(
        self,
        db: Session,
        meeting_id: int,
        save_ics_to: Optional[Path] = None,
    ) -> Optional[Path]:
        """
        Generate the .ics file for a meeting and email it to all participants.
        Returns the path to the saved .ics file, or None on failure.
        """
        meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
        if not meeting:
            logger.error(f"Meeting {meeting_id} not found.")
            return None

        organizer = meeting.organizer
        participants = meeting.participants

        participant_info = [
            {"name": p.name, "email": p.email}
            for p in participants
        ]

        description = (
            f"Meeting organized by {organizer.name}\n\n"
            f"Agenda:\n{meeting.agenda or 'No agenda set.'}\n\n"
            f"Location: {meeting.location}"
        )

        # Build .ics
        ics_path = build_ics(
            meeting_id=meeting.id,
            title=meeting.title,
            description=description,
            start_time=meeting.start_time,
            end_time=meeting.end_time,
            organizer_name=organizer.name,
            organizer_email=organizer.email,
            participants=participant_info,
            location=meeting.location,
            save_path=save_ics_to,
        )

        # Update meeting record with ics path
        meeting.ics_path = str(ics_path)
        db.commit()

        # Build HTML email body
        html = meeting_invite_html(
            meeting_title=meeting.title,
            organizer_name=organizer.name,
            start_time=meeting.start_time.strftime("%A, %d %B %Y  %I:%M %p IST"),
            end_time=meeting.end_time.strftime("%I:%M %p IST"),
            participants=[p.name for p in participants],
            agenda=meeting.agenda or "No agenda set.",
            location=meeting.location,
        )

        to_emails = [p.email for p in participants]

        success = send_email(
            to_emails=to_emails,
            subject=f"[MeetSmart AI] Meeting Invite: {meeting.title}",
            html_body=html,
            attachments=[ics_path],
        )

        if success:
            logger.info(f"✅ Invite sent to {len(to_emails)} participants for meeting [{meeting_id}]")
        else:
            logger.error(f"❌ Invite email failed for meeting [{meeting_id}]")

        return ics_path


# Module-level singleton
invite_agent = InviteAgent()
