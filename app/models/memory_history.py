import uuid
from sqlalchemy import Column, DateTime, String, text
from sqlalchemy.dialects.postgresql import JSONB, UUID

from app.core.db import Base


class MemoryHistory(Base):
    __tablename__ = "memory_history"

    history_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    memory_id = Column(UUID(as_uuid=True), nullable=False)
    event_type = Column(String(50), nullable=False)
    actor_type = Column(String(50), nullable=False)
    actor_id = Column(String(100), nullable=True)
    old_value = Column(JSONB, nullable=True)
    new_value = Column(JSONB, nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=text("NOW()"))