"""
MeetSmart AI — MoM Agent.
Post-meeting: drafts a formal Minutes of Meeting Word document,
saves it to /outputs/ with a date-stamped filename,
and emails it to all participants.
"""

import json
import logging
from pathlib import Path
from typing import Optional

from sqlalchemy.orm import Session

from src.db.models import Meeting, MeetingNote, ActionItem
from src.services.docx_service import build_mom_document
from src.services.email_service import send_email, mom_delivery_html

logger = logging.getLogger(__name__)


class MoMAgent:
    """
    Generates and distributes the formal Minutes of Meeting document.
    Requires the Notes Agent to have already processed the meeting transcript.
    """

    def generate_and_send(
        self,
        db: Session,
        meeting_id: int,
        save_path: Optional[Path] = None,
    ) -> Optional[Path]:
        """
        Generate MoM Word document and email to all participants.
        Returns path to the saved .docx, or None on failure.
        """
        meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
        if not meeting:
            logger.error(f"Meeting {meeting_id} not found.")
            return None

        # Get meeting notes
        note = (
            db.query(MeetingNote)
            .filter(MeetingNote.meeting_id == meeting_id)
            .order_by(MeetingNote.created_at.desc())
            .first()
        )

        # Get action items
        action_items_orm = (
            db.query(ActionItem)
            .filter(ActionItem.meeting_id == meeting_id)
            .order_by(ActionItem.priority.desc())
            .all()
        )

        # Prepare data
        summary = note.summary if note else "No meeting notes recorded."
        decisions = json.loads(note.decisions_json) if note and note.decisions_json else []
        action_items = [
            {
                "description": ai.description,
                "owner": ai.owner_name or "Team",
                "deadline": ai.deadline.strftime("%Y-%m-%d") if ai.deadline else "TBD",
                "priority": ai.priority or "medium",
                "status": ai.status or "pending",
            }
            for ai in action_items_orm
        ]

        participants_info = [
            {
                "name": p.name,
                "role": p.role,
                "email": p.email,
            }
            for p in meeting.participants
        ]

        # Build Word document
        docx_path = build_mom_document(
            meeting_title=meeting.title,
            meeting_date=meeting.start_time,
            organizer_name=meeting.organizer.name,
            participants=participants_info,
            agenda=meeting.agenda or "No agenda set.",
            summary=summary,
            decisions=decisions,
            action_items=action_items,
            save_path=save_path,
        )

        # Update note with mom_path
        if note:
            note.mom_path = str(docx_path)
            db.commit()

        # Send email with .docx attachment
        to_emails = [p.email for p in meeting.participants]
        date_str = meeting.start_time.strftime("%d %B %Y")
        html = mom_delivery_html(
            meeting_title=meeting.title,
            date_str=date_str,
            participant_names=[p.name for p in meeting.participants],
            summary=summary,
            action_count=len(action_items),
        )

        success = send_email(
            to_emails=to_emails,
            subject=f"[MeetSmart AI] Minutes of Meeting — {meeting.title} ({date_str})",
            html_body=html,
            attachments=[docx_path],
        )

        if success:
            logger.info(f"✅ MoM sent to {len(to_emails)} participants. Doc: {docx_path}")
        else:
            logger.error(f"❌ MoM email failed for meeting [{meeting_id}]")

        return docx_path


# Module-level singleton
mom_agent = MoMAgent()
