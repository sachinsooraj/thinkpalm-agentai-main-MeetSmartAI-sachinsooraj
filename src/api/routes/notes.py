"""
MeetSmart AI — Notes & MoM API routes.
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, UploadFile, File, Form
from sqlalchemy.orm import Session

from src.db.database import get_db
from src.agents.notes_agent import notes_agent
from src.agents.mom_agent import mom_agent
from src.agents.reminder_agent import reminder_agent
from src.api.models import NotesRequest, NotesResult, SuccessResponse

router = APIRouter(prefix="/api/notes", tags=["Notes & MoM"])


@router.post("/process", response_model=NotesResult)
def process_notes(req: NotesRequest, db: Session = Depends(get_db)):
    """
    Process meeting transcript/notes using AI.
    Returns structured summary, decisions, and action items.
    """
    if not req.transcript.strip():
        raise HTTPException(status_code=400, detail="Transcript cannot be empty.")

    result = notes_agent.process(db, req.meeting_id, req.transcript, save_json=True)
    if not result:
        raise HTTPException(status_code=404, detail="Meeting not found.")

    return NotesResult(
        meeting_id=result["meeting_id"],
        meeting_title=result.get("meeting_title", ""),
        summary=result.get("summary", ""),
        decisions=result.get("decisions", []),
        action_items=result.get("action_items", []),
        key_topics=result.get("key_topics", []),
        mode=result.get("mode", "rule-based"),
    )


@router.post("/upload/{meeting_id}", response_model=NotesResult)
async def upload_transcript(
    meeting_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """Upload a .txt transcript file and process it."""
    if not file.filename.endswith((".txt", ".md")):
        raise HTTPException(status_code=400, detail="Only .txt and .md files supported.")

    content = await file.read()
    transcript = content.decode("utf-8", errors="replace")

    result = notes_agent.process(db, meeting_id, transcript, save_json=True)
    if not result:
        raise HTTPException(status_code=404, detail="Meeting not found.")

    return NotesResult(
        meeting_id=result["meeting_id"],
        meeting_title=result.get("meeting_title", ""),
        summary=result.get("summary", ""),
        decisions=result.get("decisions", []),
        action_items=result.get("action_items", []),
        key_topics=result.get("key_topics", []),
        mode=result.get("mode", "rule-based"),
    )


@router.post("/generate-mom/{meeting_id}", response_model=SuccessResponse)
def generate_mom(
    meeting_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """
    Generate and email the Minutes of Meeting Word document for a meeting.
    Runs in background — returns immediately.
    """
    background_tasks.add_task(_generate_mom_task, meeting_id)
    return SuccessResponse(
        success=True,
        message=f"MoM generation started for meeting {meeting_id}. Document will be emailed to participants.",
    )


@router.post("/send-reminder/{meeting_id}", response_model=SuccessResponse)
def send_test_reminder(meeting_id: int, db: Session = Depends(get_db)):
    """Send a test/manual reminder for a meeting (for demo purposes)."""
    try:
        reminder_agent.send_test_reminder(meeting_id)
        return SuccessResponse(success=True, message="Test reminder sent.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def _generate_mom_task(meeting_id: int):
    """Background task: generate MoM doc and send email."""
    from src.db.database import SessionLocal
    db = SessionLocal()
    try:
        mom_agent.generate_and_send(db, meeting_id)
    finally:
        db.close()
