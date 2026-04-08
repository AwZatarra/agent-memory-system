import uuid
from sqlalchemy import Column, DateTime, String, Text, text
from sqlalchemy.dialects.postgresql import UUID

from app.core.db import Base


class MemoryRelation(Base):
    __tablename__ = "memory_relations"

    relation_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    from_memory_id = Column(UUID(as_uuid=True), nullable=False)
    to_memory_id = Column(UUID(as_uuid=True), nullable=False)
    relation_type = Column(String(50), nullable=False)
    actor_type = Column(String(50), nullable=False)
    actor_id = Column(String(100), nullable=True)
    comment = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=text("NOW()"))