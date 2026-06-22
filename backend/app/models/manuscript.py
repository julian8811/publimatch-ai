import uuid
from sqlalchemy import Column, String, DateTime, ForeignKey, Text, ARRAY, func
from sqlalchemy.dialects.postgresql import UUID
from pgvector.sqlalchemy import Vector
from .base import Base

class Manuscript(Base):
    __tablename__ = 'manuscripts'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey('projects.id', ondelete="CASCADE"))
    title = Column(String, nullable=False)
    abstract = Column(Text)
    keywords = Column(ARRAY(String))
    language = Column(String(10))
    article_type = Column(String(50))
    manuscript_embedding = Column(Vector(768))
    file_path = Column(Text)
    extracted_text = Column(Text)
    status = Column(String(20), default="draft")
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
