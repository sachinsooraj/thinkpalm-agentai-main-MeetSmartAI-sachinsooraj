"""
MeetSmart AI — Reminder Agent.
Uses APScheduler to send:
  - Pre-meeting reminders (24h and 1h before)
  - Post-meeting action item follow-ups (24h after, for pending items)
"""

import logging
from datetime import datetime, timedelta
from typing import List

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.date import DateTrigger
from sqlalchemy.orm import Session

from src.db.database import SessionLocal
from src.db.models import Meeting, ActionItem, Employee
from src.services.email_service import send_email, reminder_html, action_followup_html

logger = logging.getLogger(__name__)


class ReminderAgent:
    """
    Manages scheduled reminders and follow-ups.
    Uses APScheduler BackgroundScheduler so it runs in-process with FastAPI.
    """

    def __init__(self):
        self.scheduler = BackgroundScheduler(timezone="Asia/Kolkata")

    def start(self):
        """Start the scheduler (called at app startup)."""
        self.scheduler.start()
        logger.info("⏰ Reminder Agent scheduler started.")

    def stop(self):
        """Shutdown the scheduler gracefully."""
        if self.scheduler.running:
            self.scheduler.shutdown(wait=False)
            logger.info("⏰ Reminder Agent scheduler stopped.")

    def schedule_meeting_reminders(self, meeting_id: int, start_time: datetime):
        """Schedule 24h and 1h pre-meeting reminders, plus 24h post-meeting follow-up."""
        now = datetime.now()

        # 24-hour reminder
        remind_24h = start_time - timedelta(hours=24)
        if remind_24h > now:
            self.scheduler.add_job(
                self._send_pre_reminder,
                trigger=DateTrigger(run_date=remind_24h),
                args=[meeting_id, "24 hours"],
                id=f"remind_24h_{meeting_id}",
                replace_existing=True,
            )
            logger.info(f"Scheduled 24h reminder for meeting {meeting_id} at {remind_24h}")

        # 1-hour reminder
        remind_1h = start_time - timedelta(hours=1)
        if remind_1h > now:
            self.scheduler.add_job(
                self._send_pre_reminder,
                trigger=DateTrigger(run_date=remind_1h),
                args=[meeting_id, "1 hour"],
                id=f"remind_1h_{meeting_id}",
                replace_existing=True,
            )
            logger.info(f"Scheduled 1h reminder for meeting {meeting_id} at {remind_1h}")

        # Post-meeting follow-up (24h after)
        followup_time = start_time + timedelta(hours=24)
        if followup_time > now:
            self.scheduler.add_job(
                self._send_action_followup,
                trigger=DateTrigger(run_date=followup_time),
                args=[meeting_id],
                id=f"followup_{meeting_id}",
                replace_existing=True,
            )
            logger.info(f"Scheduled follow-up for meeting {meeting_id} at {followup_time}")

    def cancel_reminders(self, meeting_id: int):
        """Remove all scheduled jobs for a meeting (e.g., when cancelled)."""
        for job_id in [f"remind_24h_{meeting_id}", f"remind_1h_{meeting_id}", f"followup_{meeting_id}"]:
            try:
                self.scheduler.remove_job(job_id)
            except Exception:
                pass

    def _send_pre_reminder(self, meeting_id: int, time_until: str):
        """Send a pre-meeting reminder to all participants."""
        db = SessionLocal()
        try:
            meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
            if not meeting or meeting.status != "scheduled":
                return

            to_emails = [p.email for p in meeting.participants]
            html = reminder_html(
                meeting_title=meeting.title,
                start_time=meeting.start_time.strftime("%A, %d %B %Y  %I:%M %p IST"),
                participants=[p.name for p in meeting.participants],
                time_until=time_until,
            )
            send_email(
                to_emails=to_emails,
                subject=f"[MeetSmart AI] ⏰ Reminder: {meeting.title} starts in {time_until}",
                html_body=html,
            )
            logger.info(f"Pre-meeting reminder ({time_until}) sent for meeting [{meeting_id}]")
        finally:
            db.close()

    def _send_action_followup(self, meeting_id: int):
        """Send action item follow-up emails to each owner with their pending items."""
        db = SessionLocal()
        try:
            meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
            if not meeting:
                return

            # Group pending action items by owner
            pending_items = (
                db.query(ActionItem)
                .filter(
                    ActionItem.meeting_id == meeting_id,
                    ActionItem.status == "pending",
                )
                .all()
            )

            if not pending_items:
                logger.info(f"No pending action items for meeting [{meeting_id}] — skip follow-up.")
                return

            # Group by owner_id
            owner_map: dict = {}
            for item in pending_items:
                key = item.owner_id or 0
                if key not in owner_map:
                    owner_map[key] = {"name": item.owner_name or "Team", "email": None, "items": []}
                owner_map[key]["items"].append({
                    "description": item.description,
                    "deadline": item.deadline.strftime("%Y-%m-%d") if item.deadline else "TBD",
                    "status": item.status,
                })

            # Fill in email for known owners
            for participant in meeting.participants:
                if participant.id in owner_map:
                    owner_map[participant.id]["email"] = participant.email

            # Send one email per owner
            for owner_id, data in owner_map.items():
                email = data.get("email")
                if not email:
                    continue
                html = action_followup_html(
                    recipient_name=data["name"],
                    action_items=data["items"],
                )
                send_email(
                    to_emails=[email],
                    subject=f"[MeetSmart AI] 📋 Pending Action Items — {meeting.title}",
                    html_body=html,
                )
                logger.info(f"Action follow-up sent to {email} ({len(data['items'])} items)")

        finally:
            db.close()

    def send_test_reminder(self, meeting_id: int):
        """Immediately send a test reminder (useful for demo)."""
        self._send_pre_reminder(meeting_id, "NOW (test)")


# Module-level singleton
reminder_agent = ReminderAgent()
