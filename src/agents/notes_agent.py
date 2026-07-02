"""
MeetSmart AI — Notes Agent.
Ingests meeting transcript or notes, calls Gemini (or rule-based fallback),
and returns structured meeting notes with action items and owners.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

from sqlalchemy.orm import Session

from src.db.models import Meeting, MeetingNote, ActionItem, Employee
from src.services.gemini_service import process_meeting_notes
from src.utils.config import settings

logger = logging.getLogger(__name__)


class NotesAgent:
    """
    Processes raw meeting transcripts into structured notes and action items.
    Saves results to DB and outputs/action_items.json.
    """

    def process(
        self,
        db: Session,
        meeting_id: int,
        transcript: str,
        save_json: bool = True,
    ) -> dict:
        """
        Process transcript for a meeting:
          1. Call Gemini / rule-based extractor.
          2. Persist MeetingNote and ActionItems to DB.
          3. Optionally save action items as JSON file.
          4. Return structured notes dict.
        """
        meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
        if not meeting:
            logger.error(f"Meeting {meeting_id} not found for notes processing.")
            return {}

        logger.info(f"Processing notes for meeting [{meeting_id}] ({len(transcript)} chars)")

        # LLM / rule-based extraction
        structured = process_meeting_notes(transcript)

        # Persist MeetingNote
        note = MeetingNote(
            meeting_id=meeting_id,
            summary=structured.get("summary", ""),
            decisions_json=json.dumps(structured.get("decisions", [])),
            raw_transcript=transcript[:10000],  # cap to avoid huge DB entries
        )
        db.add(note)
        db.flush()

        # Persist ActionItems
        action_items_data = structured.get("action_items", [])
        for item_data in action_items_data:
            # Try to resolve owner to an employee
            owner_name = item_data.get("owner", "Team")
            owner_id = self._resolve_owner(db, owner_name, meeting)

            deadline_str = item_data.get("deadline", "TBD")
            deadline_dt = self._parse_deadline(deadline_str)

            action = ActionItem(
                meeting_id=meeting_id,
                description=item_data.get("description", ""),
                owner_id=owner_id,
                owner_name=owner_name,
                deadline=deadline_dt,
                priority=item_data.get("priority", "medium"),
                status="pending",
            )
            db.add(action)

        db.commit()

        # Save JSON output
        if save_json:
            self._save_json(meeting, structured)

        # Update meeting status
        meeting.status = "completed"
        db.commit()

        result = {
            "meeting_id": meeting_id,
            "meeting_title": meeting.title,
            "summary": structured.get("summary", ""),
            "decisions": structured.get("decisions", []),
            "action_items": action_items_data,
            "key_topics": structured.get("key_topics", []),
            "mode": structured.get("mode", "gemini"),
            "note_id": note.id,
        }

        logger.info(
            f"✅ Notes processed: {len(action_items_data)} action items, "
            f"{len(structured.get('decisions', []))} decisions"
        )
        return result

    def get_action_items(self, db: Session, meeting_id: int) -> list:
        """Return all action items for a meeting."""
        items = (
            db.query(ActionItem)
            .filter(ActionItem.meeting_id == meeting_id)
            .order_by(ActionItem.priority.desc())
            .all()
        )
        return items

    def update_action_status(
        self, db: Session, action_item_id: int, status: str
    ) -> bool:
        item = db.query(ActionItem).filter(ActionItem.id == action_item_id).first()
        if item:
            item.status = status
            db.commit()
            return True
        return False

    def _resolve_owner(self, db: Session, owner_name: str, meeting: Meeting) -> Optional[int]:
        """Try to match an owner name to a meeting participant."""
        if not owner_name or owner_name.lower() in ("team", "tbd", "all"):
            return None
        # Simple first-name or full-name match
        for participant in meeting.participants:
            first = participant.name.split()[0].lower()
            if (
                first in owner_name.lower()
                or owner_name.lower() in participant.name.lower()
            ):
                return participant.id
        return None

    def _parse_deadline(self, deadline_str: str) -> Optional[datetime]:
        """Try to parse a deadline string into a datetime."""
        if not deadline_str or deadline_str.upper() in ("TBD", "N/A", "NONE"):
            return None
        formats = ["%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%m/%d/%Y"]
        for fmt in formats:
            try:
                return datetime.strptime(deadline_str, fmt)
            except ValueError:
                continue
        return None

    def _save_json(self, meeting: Meeting, structured: dict):
        """Save structured notes as a JSON file in /outputs."""
        try:
            outputs_dir = settings.outputs_path
            safe_title = "".join(
                c if c.isalnum() or c in "_ " else "_" for c in meeting.title
            )
            filename = f"action_items_{meeting.start_time.strftime('%Y-%m-%d')}_{safe_title[:30]}.json"
            out_path = outputs_dir / filename
            with open(out_path, "w") as f:
                json.dump(
                    {
                        "meeting_id": meeting.id,
                        "meeting_title": meeting.title,
                        "date": meeting.start_time.isoformat(),
                        **structured,
                    },
                    f,
                    indent=2,
                    default=str,
                )
            logger.info(f"Action items saved to {out_path}")
        except Exception as e:
            logger.warning(f"Could not save JSON: {e}")


# Module-level singleton
notes_agent = NotesAgent()
