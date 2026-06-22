from pydantic import BaseModel, ConfigDict
from typing import List, Optional
from uuid import UUID
from datetime import datetime


# --- Project ---

class ProjectBase(BaseModel):
    name: str
    description: Optional[str] = None


class ProjectCreate(ProjectBase):
    pass


class ProjectResponse(ProjectBase):
    id: UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# --- Manuscript ---

class ManuscriptBase(BaseModel):
    title: str
    abstract: Optional[str] = None


class ManuscriptResponse(ManuscriptBase):
    id: UUID
    project_id: UUID
    status: str
    extracted_text: Optional[str] = None
    keywords: Optional[List[str]] = None
    article_type: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# --- Auth ---

class UserCreate(BaseModel):
    email: str
    password: str
    full_name: Optional[str] = None
    institution: Optional[str] = None


class UserResponse(BaseModel):
    id: UUID
    email: str
    full_name: Optional[str] = None
    institution: Optional[str] = None
    role: str

    model_config = ConfigDict(from_attributes=True)


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


# --- Scoring ---

class MatchScore(BaseModel):
    final_score: float
    semantic_score: float = 0
    impact_score: float = 0
    oa_score: float = 0
    indexing_score: float = 0
    language_score: float = 0
    cost_score: float = 0
    review_speed_score: float = 0


class AIAnalysis(BaseModel):
    compatibility_reason: str
    predatory_risk: str
    submission_strategy: str


# --- Risk Assessment ---

class RiskAssessmentResponse(BaseModel):
    risk_score: int
    risk_level: str
    signals: List[str]


# --- Journal Match ---

class JournalMatchResponse(BaseModel):
    openalex_id: str
    name: str
    issn_print: Optional[str] = None
    publisher: str
    open_access: bool
    apc_usd: float
    homepage_url: str
    scores: MatchScore
    ai_analysis: Optional[AIAnalysis] = None
    risk_assessment: Optional[RiskAssessmentResponse] = None


# --- Tasks ---

class TaskStatusResponse(BaseModel):
    task_id: str
    status: str
    result: Optional[dict] = None
    error: Optional[str] = None
