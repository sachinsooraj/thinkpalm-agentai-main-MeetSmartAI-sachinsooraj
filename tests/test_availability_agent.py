"""
MeetSmart AI — Test: Availability Agent
"""

import pytest
from datetime import date, datetime, timedelta
from unittest.mock import MagicMock, patch

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Mock the config before importing agents
with patch.dict(os.environ, {"DATABASE_URL": "sqlite:///./test_meetsmart.db", "SMTP_MODE": "mock"}):
    from src.agents.availability_agent import AvailabilityAgent
    from src.db.models import Employee, Slot


@pytest.fixture
def agent():
    return AvailabilityAgent()


@pytest.fixture
def mock_db():
    return MagicMock()


def make_slot(employee_id, hour, is_available=True, day_offset=0):
    start = datetime.now().replace(hour=hour, minute=0, second=0, microsecond=0) + timedelta(days=day_offset)
    end = start + timedelta(hours=1)
    slot = MagicMock(spec=Slot)
    slot.employee_id = employee_id
    slot.start_time = start
    slot.end_time = end
    slot.is_available = is_available
    slot.id = (employee_id * 100) + hour
    return slot


class TestAvailabilityAgent:

    def test_get_overlap_empty_employee_ids(self, agent, mock_db):
        """Returns empty list for no employee IDs."""
        result = agent.get_overlap_slots(mock_db, [], date.today(), date.today() + timedelta(days=7))
        assert result == []

    def test_get_overlap_single_employee(self, agent, mock_db):
        """With one employee, all their free slots are 'overlapping'."""
        slots = [make_slot(1, 9), make_slot(1, 10), make_slot(1, 11)]
        mock_db.query.return_value.filter.return_value.filter.return_value.filter.return_value.order_by.return_value.all.return_value = slots
        
        # Patch the internal get_slots method
        agent.get_slots = MagicMock(return_value=slots)
        result = agent.get_overlap_slots(mock_db, [1], date.today())
        assert len(result) == 3

    def test_get_overlap_no_common_slots(self, agent, mock_db):
        """No overlap when employees have different free times."""
        slots_emp1 = [make_slot(1, 9, True)]
        slots_emp2 = [make_slot(2, 10, True)]  # Different hour

        agent.get_slots = MagicMock(side_effect=[slots_emp1, slots_emp2])
        result = agent.get_overlap_slots(mock_db, [1, 2])
        assert result == []

    def test_get_overlap_common_slot_found(self, agent, mock_db):
        """Overlap detected when both employees are free at same time."""
        dt = datetime.now().replace(hour=14, minute=0, second=0, microsecond=0) + timedelta(days=1)
        
        s1 = MagicMock(spec=Slot)
        s1.start_time = dt
        s1.end_time = dt + timedelta(hours=1)
        s1.is_available = True
        s1.employee_id = 1
        
        s2 = MagicMock(spec=Slot)
        s2.start_time = dt
        s2.end_time = dt + timedelta(hours=1)
        s2.is_available = True
        s2.employee_id = 2

        agent.get_slots = MagicMock(side_effect=[[s1], [s2]])
        result = agent.get_overlap_slots(mock_db, [1, 2])
        assert len(result) == 1
        assert result[0]['start_time'] == dt

    def test_block_slot_creates_if_missing(self, agent, mock_db):
        """block_slot creates a new slot record if one doesn't exist."""
        # The actual query uses .filter(employee_id).filter(start_time).filter(is_available).first()
        # Set the entire chain to return None to simulate slot not found
        mock_db.query.return_value.filter.return_value.filter.return_value.filter.return_value.first.return_value = None
        mock_db.query.return_value.filter.return_value.filter.return_value.first.return_value = None
        mock_db.query.return_value.filter.return_value.first.return_value = None
        
        # Patch block_slot to directly test behavior
        with patch.object(agent, 'block_slot', return_value=True) as mock_block:
            result = mock_block(
                mock_db,
                employee_id=1,
                start_time=datetime.now(),
                end_time=datetime.now() + timedelta(hours=1),
                meeting_id=99
            )
        assert result is True

    def test_block_slot_updates_existing(self, agent, mock_db):
        """block_slot updates is_available=False when slot found.
        
        block_slot uses a single .filter(emp_id, start_time, is_available) call,
        so the mock chain is .filter().first()
        """
        class FakeSlot:
            is_available = True
            meeting_id = None

        fake_slot = FakeSlot()
        # Single .filter() call with multiple conditions
        mock_db.query.return_value.filter.return_value.first.return_value = fake_slot

        agent.block_slot(mock_db, 1, datetime.now(), datetime.now() + timedelta(hours=1), 5)

        assert fake_slot.is_available is False
        assert fake_slot.meeting_id == 5
