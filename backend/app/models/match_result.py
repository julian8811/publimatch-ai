import uuid
from sqlalchemy import Column, String, DateTime, ForeignKey, Text, Numeric, func
from sqlalchemy.dialects.postgresql import UUID
from .base import Base


class MatchResult(Base):
    __tablename__ = 'match_results'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    manuscript_id = Column(UUID(as_uuid=True), ForeignKey('manuscripts.id', ondelete='CASCADE'))
    journal_id = Column(UUID(as_uuid=True), ForeignKey('journals.id', ondelete='CASCADE'))
    scope_score = Column(Numeric(5, 2))
    recent_articles_score = Column(Numeric(5, 2), default=0)
    methodology_score = Column(Numeric(5, 2))
    indexing_score = Column(Numeric(5, 2))
    language_score = Column(Numeric(5, 2))
    cost_score = Column(Numeric(5, 2))
    risk_adjustment = Column(Numeric(5, 2), default=0)
    final_score = Column(Numeric(5, 2), nullable=False)
    explanation = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
