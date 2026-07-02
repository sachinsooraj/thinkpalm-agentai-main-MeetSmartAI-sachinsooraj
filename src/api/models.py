"""
MeetSmart AI — Pydantic request/response schemas.
"""

from datetime import datetime, date
from typing import List, Optional
from pydantic import BaseModel, EmailStr


# ── Employee schemas ─────────────────────────────────────────────────────────

class EmployeeOut(BaseModel):
    id: int
    name: str
    email: str
    department: str
    role: str
    timezone: str
    avatar_initials: Optional[str] = None

    class Config:
        from_attributes = True


# ── Slot schemas ─────────────────────────────────────────────────────────────

class SlotOut(BaseModel):
    id: int
    employee_id: int
    start_time: datetime
    end_time: datetime
    is_available: bool

    class Config:
        from_attributes = True


class OverlapSlotOut(BaseModel):
    start_time: datetime
    end_time: datetime
    employee_count: int
    is_overlap: bool


# ── Availability schemas ──────────────────────────────────────────────────────

class AvailabilityRequest(BaseModel):
    employee_ids: List[int]
    from_date: Optional[date] = None
    to_date: Optional[date] = None
    duration_minutes: int = 60


class WeeklyGridRequest(BaseModel):
    employee_ids: List[int]
    week_start: date


# ── Booking schemas ───────────────────────────────────────────────────────────

class BookingRequest(BaseModel):
    title: str
    agenda: str = ""
    organizer_id: int
    participant_ids: List[int]
    duration_minutes: int = 60
    preferred_date: Optional[date] = None
    start_time: Optional[datetime] = None
    location: str = "Google Meet / Teams"


class MeetingOut(BaseModel):
    id: int
    title: str
    agenda: Optional[str]
    start_time: datetime
    end_time: datetime
    location: str
    status: str
    organizer: EmployeeOut
    participants: List[EmployeeOut]
    ics_path: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


# ── Notes schemas ─────────────────────────────────────────────────────────────

class NotesRequest(BaseModel):
    meeting_id: int
    transcript: str


class ActionItemOut(BaseModel):
    id: int
    meeting_id: int
    description: str
    owner_name: Optional[str]
    deadline: Optional[datetime]
    status: str
    priority: str

    class Config:
        from_attributes = True


class NotesResult(BaseModel):
    meeting_id: int
    meeting_title: str
    summary: str
    decisions: List[str]
    action_items: List[dict]
    key_topics: List[str]
    mode: str


# ── Action Item update ────────────────────────────────────────────────────────

class ActionStatusUpdate(BaseModel):
    status: str  # pending | in_progress | done


# ── Generic responses ─────────────────────────────────────────────────────────

class SuccessResponse(BaseModel):
    success: bool
    message: str


class HealthResponse(BaseModel):
    status: str
    app: str
    version: str
    gemini_enabled: bool
    smtp_mode: str
