"""
MeetSmart AI — Availability API routes.
"""

from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from src.db.database import get_db
from src.agents.availability_agent import availability_agent
from src.api.models import EmployeeOut, SlotOut, OverlapSlotOut, AvailabilityRequest, WeeklyGridRequest
from src.db.seed import refresh_slots

from pydantic import BaseModel as PydanticBase

class EmployeeCreate(PydanticBase):
    name: str
    email: str
    department: str
    role: str
    timezone: str = "Asia/Kolkata"
    avatar_initials: str = ""

router = APIRouter(prefix="/api/availability", tags=["Availability"])


@router.get("/employees", response_model=List[EmployeeOut])
def list_employees(db: Session = Depends(get_db)):
    """Return all employees in the system."""
    return availability_agent.list_employees(db)


@router.post("/employees", response_model=EmployeeOut, status_code=201)
def create_employee(data: EmployeeCreate, db: Session = Depends(get_db)):
    """Add a new employee and generate 14 days of availability slots for them."""
    from src.db.models import Employee
    from src.db.seed import generate_slots_for_employee
    from datetime import date

    # Check for duplicate email
    existing = db.query(Employee).filter(Employee.email == data.email).first()
    if existing:
        raise HTTPException(status_code=409, detail=f"Employee with email '{data.email}' already exists.")

    emp = Employee(
        name=data.name,
        email=data.email,
        department=data.department,
        role=data.role,
        timezone=data.timezone,
        avatar_initials=data.avatar_initials or (data.name[0].upper() + (data.name.split()[-1][0].upper() if len(data.name.split()) > 1 else "")),
    )
    db.add(emp)
    db.flush()  # get the auto-generated id

    # Auto-generate 14 days of slots
    slots = generate_slots_for_employee(emp.id, date.today(), days=14)
    db.bulk_save_objects(slots)
    db.commit()
    db.refresh(emp)
    return emp


@router.get("/employees/{employee_id}", response_model=EmployeeOut)
def get_employee(employee_id: int, db: Session = Depends(get_db)):
    emp = availability_agent.get_employee(db, employee_id)
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")
    return emp


@router.get("/slots/{employee_id}", response_model=List[SlotOut])
def get_slots(
    employee_id: int,
    from_date: Optional[date] = Query(None),
    to_date: Optional[date] = Query(None),
    only_available: bool = Query(True),
    db: Session = Depends(get_db),
):
    """Return availability slots for a single employee."""
    emp = availability_agent.get_employee(db, employee_id)
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")
    return availability_agent.get_slots(db, employee_id, from_date, to_date, only_available)


@router.post("/overlap", response_model=List[OverlapSlotOut])
def get_overlap(req: AvailabilityRequest, db: Session = Depends(get_db)):
    """Find overlapping free slots across multiple employees."""
    if len(req.employee_ids) < 1:
        raise HTTPException(status_code=400, detail="At least one employee_id required")
    return availability_agent.get_overlap_slots(
        db,
        req.employee_ids,
        req.from_date,
        req.to_date,
        req.duration_minutes,
    )


@router.post("/grid")
def get_weekly_grid(req: WeeklyGridRequest, db: Session = Depends(get_db)):
    """Return a weekly availability grid for the booking UI."""
    return availability_agent.get_weekly_grid(db, req.employee_ids, req.week_start)


@router.post("/refresh-slots")
def do_refresh_slots(db: Session = Depends(get_db)):
    """
    Delete all future available slots and regenerate from today (+14 days).
    Useful when demo slots have expired.
    """
    employees = availability_agent.list_employees(db)
    if not employees:
        raise HTTPException(status_code=404, detail="No employees found. Run seed first.")
    count = refresh_slots(db, employees, days=14)
    return {"status": "ok", "slots_generated": count, "message": f"Refreshed {count} slots from today."}
