"""
MeetSmart AI — SQLAlchemy ORM models.
Tables: employees, slots, meetings, meeting_participants, action_items, notes
"""

from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime,
    ForeignKey, Text, Table,
)
from sqlalchemy.orm import relationship
from src.db.database import Base

# ── Many-to-Many: meetings ↔ employees ──────────────────────────────────────
meeting_participants = Table(
    "meeting_participants",
    Base.metadata,
    Column("meeting_id", Integer, ForeignKey("meetings.id"), primary_key=True),
    Column("employee_id", Integer, ForeignKey("employees.id"), primary_key=True),
)


class Employee(Base):
    __tablename__ = "employees"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    email = Column(String(200), unique=True, nullable=False)
    department = Column(String(100), nullable=False)
    role = Column(String(100), nullable=False)
    timezone = Column(String(50), default="Asia/Kolkata")
    avatar_initials = Column(String(4), nullable=True)  # e.g. "AS"

    slots = relationship("Slot", back_populates="employee", cascade="all, delete-orphan")
    organized_meetings = relationship("Meeting", back_populates="organizer")
    action_items = relationship("ActionItem", back_populates="owner")
    meetings = relationship("Meeting", secondary=meeting_participants, back_populates="participants")


class Slot(Base):
    __tablename__ = "slots"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    is_available = Column(Boolean, default=True)
    meeting_id = Column(Integer, ForeignKey("meetings.id"), nullable=True)

    employee = relationship("Employee", back_populates="slots")
    meeting = relationship("Meeting", foreign_keys=[meeting_id])


class Meeting(Base):
    __tablename__ = "meetings"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    agenda = Column(Text, nullable=True)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    organizer_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    status = Column(String(30), default="scheduled")  # scheduled | completed | cancelled
    ics_path = Column(String(500), nullable=True)
    location = Column(String(200), default="Google Meet / Teams")
    created_at = Column(DateTime, default=datetime.utcnow)

    organizer = relationship("Employee", back_populates="organized_meetings")
    participants = relationship("Employee", secondary=meeting_participants, back_populates="meetings")
    action_items = relationship("ActionItem", back_populates="meeting", cascade="all, delete-orphan")
    notes = relationship("MeetingNote", back_populates="meeting", cascade="all, delete-orphan")


class ActionItem(Base):
    __tablename__ = "action_items"

    id = Column(Integer, primary_key=True, index=True)
    meeting_id = Column(Integer, ForeignKey("meetings.id"), nullable=False)
    description = Column(Text, nullable=False)
    owner_id = Column(Integer, ForeignKey("employees.id"), nullable=True)
    owner_name = Column(String(100), nullable=True)   # denormalized for display
    deadline = Column(DateTime, nullable=True)
    status = Column(String(20), default="pending")    # pending | in_progress | done
    priority = Column(String(10), default="medium")   # low | medium | high
    created_at = Column(DateTime, default=datetime.utcnow)

    meeting = relationship("Meeting", back_populates="action_items")
    owner = relationship("Employee", back_populates="action_items")


class MeetingNote(Base):
    __tablename__ = "meeting_notes"

    id = Column(Integer, primary_key=True, index=True)
    meeting_id = Column(Integer, ForeignKey("meetings.id"), nullable=False)
    summary = Column(Text, nullable=True)
    decisions_json = Column(Text, nullable=True)   # JSON string: list of decision strings
    raw_transcript = Column(Text, nullable=True)
    mom_path = Column(String(500), nullable=True)  # path to saved .docx
    created_at = Column(DateTime, default=datetime.utcnow)

    meeting = relationship("Meeting", back_populates="notes")
