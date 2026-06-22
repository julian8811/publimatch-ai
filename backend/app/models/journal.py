import uuid
from sqlalchemy import Column, String, DateTime, Boolean, Text, ARRAY, Numeric, Integer, func
from sqlalchemy.dialects.postgresql import UUID
from pgvector.sqlalchemy import Vector
from .base import Base

class Journal(Base):
    __tablename__ = 'journals'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    issn_print = Column(String(9))
    issn_online = Column(String(9))
    publisher = Column(String)
    country = Column(String(100))
    languages = Column(ARRAY(String(10)))
    scope = Column(Text)
    scope_embedding = Column(Vector(1536))
    website_url = Column(Text)
    author_guidelines_url = Column(Text)
    open_access = Column(Boolean, default=False)
    indexed_scopus = Column(Boolean, default=False)
    indexed_wos = Column(Boolean, default=False)
    indexed_doaj = Column(Boolean, default=False)
    indexed_latindex = Column(Boolean, default=False)
    apc_amount = Column(Numeric, default=0.0)
    apc_currency = Column(String(10), default="USD")
    average_review_weeks = Column(Integer)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
