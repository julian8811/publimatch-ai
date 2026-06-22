import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import uuid

from app.db.database import get_db
from app.models.manuscript import Manuscript
from app.models.project import Project
from app.models.user import User
from app.schemas import JournalMatchResponse, MatchScore, RiskAssessmentResponse
from app.services.openalex_service import OpenAlexService
from app.services.scoring_service import ScoringService
from app.services.llm_service import LLMService
from app.services.doaj_service import DOAJService
from app.services.risk_service import RiskAssessmentService
from app.core.security import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter()
openalex_service = OpenAlexService()
scoring_service = ScoringService()
llm_service = LLMService()
doaj_service = DOAJService()
risk_service = RiskAssessmentService()


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
        scores = scoring_service.calculate_journal_match_score(
            manuscript.keywords, j, manuscript=manuscript
        )
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

    # Run risk assessment for each result
    for res in results[:10]:  # Assess top 10
        try:
            # DOAJ verification
            doaj_result = {"in_doaj": False}
            if res.issn_print:
                doaj_result = await doaj_service.verify_journal(res.issn_print)

            # Build risk assessment input from available data
            risk_input = {
                "in_doaj": doaj_result.get("in_doaj", False),
                "indexed_scopus": False,  # Not available from OpenAlex dict
                "indexed_wos": False,
                "issn": res.issn_print,
                "publisher": res.publisher,
            }
            risk_result = risk_service.assess_journal(risk_input)
            res.risk_assessment = RiskAssessmentResponse(
                risk_score=risk_result["risk_score"],
                risk_level=risk_result["risk_level"],
                signals=risk_result["signals"],
            )
        except Exception as e:
            logger.error(
                "Risk assessment failed for journal %s: %s",
                res.openalex_id,
                e,
                exc_info=True,
            )
            # Graceful degradation — risk assessment is optional
            res.risk_assessment = None

    # AI analysis for top 3
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
