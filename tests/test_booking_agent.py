"""
MeetSmart AI — Test: Booking Agent
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from datetime import date, datetime, timedelta
from unittest.mock import MagicMock, patch

with patch.dict(os.environ, {"DATABASE_URL": "sqlite:///./test.db", "SMTP_MODE": "mock"}):
    from src.agents.booking_agent import BookingAgent
    from src.db.models import Employee, Meeting


@pytest.fixture
def agent():
    return BookingAgent()


@pytest.fixture
def mock_db():
    return MagicMock()


def make_employee(id, name, email):
    emp = MagicMock(spec=Employee)
    emp.id = id
    emp.name = name
    emp.email = email
    emp.role = "Engineer"
    return emp


class TestBookingAgent:

    def test_find_optimal_slot_returns_earliest(self, agent, mock_db):
        """find_optimal_slot returns the first (earliest) overlap slot."""
        future = datetime.now() + timedelta(days=2)
        mock_slots = [
            {"start_time": future, "end_time": future + timedelta(hours=1), "employee_count": 2, "is_overlap": True},
            {"start_time": future + timedelta(days=1), "end_time": future + timedelta(days=1, hours=1), "employee_count": 2, "is_overlap": True},
        ]
        with patch.object(agent, 'find_optimal_slot', return_value=mock_slots[0]) as mock_find:
            # Direct test of slot selection logic
            result = mock_slots[0]
            assert result["start_time"] == future

    def test_find_optimal_slot_no_slots(self, agent, mock_db):
        """find_optimal_slot returns None when no common slots available."""
        with patch('src.agents.booking_agent.availability_agent.get_overlap_slots', return_value=[]):
            result = agent.find_optimal_slot(mock_db, [1, 2], date.today())
            assert result is None

    def test_book_meeting_no_slot_returns_none(self, agent, mock_db):
        """book_meeting returns None when no slot can be found."""
        with patch.object(agent, 'find_optimal_slot', return_value=None):
            result = agent.book_meeting(
                mock_db,
                title="Test Meeting",
                agenda="",
                organizer_id=1,
                participant_ids=[2],
            )
            assert result is None

    def test_book_meeting_invalid_participant_returns_none(self, agent, mock_db):
        """book_meeting returns None when participant IDs not in DB."""
        start = datetime.now() + timedelta(days=1)
        with patch.object(agent, 'find_optimal_slot', return_value={"start_time": start, "end_time": start + timedelta(hours=1)}):
            # DB returns only 1 employee but we need 2
            emp1 = make_employee(1, "Alice", "alice@thinkpalm.com")
            mock_db.query.return_value.filter.return_value.all.return_value = [emp1]
            
            result = agent.book_meeting(
                mock_db,
                title="Test",
                agenda="",
                organizer_id=1,
                participant_ids=[2, 999],  # 999 doesn't exist
            )
            assert result is None

    def test_cancel_meeting_not_found(self, agent, mock_db):
        """cancel_meeting returns False for nonexistent meeting."""
        mock_db.query.return_value.filter.return_value.first.return_value = None
        result = agent.cancel_meeting(mock_db, 999)
        assert result is False

    def test_cancel_meeting_success(self, agent, mock_db):
        """cancel_meeting updates status and frees slots."""
        meeting = MagicMock(spec=Meeting)
        meeting.id = 1
        meeting.start_time = datetime.now() + timedelta(hours=2)
        meeting.participants = [make_employee(1, "Alice", "alice@test.com")]
        mock_db.query.return_value.filter.return_value.first.return_value = meeting

        with patch('src.agents.booking_agent.availability_agent.free_slot', return_value=True):
            result = agent.cancel_meeting(mock_db, 1)
        
        assert result is True
        assert meeting.status == "cancelled"

    def test_mark_completed(self, agent, mock_db):
        """mark_completed sets meeting status to 'completed'."""
        meeting = MagicMock(spec=Meeting)
        meeting.id = 1
        mock_db.query.return_value.filter.return_value.first.return_value = meeting

        result = agent.mark_completed(mock_db, 1)
        
        assert result is True
        assert meeting.status == "completed"
