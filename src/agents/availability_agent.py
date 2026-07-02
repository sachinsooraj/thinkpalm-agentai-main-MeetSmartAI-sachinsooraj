"""
MeetSmart AI — Availability Agent.
Reads/writes the SQLite slots table to:
  - surface open slots for one employee
  - find overlapping free slots across multiple employees
"""

from datetime import datetime, date, timedelta
from typing import List, Optional, Dict
import logging

from sqlalchemy.orm import Session

from src.db.models import Employee, Slot, Meeting

logger = logging.getLogger(__name__)


class AvailabilityAgent:
    """
    Manages employee availability slots.
    All methods work synchronously over a SQLAlchemy session.
    """

    def get_employee(self, db: Session, employee_id: int) -> Optional[Employee]:
        return db.query(Employee).filter(Employee.id == employee_id).first()

    def list_employees(self, db: Session) -> List[Employee]:
        return db.query(Employee).order_by(Employee.name).all()

    def get_slots(
        self,
        db: Session,
        employee_id: int,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
        only_available: bool = True,
    ) -> List[Slot]:
        """Return slots for a single employee, optionally filtered by date range."""
        query = db.query(Slot).filter(Slot.employee_id == employee_id)

        if only_available:
            query = query.filter(Slot.is_available == True)

        if from_date:
            from_dt = datetime(from_date.year, from_date.month, from_date.day, 0, 0, 0)
            query = query.filter(Slot.start_time >= from_dt)

        if to_date:
            to_dt = datetime(to_date.year, to_date.month, to_date.day, 23, 59, 59)
            query = query.filter(Slot.end_time <= to_dt)

        return query.order_by(Slot.start_time).all()

    def get_overlap_slots(
        self,
        db: Session,
        employee_ids: List[int],
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
        duration_minutes: int = 60,
    ) -> List[Dict]:
        """
        Find time slots where ALL listed employees are free simultaneously.
        Returns list of {start_time, end_time, employee_count} dicts.
        """
        if not employee_ids:
            return []

        # Fetch available slots for each employee
        all_slots: Dict[int, List[Slot]] = {}
        for eid in employee_ids:
            all_slots[eid] = self.get_slots(db, eid, from_date, to_date, only_available=True)

        if not all(all_slots.values()):
            return []

        # Build a set of (start_time) → count of available employees
        slot_map: Dict[datetime, int] = {}
        for eid, slots in all_slots.items():
            for slot in slots:
                key = slot.start_time
                slot_map[key] = slot_map.get(key, 0) + 1

        # Find slots where all employees are free
        n = len(employee_ids)
        overlapping = []
        for start_time, count in sorted(slot_map.items()):
            if count == n:
                end_time = start_time + timedelta(minutes=duration_minutes)
                overlapping.append({
                    "start_time": start_time,
                    "end_time": end_time,
                    "employee_count": count,
                    "is_overlap": True,
                })

        logger.info(
            f"Availability overlap: {len(overlapping)} common slots for "
            f"employees {employee_ids}"
        )
        return overlapping

    def block_slot(
        self,
        db: Session,
        employee_id: int,
        start_time: datetime,
        end_time: datetime,
        meeting_id: int,
    ) -> bool:
        """Mark an employee's slot as unavailable (booked for a meeting)."""
        slot = (
            db.query(Slot)
            .filter(
                Slot.employee_id == employee_id,
                Slot.start_time == start_time,
                Slot.is_available == True,
            )
            .first()
        )
        if not slot:
            # Slot might not exist (e.g., if seeded differently) — create it
            slot = Slot(
                employee_id=employee_id,
                start_time=start_time,
                end_time=end_time,
                is_available=False,
                meeting_id=meeting_id,
            )
            db.add(slot)
        else:
            slot.is_available = False
            slot.meeting_id = meeting_id

        db.commit()
        return True

    def free_slot(
        self,
        db: Session,
        employee_id: int,
        start_time: datetime,
    ) -> bool:
        """Re-open a slot (e.g., meeting cancelled)."""
        slot = (
            db.query(Slot)
            .filter(Slot.employee_id == employee_id, Slot.start_time == start_time)
            .first()
        )
        if slot:
            slot.is_available = True
            slot.meeting_id = None
            db.commit()
            return True
        return False

    def add_slots(
        self,
        db: Session,
        employee_id: int,
        slots: List[Dict],   # [{"start_time": datetime, "end_time": datetime}]
    ) -> int:
        """Add new availability slots for an employee. Returns count added."""
        added = 0
        for s in slots:
            existing = (
                db.query(Slot)
                .filter(Slot.employee_id == employee_id, Slot.start_time == s["start_time"])
                .first()
            )
            if not existing:
                db.add(Slot(
                    employee_id=employee_id,
                    start_time=s["start_time"],
                    end_time=s["end_time"],
                    is_available=True,
                ))
                added += 1

        db.commit()
        return added

    def get_weekly_grid(
        self,
        db: Session,
        employee_ids: List[int],
        week_start: date,
    ) -> Dict:
        """
        Build a weekly availability grid for the UI.
        Returns {employee_id: {date_str: [{"hour": int, "available": bool}]}}
        """
        week_end = week_start + timedelta(days=6)
        grid = {}

        for eid in employee_ids:
            emp = self.get_employee(db, eid)
            if not emp:
                continue
            slots = self.get_slots(db, eid, week_start, week_end, only_available=False)
            employee_grid: Dict[str, List] = {}

            for slot in slots:
                date_key = slot.start_time.strftime("%Y-%m-%d")
                if date_key not in employee_grid:
                    employee_grid[date_key] = []
                employee_grid[date_key].append({
                    "hour": slot.start_time.hour,
                    "available": slot.is_available,
                    "slot_id": slot.id,
                })

            grid[eid] = {
                "employee": {"id": emp.id, "name": emp.name, "role": emp.role, "initials": emp.avatar_initials},
                "slots": employee_grid,
            }

        return grid


# Module-level singleton
availability_agent = AvailabilityAgent()
