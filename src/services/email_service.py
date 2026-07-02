"""
MeetSmart AI — Email service.
Supports two modes (controlled by SMTP_MODE env var):
  - "mock"  → prints email content to console (no setup required)
  - "gmail" → sends real emails via Gmail SMTP + App Password
"""

import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from pathlib import Path
from typing import List, Optional
import logging

from src.utils.config import settings

logger = logging.getLogger(__name__)


def _build_message(
    to_emails: List[str],
    subject: str,
    html_body: str,
    attachments: Optional[List[Path]] = None,
    from_name: str = "MeetSmart AI",
) -> MIMEMultipart:
    msg = MIMEMultipart("mixed")
    msg["Subject"] = subject
    msg["From"] = f"{from_name} <{settings.GMAIL_ADDRESS or 'noreply@meetsmart.ai'}>"
    msg["To"] = ", ".join(to_emails)

    # HTML body
    alt_part = MIMEMultipart("alternative")
    alt_part.attach(MIMEText(html_body, "html"))
    msg.attach(alt_part)

    # Attachments
    if attachments:
        for filepath in attachments:
            filepath = Path(filepath)
            if not filepath.exists():
                logger.warning(f"Attachment not found: {filepath}")
                continue
            with open(filepath, "rb") as f:
                part = MIMEBase("application", "octet-stream")
                part.set_payload(f.read())
            encoders.encode_base64(part)
            part.add_header("Content-Disposition", f'attachment; filename="{filepath.name}"')
            msg.attach(part)

    return msg


def send_email(
    to_emails: List[str],
    subject: str,
    html_body: str,
    attachments: Optional[List[Path]] = None,
) -> bool:
    """Send email — mock mode prints to console, gmail mode sends real email."""
    msg = _build_message(to_emails, subject, html_body, attachments)

    if settings.SMTP_MODE == "mock":
        _mock_send(to_emails, subject, html_body, attachments)
        return True

    # Gmail SMTP
    try:
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
            server.login(settings.GMAIL_ADDRESS, settings.GMAIL_APP_PASSWORD)
            server.sendmail(settings.GMAIL_ADDRESS, to_emails, msg.as_string())
        logger.info(f"📧 Email sent to: {', '.join(to_emails)} | Subject: {subject}")
        return True
    except Exception as e:
        logger.error(f"❌ Email send failed: {e}")
        return False


def _mock_send(
    to_emails: List[str],
    subject: str,
    html_body: str,
    attachments: Optional[List[Path]] = None,
):
    """Print email to console — used in mock mode / demos."""
    border = "─" * 60
    attach_names = [Path(a).name for a in (attachments or [])]
    print(f"\n{'📧 MOCK EMAIL ':─<60}")
    print(f"  To      : {', '.join(to_emails)}")
    print(f"  Subject : {subject}")
    if attach_names:
        print(f"  Attach  : {', '.join(attach_names)}")
    print(border)
    # Strip HTML for console readability
    import re
    plain = re.sub(r"<[^>]+>", "", html_body).strip()
    # Truncate long bodies
    if len(plain) > 800:
        plain = plain[:800] + "\n  ... [truncated]"
    print(plain)
    print(f"{border}\n")


# ── Email templates ──────────────────────────────────────────────────────────

def meeting_invite_html(
    meeting_title: str,
    organizer_name: str,
    start_time: str,
    end_time: str,
    participants: List[str],
    agenda: str,
    location: str = "Google Meet / Teams",
) -> str:
    plist = "".join(f"<li>{p}</li>" for p in participants)
    return f"""
    <html><body style="font-family:Arial,sans-serif;background:#0f172a;color:#e2e8f0;padding:24px;">
    <div style="max-width:600px;margin:auto;background:#1e293b;border-radius:12px;padding:32px;border:1px solid #334155;">
      <div style="text-align:center;margin-bottom:24px;">
        <h1 style="color:#7c3aed;margin:0;">📅 MeetSmart AI</h1>
        <p style="color:#94a3b8;margin:4px 0;">ThinkPalm Internal Meeting Platform</p>
      </div>
      <h2 style="color:#f1f5f9;border-bottom:1px solid #334155;padding-bottom:12px;">{meeting_title}</h2>
      <table style="width:100%;border-collapse:collapse;">
        <tr><td style="padding:8px 0;color:#94a3b8;width:120px;">🕐 Start</td><td style="color:#f1f5f9;">{start_time}</td></tr>
        <tr><td style="padding:8px 0;color:#94a3b8;">🕔 End</td><td style="color:#f1f5f9;">{end_time}</td></tr>
        <tr><td style="padding:8px 0;color:#94a3b8;">👤 Organizer</td><td style="color:#f1f5f9;">{organizer_name}</td></tr>
        <tr><td style="padding:8px 0;color:#94a3b8;">📍 Location</td><td style="color:#f1f5f9;">{location}</td></tr>
      </table>
      <h3 style="color:#7c3aed;margin-top:24px;">Participants</h3>
      <ul style="color:#f1f5f9;">{plist}</ul>
      <h3 style="color:#7c3aed;">Agenda</h3>
      <p style="color:#f1f5f9;background:#0f172a;padding:16px;border-radius:8px;white-space:pre-wrap;">{agenda}</p>
      <p style="margin-top:24px;color:#64748b;font-size:12px;">
        This invite was generated by MeetSmart AI · ThinkPalm Internal · Please see the attached .ics file to add this to your calendar.
      </p>
    </div></body></html>
    """


