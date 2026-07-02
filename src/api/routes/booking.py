"""
MeetSmart AI — Booking API routes.
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session

from src.db.database import get_db
from src.agents.booking_agent import booking_agent
from src.agents.invite_agent import invite_agent
from src.agents.reminder_agent import reminder_agent
from src.api.models import BookingRequest, MeetingOut, SuccessResponse

router = APIRouter(prefix="/api/booking", tags=["Booking"])


@router.post("/book", response_model=MeetingOut)
def book_meeting(
    req: BookingRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """
    Book a meeting:
    1. Find optimal slot (or use provided start_time).
    2. Create meeting record.
    3. In background: generate .ics invite and send emails.
    4. Schedule reminders.
    """
    meeting = booking_agent.book_meeting(
        db=db,
        title=req.title,
        agenda=req.agenda,
        organizer_id=req.organizer_id,
        participant_ids=req.participant_ids,
        start_time=req.start_time,
        duration_minutes=req.duration_minutes,
        location=req.location,
        preferred_date=req.preferred_date,
    )

    if meeting is None:
        raise HTTPException(
            status_code=409,
            detail="No common available slot found for the selected participants and date range.",
        )

    meeting_id = meeting.id
    start_time = meeting.start_time

    # Send invite in background
    background_tasks.add_task(invite_agent.generate_and_send, db, meeting_id)

    # Schedule reminders
    try:
        reminder_agent.schedule_meeting_reminders(meeting_id, start_time)
    except Exception as e:
        pass  # Non-critical — reminders are best-effort

    # Refresh to load relationships
    db.refresh(meeting)
    return meeting


@router.post("/cancel/{meeting_id}", response_model=SuccessResponse)
def cancel_meeting(meeting_id: int, db: Session = Depends(get_db)):
    """Cancel a meeting and free all participant slots."""
    success = booking_agent.cancel_meeting(db, meeting_id)
    if not success:
        raise HTTPException(status_code=404, detail="Meeting not found")
    reminder_agent.cancel_reminders(meeting_id)
    return SuccessResponse(success=True, message=f"Meeting {meeting_id} cancelled.")


@router.post("/complete/{meeting_id}", response_model=SuccessResponse)
def complete_meeting(meeting_id: int, db: Session = Depends(get_db)):
    """Mark a meeting as completed."""
    success = booking_agent.mark_completed(db, meeting_id)
    if not success:
        raise HTTPException(status_code=404, detail="Meeting not found")
    return SuccessResponse(success=True, message=f"Meeting {meeting_id} marked as completed.")
