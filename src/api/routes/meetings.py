"""
MeetSmart AI — Meetings list/detail API routes.
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from src.db.database import get_db
from src.agents.booking_agent import booking_agent
from src.api.models import MeetingOut, ActionItemOut, ActionStatusUpdate, SuccessResponse
from src.db.models import ActionItem

router = APIRouter(prefix="/api/meetings", tags=["Meetings"])


@router.get("/", response_model=List[MeetingOut])
def list_meetings(
    employee_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """List all meetings, optionally filtered by employee or status."""
    return booking_agent.list_meetings(db, employee_id, status)


@router.get("/{meeting_id}", response_model=MeetingOut)
def get_meeting(meeting_id: int, db: Session = Depends(get_db)):
    """Get a single meeting by ID."""
    meeting = booking_agent.get_meeting(db, meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    return meeting


@router.get("/{meeting_id}/action-items", response_model=List[ActionItemOut])
def get_action_items(meeting_id: int, db: Session = Depends(get_db)):
    """Return all action items for a meeting."""
    meeting = booking_agent.get_meeting(db, meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    items = db.query(ActionItem).filter(ActionItem.meeting_id == meeting_id).all()
    return items


@router.patch("/action-items/{item_id}/status", response_model=SuccessResponse)
def update_action_status(
    item_id: int,
    update: ActionStatusUpdate,
    db: Session = Depends(get_db),
):
    """Update the status of an action item."""
    valid_statuses = {"pending", "in_progress", "done"}
    if update.status not in valid_statuses:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status. Must be one of: {', '.join(valid_statuses)}",
        )
    item = db.query(ActionItem).filter(ActionItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Action item not found")
    item.status = update.status
    db.commit()
    return SuccessResponse(success=True, message=f"Action item {item_id} updated to '{update.status}'")