def reminder_html(
    meeting_title: str,
    start_time: str,
    participants: List[str],
    time_until: str,
) -> str:
    return f"""
    <html><body style="font-family:Arial,sans-serif;background:#0f172a;color:#e2e8f0;padding:24px;">
    <div style="max-width:600px;margin:auto;background:#1e293b;border-radius:12px;padding:32px;border:1px solid #334155;">
      <h1 style="color:#f59e0b;">⏰ Meeting Reminder</h1>
      <h2 style="color:#f1f5f9;">{meeting_title}</h2>
      <p style="color:#94a3b8;">Your meeting starts in <strong style="color:#7c3aed;">{time_until}</strong></p>
      <p style="color:#94a3b8;">Scheduled: <strong style="color:#f1f5f9;">{start_time}</strong></p>
      <p style="color:#64748b;font-size:12px;margin-top:24px;">MeetSmart AI · ThinkPalm Internal</p>
    </div></body></html>
    """


def mom_delivery_html(
    meeting_title: str,
    date_str: str,
    participant_names: List[str],
    summary: str,
    action_count: int,
) -> str:
    plist = "".join(f"<li>{p}</li>" for p in participant_names)
    return f"""
    <html><body style="font-family:Arial,sans-serif;background:#0f172a;color:#e2e8f0;padding:24px;">
    <div style="max-width:600px;margin:auto;background:#1e293b;border-radius:12px;padding:32px;border:1px solid #334155;">
      <div style="text-align:center;margin-bottom:24px;">
        <h1 style="color:#7c3aed;">📄 Minutes of Meeting</h1>
        <p style="color:#94a3b8;">MeetSmart AI · ThinkPalm Internal</p>
      </div>
      <h2 style="color:#f1f5f9;border-bottom:1px solid #334155;padding-bottom:12px;">{meeting_title}</h2>
      <p style="color:#94a3b8;">Date: <strong style="color:#f1f5f9;">{date_str}</strong></p>
      <h3 style="color:#7c3aed;">Summary</h3>
      <p style="color:#f1f5f9;background:#0f172a;padding:16px;border-radius:8px;">{summary}</p>
      <h3 style="color:#7c3aed;">Participants</h3>
      <ul style="color:#f1f5f9;">{plist}</ul>
      <p style="color:#94a3b8;">📋 <strong style="color:#f59e0b;">{action_count} action item(s)</strong> have been identified. Please review the attached MoM document.</p>
      <p style="color:#64748b;font-size:12px;margin-top:24px;">The full Minutes of Meeting document is attached to this email as a Word document (.docx).</p>
    </div></body></html>
    """


def action_followup_html(
    recipient_name: str,
    action_items: List[dict],
) -> str:
    rows = "".join(
        f"""<tr>
          <td style="padding:8px;border-bottom:1px solid #334155;color:#f1f5f9;">{item.get('description','')}</td>
          <td style="padding:8px;border-bottom:1px solid #334155;color:#94a3b8;">{item.get('deadline','TBD')}</td>
          <td style="padding:8px;border-bottom:1px solid #334155;color:#f59e0b;">{item.get('status','pending')}</td>
        </tr>"""
        for item in action_items
    )
    return f"""
    <html><body style="font-family:Arial,sans-serif;background:#0f172a;color:#e2e8f0;padding:24px;">
    <div style="max-width:600px;margin:auto;background:#1e293b;border-radius:12px;padding:32px;border:1px solid #334155;">
      <h1 style="color:#ef4444;">📋 Action Item Follow-up</h1>
      <p style="color:#94a3b8;">Hi <strong style="color:#f1f5f9;">{recipient_name}</strong>, here are your pending action items:</p>
      <table style="width:100%;border-collapse:collapse;margin-top:16px;">
        <thead>
          <tr style="background:#0f172a;">
            <th style="padding:10px;text-align:left;color:#7c3aed;">Task</th>
            <th style="padding:10px;text-align:left;color:#7c3aed;">Deadline</th>
            <th style="padding:10px;text-align:left;color:#7c3aed;">Status</th>
          </tr>
        </thead>
        <tbody>{rows}</tbody>
      </table>
      <p style="color:#64748b;font-size:12px;margin-top:24px;">MeetSmart AI · ThinkPalm Internal</p>
    </div></body></html>
    """
