import logging

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
import uuid
import fitz  # PyMuPDF

from app.db.database import get_db
from app.models.manuscript import Manuscript
from app.models.project import Project
from app.models.user import User
from app.schemas import ManuscriptResponse
from app.services.llm_service import LLMService
from app.core.security import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter()
llm_service = LLMService()


@router.post("/upload", response_model=ManuscriptResponse)
async def upload_manuscript(
    project_id: uuid.UUID = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Verify the user owns this project
    if project.user_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="You do not have permission to upload to this project",
        )

    extracted_text = ""
    if file.filename and file.filename.endswith(".pdf"):
        content = await file.read()
        doc = fitz.open(stream=content, filetype="pdf")
        for page in doc:
            extracted_text += page.get_text()
    else:
        extracted_text = (await file.read()).decode("utf-8", errors="ignore")

    # Remove null characters to avoid Postgres ValueError
    extracted_text = extracted_text.replace("\x00", "")

    manuscript = Manuscript(
        project_id=project_id,
        title=file.filename or "untitled",
        file_path=file.filename,
        extracted_text=extracted_text,
        status="processing",
    )
    db.add(manuscript)
    db.commit()
    db.refresh(manuscript)

    try:
        profile = await llm_service.extract_manuscript_profile(extracted_text)
        manuscript.title = profile.get("title", manuscript.title)
        manuscript.abstract = profile.get("abstract", "")
        manuscript.keywords = profile.get("keywords", [])
        manuscript.article_type = profile.get("article_type", "")
        manuscript.status = "processed"
    except Exception as e:
        manuscript.status = "error"
        logger.error(f"LLM extraction failed for manuscript {manuscript.id}: {e}", exc_info=True)

    db.commit()
    db.refresh(manuscript)

    return manuscript


@router.get("/{manuscript_id}", response_model=ManuscriptResponse)
def get_manuscript(
    manuscript_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    manuscript = db.query(Manuscript).filter(Manuscript.id == manuscript_id).first()
    if not manuscript:
        raise HTTPException(status_code=404, detail="Manuscript not found")

    # Verify the user owns this manuscript's project
    project = db.query(Project).filter(Project.id == manuscript.project_id).first()
    if project and project.user_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="You do not have permission to view this manuscript",
        )

    return manuscript
