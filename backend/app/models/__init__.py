from .base import Base
from .user import User
from .project import Project
from .manuscript import Manuscript
from .journal import Journal
from .match_result import MatchResult
from .risk_assessment import RiskAssessment

# Expose models for Alembic
__all__ = ["Base", "User", "Project", "Manuscript", "Journal", "MatchResult", "RiskAssessment"]
