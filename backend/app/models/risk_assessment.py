import uuid
from sqlalchemy import Column, String, DateTime, ForeignKey, Text, Integer, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from .base import Base


class RiskAssessment(Base):
    __tablename__ = 'risk_assessments'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    journal_id = Column(UUID(as_uuid=True), ForeignKey('journals.id', ondelete='CASCADE'))
    manuscript_id = Column(UUID(as_uuid=True), ForeignKey('manuscripts.id', ondelete='CASCADE'))
    risk_level = Column(String(20), default='low')
    risk_score = Column(Integer, default=0)
    signals = Column(JSONB)
    evidence = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
