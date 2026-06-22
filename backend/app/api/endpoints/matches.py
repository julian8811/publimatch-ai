import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import uuid

from app.db.database import get_db
from app.models.manuscript import Manuscript
from app.models.project import Project
from app.models.user import User
from app.schemas import JournalMatchResponse, MatchScore
from app.services.openalex_service import OpenAlexService
from app.services.scoring_service import ScoringService
from app.services.llm_service import LLMService
from app.core.security import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter()
openalex_service = OpenAlexService()
scoring_service = ScoringService()
llm_service = LLMService()


@router.get("/{manuscript_id}", response_model=list[JournalMatchResponse])
async def get_matches(
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
            detail="You do not have permission to view matches for this manuscript",
        )

    if not manuscript.keywords:
        raise HTTPException(
            status_code=400,
            detail="Manuscript has no extracted keywords yet. Make sure it was processed by the LLM.",
        )

    journals = await openalex_service.fetch_journals_by_concept(manuscript.keywords)

    results = []
    for j in journals:
        scores = scoring_service.calculate_journal_match_score(manuscript.keywords, j)
        results.append(
            JournalMatchResponse(
                openalex_id=j["openalex_id"],
                name=j["name"],
                issn_print=j.get("issn_print"),
                publisher=j["publisher"],
                open_access=j["open_access"],
                apc_usd=j["apc_usd"],
                homepage_url=j["homepage_url"],
                scores=MatchScore(**scores),
            )
        )

    results.sort(key=lambda x: x.scores.final_score, reverse=True)

    for res in results[:3]:
        journal_data = {
            "name": res.name,
            "publisher": res.publisher,
            "open_access": res.open_access,
            "apc_usd": res.apc_usd,
        }
        try:
            analysis = await llm_service.analyze_journal_compatibility(
                manuscript.abstract, journal_data
            )
            res.ai_analysis = analysis
        except Exception as e:
            logger.error(f"AI analysis failed for journal {res.openalex_id}: {e}", exc_info=True)

    return results
