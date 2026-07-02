"""
MeetSmart AI — Database seeder.
Populates 6 demo ThinkPalm employees with realistic availability slots
for the next 14 days (Mon–Fri, 9 AM – 5 PM, 1-hour slots).

Run this anytime to refresh expired slots:
    python3 src/db/seed.py --refresh
"""

import sys
import os
import argparse
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from datetime import datetime, timedelta, date
import random

from src.db.database import engine, SessionLocal, init_db
from src.db.models import Employee, Slot


EMPLOYEES = [
    {"name": "Arjun Sharma",   "email": "arjun.sharma@thinkpalm.com",   "department": "Engineering", "role": "Senior Software Engineer", "timezone": "Asia/Kolkata", "avatar_initials": "AS"},
    {"name": "Priya Nair",     "email": "priya.nair@thinkpalm.com",     "department": "Product",     "role": "Product Manager",          "timezone": "Asia/Kolkata", "avatar_initials": "PN"},
    {"name": "Rahul Menon",    "email": "rahul.menon@thinkpalm.com",    "department": "Engineering", "role": "DevOps Engineer",          "timezone": "Asia/Kolkata", "avatar_initials": "RM"},
    {"name": "Divya Krishnan", "email": "divya.krishnan@thinkpalm.com", "department": "Design",      "role": "UX Designer",              "timezone": "Asia/Kolkata", "avatar_initials": "DK"},
    {"name": "Sanjay Pillai",  "email": "sanjay.pillai@thinkpalm.com",  "department": "Management",  "role": "Engineering Manager",      "timezone": "Asia/Kolkata", "avatar_initials": "SP"},
    {"name": "Meera Thomas",   "email": "meera.thomas@thinkpalm.com",   "department": "QA",          "role": "QA Lead",                  "timezone": "Asia/Kolkata", "avatar_initials": "MT"},
]


def generate_slots_for_employee(employee_id: int, start_date: date, days: int = 14):
    """Generate 1-hour slots Mon–Fri, 9 AM–5 PM for `days` days from start_date."""
    slots = []
    random.seed(employee_id * 1000 + start_date.toordinal())  # deterministic per employee+date
    for day_offset in range(days):
        current_date = start_date + timedelta(days=day_offset)
        if current_date.weekday() >= 5:   # skip weekends
            continue
        for hour in range(9, 17):         # 9 AM – 4 PM (last slot 4–5 PM)
            is_available = random.random() > 0.2  # ~80% available
            slot_start = datetime(current_date.year, current_date.month, current_date.day, hour, 0, 0)
            slot_end   = slot_start + timedelta(hours=1)
            slots.append(Slot(
                employee_id=employee_id,
                start_time=slot_start,
                end_time=slot_end,
                is_available=is_available,
            ))
    return slots


def refresh_slots(db, employees, days: int = 14):
    """Delete all future unbooked slots and regenerate from today."""
    today = datetime.now()

    # Delete only future unbooked slots (keep booked/past for history)
    deleted = (
        db.query(Slot)
        .filter(Slot.start_time >= today, Slot.is_available == True)
        .delete(synchronize_session=False)
    )
    db.commit()
    print(f"🗑️  Cleared {deleted} stale future slots.")

    today_date = date.today()
    all_slots = []
    for emp in employees:
        all_slots.extend(generate_slots_for_employee(emp.id, today_date, days=days))

    db.bulk_save_objects(all_slots)
    db.commit()
    print(f"✅ Generated {len(all_slots)} fresh slots from {today_date} (+{days} days).")
    return len(all_slots)


def seed(force_refresh: bool = False):
    print("⚙️  Initialising database tables...")
    init_db()

    db = SessionLocal()
    try:
        existing_employees = db.query(Employee).all()

        if existing_employees and not force_refresh:
            # Check if we have any future slots
            future_count = (
                db.query(Slot)
                .filter(Slot.start_time >= datetime.now(), Slot.is_available == True)
                .count()
            )
            if future_count > 0:
                print(f"✅ Database already seeded — {future_count} future slots available. Skipping.")
                return
            else:
                print("⚠️  All slots are in the past — refreshing slots...")
                refresh_slots(db, existing_employees)
                return

        if existing_employees and force_refresh:
            print("🔄 Force refresh: regenerating all slots...")
            refresh_slots(db, existing_employees)
            return

        # First-time seed
        print("🌱 Seeding employees...")
        employees = []
        for emp_data in EMPLOYEES:
            emp = Employee(**emp_data)
            db.add(emp)
            db.flush()
            employees.append(emp)

        print("📅 Generating availability slots...")
        all_slots = []
        for emp in employees:
            all_slots.extend(generate_slots_for_employee(emp.id, date.today(), days=14))

        db.bulk_save_objects(all_slots)
        db.commit()

        print(f"✅ Seeded {len(employees)} employees and {len(all_slots)} availability slots.")
        print("\n👤 Employees:")
        for emp in employees:
            print(f"   [{emp.id}] {emp.name} ({emp.role}) — {emp.email}")

    except Exception as e:
        db.rollback()
        print(f"❌ Seeding failed: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--refresh", action="store_true", help="Force refresh all slots from today")
    args = parser.parse_args()
    seed(force_refresh=args.refresh)
