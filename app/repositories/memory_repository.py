from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from app.models.memory import MemoryRecord
from app.schemas.memory import MemoryCreate, MemoryUpdate


class MemoryRepository:
    def __init__(self, db: Session):
        self.db = db

    def _utc_now(self) -> datetime:
        return datetime.now(timezone.utc)

    def _apply_validity_filter(self, query):
        now = self._utc_now()

        return query.filter(
            or_(
                MemoryRecord.valid_from.is_(None),
                MemoryRecord.valid_from <= now,
            ),
            or_(
                MemoryRecord.valid_until.is_(None),
                MemoryRecord.valid_until >= now,
            ),
        )

    def create(self, payload: MemoryCreate, embedding: list[float] | None = None) -> MemoryRecord:
        memory = MemoryRecord(
            tenant_id=payload.tenant_id,
            agent_id=payload.agent_id,
            user_id=payload.user_id,
            session_id=payload.session_id,
            memory_type=payload.memory_type,
            scope=payload.scope,
            title=payload.title,
            content=payload.content,
            summary=payload.summary,
            structured_payload=payload.structured_payload,
            embedding=embedding,
            confidence_score=payload.confidence_score,
            importance_score=payload.importance_score,
            source=payload.source,
            source_event_id=payload.source_event_id,
            status="active",
            version=1,
            parent_memory_id=payload.parent_memory_id,
            tags=payload.tags,
            valid_from=payload.valid_from,
            valid_until=payload.valid_until,
        )
        self.db.add(memory)
        self.db.commit()
        self.db.refresh(memory)
        return memory

    def get_by_id(self, memory_id: UUID) -> Optional[MemoryRecord]:
        return (
            self.db.query(MemoryRecord)
            .filter(MemoryRecord.memory_id == memory_id)
            .first()
        )

    def list_memories(
        self,
        memory_type: str | None = None,
        agent_id: str | None = None,
        user_id: str | None = None,
        session_id: str | None = None,
        status: str | None = None,
        scope: str | None = None,
        tag: str | None = None,
        enforce_validity: bool = False,
    ) -> list[MemoryRecord]:
        query = self.db.query(MemoryRecord)

        if memory_type:
            query = query.filter(MemoryRecord.memory_type == memory_type)
        if agent_id:
            query = query.filter(MemoryRecord.agent_id == agent_id)
        if user_id:
            query = query.filter(MemoryRecord.user_id == user_id)
        if session_id:
            query = query.filter(MemoryRecord.session_id == session_id)
        if status:
            query = query.filter(MemoryRecord.status == status)
        if scope:
            query = query.filter(MemoryRecord.scope == scope)
        if tag:
            query = query.filter(MemoryRecord.tags.any(tag))

        if enforce_validity:
            query = self._apply_validity_filter(query)

        return query.order_by(MemoryRecord.created_at.desc()).all()

    def list_accessible_memories(
        self,
        requesting_agent_id: str,
        requesting_tenant_id: str | None,
        memory_type: str | None = None,
        user_id: str | None = None,
        session_id: str | None = None,
        tag: str | None = None,
    ) -> list[MemoryRecord]:
        query = self.db.query(MemoryRecord).filter(MemoryRecord.status == "active")
        query = self._apply_validity_filter(query)

        access_filter = or_(
            and_(
                MemoryRecord.scope == "private",
                MemoryRecord.agent_id == requesting_agent_id,
            ),
            and_(
                MemoryRecord.scope == "shared",
                requesting_tenant_id is not None,
                MemoryRecord.tenant_id == requesting_tenant_id,
            ),
            and_(
                MemoryRecord.scope == "global",
                or_(
                    MemoryRecord.tenant_id.is_(None),
                    MemoryRecord.tenant_id == requesting_tenant_id,
                ),
            ),
        )

        query = query.filter(access_filter)

        if memory_type:
            query = query.filter(MemoryRecord.memory_type == memory_type)
        if user_id:
            query = query.filter(MemoryRecord.user_id == user_id)
        if session_id:
            query = query.filter(MemoryRecord.session_id == session_id)
        if tag:
            query = query.filter(MemoryRecord.tags.any(tag))

        return query.order_by(MemoryRecord.created_at.desc()).all()

    def semantic_search(
        self,
        query_embedding: list[float],
        memory_type: str | None = None,
        agent_id: str | None = None,
        user_id: str | None = None,
        session_id: str | None = None,
        status: str | None = None,
        scope: str | None = None,
        tag: str | None = None,
        limit: int = 5,
    ):
        similarity_expr = (1 - MemoryRecord.embedding.cosine_distance(query_embedding)).label("similarity_score")

        query = self.db.query(MemoryRecord, similarity_expr).filter(
            MemoryRecord.embedding.isnot(None)
        )

        if memory_type:
            query = query.filter(MemoryRecord.memory_type == memory_type)
        if agent_id:
            query = query.filter(MemoryRecord.agent_id == agent_id)
        if user_id:
            query = query.filter(MemoryRecord.user_id == user_id)
        if session_id:
            query = query.filter(MemoryRecord.session_id == session_id)
        if status:
            query = query.filter(MemoryRecord.status == status)
        if scope:
            query = query.filter(MemoryRecord.scope == scope)
        if tag:
            query = query.filter(MemoryRecord.tags.any(tag))

        if status == "active":
            query = self._apply_validity_filter(query)

        return query.order_by(MemoryRecord.embedding.cosine_distance(query_embedding)).limit(limit).all()

    def semantic_search_accessible(
        self,
        query_embedding: list[float],
        requesting_agent_id: str,
        requesting_tenant_id: str | None,
        memory_type: str | None = None,
        user_id: str | None = None,
        session_id: str | None = None,
        tag: str | None = None,
        limit: int = 8,
    ):
        similarity_expr = (1 - MemoryRecord.embedding.cosine_distance(query_embedding)).label("similarity_score")

        query = self.db.query(MemoryRecord, similarity_expr).filter(
            MemoryRecord.embedding.isnot(None),
            MemoryRecord.status == "active",
        )
        query = self._apply_validity_filter(query)

        access_filter = or_(
            and_(
                MemoryRecord.scope == "private",
                MemoryRecord.agent_id == requesting_agent_id,
            ),
            and_(
                MemoryRecord.scope == "shared",
                requesting_tenant_id is not None,
                MemoryRecord.tenant_id == requesting_tenant_id,
            ),
            and_(
                MemoryRecord.scope == "global",
                or_(
                    MemoryRecord.tenant_id.is_(None),
                    MemoryRecord.tenant_id == requesting_tenant_id,
                ),
            ),
        )

        query = query.filter(access_filter)

        if memory_type:
            query = query.filter(MemoryRecord.memory_type == memory_type)
        if user_id:
            query = query.filter(MemoryRecord.user_id == user_id)
        if session_id:
            query = query.filter(MemoryRecord.session_id == session_id)
        if tag:
            query = query.filter(MemoryRecord.tags.any(tag))

        return query.order_by(MemoryRecord.embedding.cosine_distance(query_embedding)).limit(limit).all()

    def update(self, memory: MemoryRecord, payload: MemoryUpdate, embedding: list[float] | None = None) -> MemoryRecord:
        data = payload.model_dump(exclude_unset=True)

        for field, value in data.items():
            setattr(memory, field, value)

        if embedding is not None:
            memory.embedding = embedding

        self.db.commit()
        self.db.refresh(memory)
        return memory

    def update_confidence_score(self, memory: MemoryRecord, new_confidence_score: float) -> MemoryRecord:
        memory.confidence_score = new_confidence_score
        self.db.commit()
        self.db.refresh(memory)
        return memory

    def invalidate(self, memory: MemoryRecord) -> MemoryRecord:
        memory.status = "invalidated"
        self.db.commit()
        self.db.refresh(memory)
        return memory

    def supersede(self, memory: MemoryRecord) -> MemoryRecord:
        memory.status = "superseded"
        self.db.commit()
        self.db.refresh(memory)
        return memory

    def expire(self, memory: MemoryRecord) -> MemoryRecord:
        memory.status = "expired"
        self.db.commit()
        self.db.refresh(memory)
        return memory

    def list_due_for_expiration(self, limit: int = 100) -> list[MemoryRecord]:
        now = self._utc_now()

        return (
            self.db.query(MemoryRecord)
            .filter(
                MemoryRecord.status == "active",
                MemoryRecord.valid_until.isnot(None),
                MemoryRecord.valid_until < now,
            )
            .order_by(MemoryRecord.valid_until.asc())
            .limit(limit)
            .all()
        )