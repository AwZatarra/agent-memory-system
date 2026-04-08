import uuid
from sqlalchemy import Column, DateTime, Float, String, Text, text
from sqlalchemy.dialects.postgresql import UUID

from app.core.db import Base


class MemoryFeedback(Base):
    __tablename__ = "memory_feedback"

    feedback_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    memory_id = Column(UUID(as_uuid=True), nullable=False)
    verdict = Column(String(50), nullable=False)
    actor_type = Column(String(50), nullable=False)
    actor_id = Column(String(100), nullable=True)
    comment = Column(Text, nullable=True)
    score_delta = Column(Float, nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=text("NOW()"))