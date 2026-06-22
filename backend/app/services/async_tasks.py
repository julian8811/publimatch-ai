"""Celery tasks for asynchronous manuscript processing.

All tasks are designed to work independently of the request-response cycle:
they create their own DB sessions and handle errors gracefully.
"""

import logging
from typing import Optional

from app.core.celery_app import celery_app
from app.db.database import SessionLocal
from app.models.manuscript import Manuscript
from app.models.match_result import MatchResult
from app.services.scoring_service import ScoringService
from app.services.embedding_service import EmbeddingService

logger = logging.getLogger(__name__)


def _get_manuscript(manuscript_id: str) -> Optional[Manuscript]:
    """Fetch a manuscript by ID from the database.

    Returns None if not found (so the task can report failure without
    crashing).
    """
    from uuid import UUID

    try:
        uid = UUID(manuscript_id)
    except (ValueError, TypeError):
        logger.error("Invalid manuscript_id: %s", manuscript_id)
        return None

    db = SessionLocal()
    try:
        return db.query(Manuscript).filter(Manuscript.id == uid).first()
    finally:
        db.close()


def _get_journals():
    """Fetch all ready-made journals from the database.

    Returns an empty list if the journals table is empty or unavailable.
    """
    from app.models.journal import Journal

    db = SessionLocal()
    try:
        journals = db.query(Journal).all()
        return [
            {
                "id": str(j.id),
                "name": j.name,
                "issn_print": j.issn_print,
                "publisher": j.publisher or "",
                "open_access": j.open_access or False,
                "apc_usd": float(j.apc_amount or 0),
                "homepage_url": j.website_url or "",
                "cited_by_count": 0,
                "scope_embedding": getattr(j, "scope_embedding", None),
                "indexed_scopus": j.indexed_scopus or False,
                "indexed_wos": j.indexed_wos or False,
                "indexed_doaj": j.indexed_doaj or False,
                "indexed_latindex": j.indexed_latindex or False,
            }
            for j in journals
        ]
    finally:
        db.close()


def _save_match_result(
    manuscript_id: str, journal_id: str, scores: dict
) -> Optional[str]:
    """Persist a single MatchResult row to the database.

    Returns the MatchResult ID as a string, or None on failure.
    """
    from uuid import UUID

    db = SessionLocal()
    try:
        result = MatchResult(
            manuscript_id=UUID(manuscript_id),
            journal_id=UUID(journal_id),
            scope_score=scores.get("semantic_score", 0),
            recent_articles_score=0,
            methodology_score=scores.get("impact_score", 0),
            indexing_score=scores.get("indexation_score", 0),
            language_score=scores.get("language_score", 0),
            cost_score=scores.get("apc_score", 0),
            final_score=scores.get("final_score", 0),
        )
        db.add(result)
        db.commit()
        db.refresh(result)
        return str(result.id)
    except Exception as e:
        logger.error("Failed to save MatchResult: %s", e, exc_info=True)
        db.rollback()
        return None
    finally:
        db.close()


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def process_manuscript_matches(self, manuscript_id: str):
    """Full async processing: fetch manuscript, score DB journals, save results.

    This task:
    1. Loads the Manuscript from the database.
    2. Loads all journals from the database (journals are pre-fetched).
    3. For each journal, computes a match score via ScoringService.
    4. Persists each result as a MatchResult row.
    5. Returns a summary dict with counts and the manuscript status.

    Args:
        manuscript_id: UUID string of the Manuscript to process.

    Returns:
        dict with keys: processed, total, manuscript_status, match_ids.
    """
    manuscript = _get_manuscript(manuscript_id)
    if manuscript is None:
        logger.error("Manuscript %s not found — cannot process matches.", manuscript_id)
        return {
            "error": f"Manuscript {manuscript_id} not found",
            "processed": 0,
            "total": 0,
        }

    journals = _get_journals()
    if not journals:
        logger.info("No journals found in DB for manuscript %s.", manuscript_id)
        return {
            "processed": 0,
            "total": 0,
            "manuscript_status": manuscript.status,
            "match_ids": [],
        }

    scoring_service = ScoringService()
    embedding_service = EmbeddingService()

    match_ids = []
    errors = 0

    for journal_data in journals:
        try:
            scores = scoring_service.calculate_journal_match_score(
                manuscript_keywords=manuscript.keywords or [],
                journal_data=journal_data,
                manuscript=manuscript,
            )
            match_id = _save_match_result(
                manuscript_id=manuscript_id,
                journal_id=journal_data["id"],
                scores=scores,
            )
            if match_id:
                match_ids.append(match_id)
            else:
                errors += 1
        except Exception as e:
            logger.error(
                "Error scoring journal %s for manuscript %s: %s",
                journal_data.get("name"),
                manuscript_id,
                e,
                exc_info=True,
            )
            errors += 1

    logger.info(
        "Processed manuscript %s: %d/%d matches saved (%d errors).",
        manuscript_id,
        len(match_ids),
        len(journals),
        errors,
    )

    return {
        "processed": len(match_ids),
        "total": len(journals),
        "errors": errors,
        "manuscript_status": manuscript.status,
        "match_ids": match_ids,
    }
