import uuid
from sqlalchemy import Column, DateTime, Float, Integer, String, Text, text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from pgvector.sqlalchemy import Vector

from app.core.db import Base


class MemoryRecord(Base):
    __tablename__ = "memory_records"

    memory_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(String(100), nullable=True)
    agent_id = Column(String(100), nullable=True)
    user_id = Column(String(100), nullable=True)
    session_id = Column(String(100), nullable=True)

    memory_type = Column(String(50), nullable=False)
    scope = Column(String(50), nullable=False, default="private")

    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    summary = Column(Text, nullable=True)
    structured_payload = Column(JSONB, nullable=True)
    embedding = Column(Vector(1536), nullable=True)

    confidence_score = Column(Float, nullable=False, default=0.5)
    importance_score = Column(Float, nullable=False, default=0.5)

    source = Column(String(50), nullable=False, default="agent")
    source_event_id = Column(String(100), nullable=True)

    status = Column(String(50), nullable=False, default="active")
    version = Column(Integer, nullable=False, default=1)
    parent_memory_id = Column(UUID(as_uuid=True), nullable=True)

    valid_from = Column(DateTime, nullable=True)
    valid_until = Column(DateTime, nullable=True)

    tags = Column(ARRAY(String), nullable=False, default=list)

    created_at = Column(DateTime, nullable=False, server_default=text("NOW()"))
    updated_at = Column(DateTime, nullable=False, server_default=text("NOW()"))
    last_accessed_at = Column(DateTime, nullable=True)
    access_count = Column(Integer, nullable=False, default=0)