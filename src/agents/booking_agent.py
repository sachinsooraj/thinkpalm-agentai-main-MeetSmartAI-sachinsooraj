"""
MeetSmart AI — Booking Agent.
Checks all participants' availability, selects the optimal slot,
confirms booking, and updates the schedule store.
"""

from datetime import datetime, date, timedelta
from typing import List, Optional, Dict
import logging

from sqlalchemy.orm import Session

from src.db.models import Employee, Meeting, meeting_participants, Slot
from src.agents.availability_agent import availability_agent

logger = logging.getLogger(__name__)


class BookingAgent:
    """
    Orchestrates the meeting booking process end-to-end.
    """

    def find_optimal_slot(
        self,
        db: Session,
        participant_ids: List[int],
        preferred_date: Optional[date] = None,
        duration_minutes: int = 60,
        look_ahead_days: int = 14,
    ) -> Optional[Dict]:
        """
        Find the earliest available slot across all participants.
        
        Strategy:
          1. Start from preferred_date (or today) and look ahead look_ahead_days.
          2. Get overlapping free slots across all participants.
          3. Return the first (earliest) slot found.
        """
        start_date = preferred_date or date.today()
        end_date = start_date + timedelta(days=look_ahead_days)

        overlapping = availability_agent.get_overlap_slots(
            db=db,
            employee_ids=participant_ids,
            from_date=start_date,
            to_date=end_date,
            duration_minutes=duration_minutes,
        )

        if not overlapping:
            logger.warning(
                f"No overlapping slots found for participants {participant_ids} "
                f"between {start_date} and {end_date}"
            )
            return None

        # Return the earliest available slot
        optimal = overlapping[0]
        logger.info(f"Optimal slot found: {optimal['start_time']} – {optimal['end_time']}")
        return optimal

    def book_meeting(
        self,
        db: Session,
        title: str,
        agenda: str,
        organizer_id: int,
        participant_ids: List[int],
        start_time: Optional[datetime] = None,
        duration_minutes: int = 60,
        location: str = "Google Meet / Teams",
        preferred_date: Optional[date] = None,
    ) -> Optional[Meeting]:
        """
        Create a meeting booking:
          1. If start_time not given, find optimal slot automatically.
          2. Create Meeting record in DB.
          3. Block all participant slots.
          4. Return the created Meeting object.
        """
        # Determine start_time
        if start_time is None:
            all_participant_ids = list(set([organizer_id] + participant_ids))
            slot = self.find_optimal_slot(
                db, all_participant_ids, preferred_date, duration_minutes
            )
            if slot is None:
                logger.error("Could not find a common available slot.")
                return None
            start_time = slot["start_time"]

        end_time = start_time + timedelta(minutes=duration_minutes)

        # Validate participants exist
        all_ids = list(set([organizer_id] + participant_ids))
        employees = db.query(Employee).filter(Employee.id.in_(all_ids)).all()
        if len(employees) != len(all_ids):
            logger.error("One or more participant IDs not found in DB.")
            return None

        # Create the meeting
        meeting = Meeting(
            title=title,
            agenda=agenda,
            start_time=start_time,
            end_time=end_time,
            organizer_id=organizer_id,
            location=location,
            status="scheduled",
        )
        db.add(meeting)
        db.flush()  # get meeting.id

        # Add participants (many-to-many)
        for emp in employees:
            meeting.participants.append(emp)

        db.commit()

        # Block slots for all participants
        for eid in all_ids:
            availability_agent.block_slot(db, eid, start_time, end_time, meeting.id)

        logger.info(
            f"✅ Meeting booked: [{meeting.id}] '{title}' on "
            f"{start_time.strftime('%Y-%m-%d %H:%M')} with {len(employees)} participants"
        )
        return meeting

    def cancel_meeting(self, db: Session, meeting_id: int) -> bool:
        """Cancel a meeting and free all blocked slots."""
        meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
        if not meeting:
            return False

        meeting.status = "cancelled"

        # Free all participant slots
        for participant in meeting.participants:
            availability_agent.free_slot(db, participant.id, meeting.start_time)

        db.commit()
        logger.info(f"Meeting {meeting_id} cancelled and slots freed.")
        return True

    def get_meeting(self, db: Session, meeting_id: int) -> Optional[Meeting]:
        return db.query(Meeting).filter(Meeting.id == meeting_id).first()

    def list_meetings(
        self,
        db: Session,
        employee_id: Optional[int] = None,
        status: Optional[str] = None,
    ) -> List[Meeting]:
        """List all (or filtered) meetings."""
        query = db.query(Meeting)
        if employee_id:
            query = query.join(meeting_participants).filter(
                meeting_participants.c.employee_id == employee_id
            )
        if status:
            query = query.filter(Meeting.status == status)
        return query.order_by(Meeting.start_time).all()

    def mark_completed(self, db: Session, meeting_id: int) -> bool:
        """Mark a meeting as completed."""
        meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
        if meeting:
            meeting.status = "completed"
            db.commit()
            return True
        return False


# Module-level singleton
booking_agent = BookingAgent()
