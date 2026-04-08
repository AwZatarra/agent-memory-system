import uuid
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.config import settings
from app.repositories.memory_feedback_repository import MemoryFeedbackRepository
from app.repositories.memory_history_repository import MemoryHistoryRepository
from app.repositories.memory_repository import MemoryRepository
from app.schemas.memory import (
    MemoryCompactionRequest,
    MemoryCreate,
    MemoryExpireRequest,
    MemoryExpireDueRequest,
    MemoryFeedbackCreate,
    MemoryUpdate,
    MemoryContradictionCreate
)
from app.services.access_control_service import AccessControlService
from app.services.embedding_service import EmbeddingService
from app.services.compaction_service import CompactionService
from app.repositories.memory_relation_repository import MemoryRelationRepository
from app.core.tracing import get_tracer


class MemoryService:
    def __init__(self, db: Session):
        self.repo = MemoryRepository(db)
        self.history_repo = MemoryHistoryRepository(db)
        self.feedback_repo = MemoryFeedbackRepository(db)
        self.access_control = AccessControlService()
        self.embedding_service = EmbeddingService() if settings.enable_embeddings else None
        self.compaction_service = CompactionService()
        self.tracer = get_tracer("memory-service")
        self.relation_repo = MemoryRelationRepository(db)

    def _feedback_delta(self, verdict: str) -> float:
        if verdict == "useful":
            return 0.05
        if verdict == "partially_useful":
            return 0.02
        if verdict == "not_useful":
            return -0.05
        raise ValueError(f"Unsupported verdict: {verdict}")

    def _clamp_score(self, value: float) -> float:
        return max(0.0, min(1.0, value))

    def create_memory(self, payload: MemoryCreate):
        with self.tracer.start_as_current_span("memory.create") as span:
            span.set_attribute("memory.type", payload.memory_type)
            span.set_attribute("memory.scope", payload.scope)
            span.set_attribute("memory.source", payload.source)
            span.set_attribute("memory.agent_id", payload.agent_id or "")
            span.set_attribute("memory.tenant_id", payload.tenant_id or "")

            embedding = None

            if settings.enable_embeddings:
                if not self.embedding_service:
                    raise ValueError("Embeddings are enabled but embedding service is not available")

                text_for_embedding = self.embedding_service.build_memory_text(
                    title=payload.title,
                    content=payload.content,
                    summary=payload.summary,
                    tags=payload.tags,
                )
                embedding = self.embedding_service.generate_embedding(text_for_embedding)

            memory = self.repo.create(payload, embedding=embedding)

            self.history_repo.create(
                memory_id=memory.memory_id,
                event_type="created",
                actor_type=payload.source,
                actor_id=payload.agent_id or payload.user_id,
                old_value=None,
                new_value={
                    "title": memory.title,
                    "content": memory.content,
                    "summary": memory.summary,
                    "status": memory.status,
                    "version": memory.version,
                    "scope": memory.scope,
                    "tenant_id": memory.tenant_id,
                    "confidence_score": memory.confidence_score,
                },
            )

            span.set_attribute("memory.id", str(memory.memory_id))
            return memory
    
    def create_memory_for_agent(
        self,
        requesting_agent_id: str,
        requesting_tenant_id: str | None,
        payload: MemoryCreate,
    ):
        allowed, reason = self.access_control.can_write_memory(
            requesting_agent_id=requesting_agent_id,
            requesting_tenant_id=requesting_tenant_id,
            target_agent_id=payload.agent_id,
            target_tenant_id=payload.tenant_id,
            scope=payload.scope,
            source=payload.source,
        )

        if not allowed:
            raise PermissionError(reason)

        return self.create_memory(payload)

    def get_memory(self, memory_id: UUID):
        return self.repo.get_by_id(memory_id)

    def get_feedback_summary(self, memory_id: UUID) -> dict:
        return self.feedback_repo.get_feedback_summary(memory_id)

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
    ):
        return self.repo.list_memories(
            memory_type=memory_type,
            agent_id=agent_id,
            user_id=user_id,
            session_id=session_id,
            status=status,
            scope=scope,
            tag=tag,
            enforce_validity=enforce_validity,
        )

    def list_accessible_memories(
        self,
        requesting_agent_id: str,
        requesting_tenant_id: str | None,
        memory_type: str | None = None,
        user_id: str | None = None,
        session_id: str | None = None,
        tag: str | None = None,
    ):
        return self.repo.list_accessible_memories(
            requesting_agent_id=requesting_agent_id,
            requesting_tenant_id=requesting_tenant_id,
            memory_type=memory_type,
            user_id=user_id,
            session_id=session_id,
            tag=tag,
        )

    def search_memories(
        self,
        query_text: str,
        memory_type: str | None = None,
        agent_id: str | None = None,
        user_id: str | None = None,
        session_id: str | None = None,
        status: str | None = None,
        scope: str | None = None,
        tag: str | None = None,
        limit: int = 5,
    ):
        if not settings.enable_embeddings:
            raise ValueError("Semantic search requires embeddings to be enabled")

        if not self.embedding_service:
            raise ValueError("Embedding service is not available")

        query_embedding = self.embedding_service.generate_embedding(query_text)

        return self.repo.semantic_search(
            query_embedding=query_embedding,
            memory_type=memory_type,
            agent_id=agent_id,
            user_id=user_id,
            session_id=session_id,
            status=status,
            scope=scope,
            tag=tag,
            limit=limit,
        )

    def semantic_search_candidates(
        self,
        query_text: str,
        memory_type: str | None = None,
        agent_id: str | None = None,
        user_id: str | None = None,
        session_id: str | None = None,
        status: str | None = None,
        scope: str | None = None,
        tag: str | None = None,
        limit: int = 8,
    ):
        if not settings.enable_embeddings:
            raise ValueError("Semantic search requires embeddings to be enabled")

        if not self.embedding_service:
            raise ValueError("Embedding service is not available")

        query_embedding = self.embedding_service.generate_embedding(query_text)

        return self.repo.semantic_search(
            query_embedding=query_embedding,
            memory_type=memory_type,
            agent_id=agent_id,
            user_id=user_id,
            session_id=session_id,
            status=status,
            scope=scope,
            tag=tag,
            limit=limit,
        )

    def semantic_search_accessible_candidates(
        self,
        requesting_agent_id: str,
        requesting_tenant_id: str | None,
        query_text: str,
        memory_type: str | None = None,
        user_id: str | None = None,
        session_id: str | None = None,
        tag: str | None = None,
        limit: int = 8,
    ):
        with self.tracer.start_as_current_span("memory.semantic_search_accessible") as span:
            span.set_attribute("requesting.agent_id", requesting_agent_id)
            span.set_attribute("requesting.tenant_id", requesting_tenant_id or "")
            span.set_attribute("search.limit", limit)
            span.set_attribute("search.memory_type", memory_type or "")
            span.set_attribute("search.tag", tag or "")

            if not settings.enable_embeddings:
                raise ValueError("Semantic search requires embeddings to be enabled")

            if not self.embedding_service:
                raise ValueError("Embedding service is not available")

            query_embedding = self.embedding_service.generate_embedding(query_text)

            results = self.repo.semantic_search_accessible(
                query_embedding=query_embedding,
                requesting_agent_id=requesting_agent_id,
                requesting_tenant_id=requesting_tenant_id,
                memory_type=memory_type,
                user_id=user_id,
                session_id=session_id,
                tag=tag,
                limit=limit,
            )

            span.set_attribute("search.result_count", len(results))
            return results
        
    def update_memory(self, memory_id: UUID, payload: MemoryUpdate):
        memory = self.repo.get_by_id(memory_id)
        if not memory:
            return None

        old_value = {
            "title": memory.title,
            "content": memory.content,
            "summary": memory.summary,
            "confidence_score": memory.confidence_score,
            "importance_score": memory.importance_score,
            "tags": memory.tags,
            "valid_from": memory.valid_from.isoformat() if memory.valid_from else None,
            "valid_until": memory.valid_until.isoformat() if memory.valid_until else None,
        }

        new_title = payload.title if payload.title is not None else memory.title
        new_content = payload.content if payload.content is not None else memory.content
        new_summary = payload.summary if payload.summary is not None else memory.summary
        new_tags = payload.tags if payload.tags is not None else memory.tags

        embedding = None
        if settings.enable_embeddings and self.embedding_service:
            text_for_embedding = self.embedding_service.build_memory_text(
                title=new_title,
                content=new_content,
                summary=new_summary,
                tags=new_tags,
            )
            embedding = self.embedding_service.generate_embedding(text_for_embedding)

        updated = self.repo.update(memory, payload, embedding=embedding)

        self.history_repo.create(
            memory_id=updated.memory_id,
            event_type="updated",
            actor_type="system",
            actor_id=None,
            old_value=old_value,
            new_value={
                "title": updated.title,
                "content": updated.content,
                "summary": updated.summary,
                "confidence_score": updated.confidence_score,
                "importance_score": updated.importance_score,
                "tags": updated.tags,
                "valid_from": updated.valid_from.isoformat() if updated.valid_from else None,
                "valid_until": updated.valid_until.isoformat() if updated.valid_until else None,
            },
        )

        return updated

    def invalidate_memory(self, memory_id: UUID, actor_type: str, actor_id: str | None = None, reason: str | None = None):
        memory = self.repo.get_by_id(memory_id)
        if not memory:
            return None

        old_value = {
            "status": memory.status,
            "version": memory.version,
        }

        updated = self.repo.invalidate(memory)

        self.history_repo.create(
            memory_id=updated.memory_id,
            event_type="invalidated",
            actor_type=actor_type,
            actor_id=actor_id,
            old_value=old_value,
            new_value={
                "status": updated.status,
                "reason": reason,
            },
        )

        return updated

    def supersede_memory(self, memory_id: UUID, actor_type: str, actor_id: str | None, replacement: MemoryCreate):
        old_memory = self.repo.get_by_id(memory_id)
        if not old_memory:
            return None, None

        self.repo.supersede(old_memory)

        replacement_data = replacement.model_copy(
            update={
                "parent_memory_id": old_memory.memory_id
            }
        )

        embedding = None
        if settings.enable_embeddings and self.embedding_service:
            text_for_embedding = self.embedding_service.build_memory_text(
                title=replacement_data.title,
                content=replacement_data.content,
                summary=replacement_data.summary,
                tags=replacement_data.tags,
            )
            embedding = self.embedding_service.generate_embedding(text_for_embedding)

        new_memory = self.repo.create(replacement_data, embedding=embedding)

        self.history_repo.create(
            memory_id=old_memory.memory_id,
            event_type="superseded",
            actor_type=actor_type,
            actor_id=actor_id,
            old_value={
                "status": "active",
                "version": old_memory.version,
            },
            new_value={
                "status": "superseded",
                "replacement_memory_id": str(new_memory.memory_id),
            },
        )

        self.history_repo.create(
            memory_id=new_memory.memory_id,
            event_type="created_from_supersede",
            actor_type=actor_type,
            actor_id=actor_id,
            old_value={
                "parent_memory_id": str(old_memory.memory_id),
            },
            new_value={
                "status": new_memory.status,
                "version": new_memory.version,
            },
        )

        return old_memory, new_memory

    def add_feedback(self, memory_id: UUID, payload: MemoryFeedbackCreate):
        with self.tracer.start_as_current_span("memory.feedback.apply") as span:
            span.set_attribute("memory.id", str(memory_id))
            span.set_attribute("feedback.verdict", payload.verdict)
            span.set_attribute("feedback.actor_type", payload.actor_type)
            span.set_attribute("feedback.actor_id", payload.actor_id or "")

            memory = self.repo.get_by_id(memory_id)
            if not memory:
                span.set_attribute("memory.found", False)
                return None, None

            span.set_attribute("memory.found", True)

            old_confidence = float(memory.confidence_score)
            delta = self._feedback_delta(payload.verdict)
            new_confidence = self._clamp_score(old_confidence + delta)

            updated_memory = self.repo.update_confidence_score(memory, new_confidence)

            feedback = self.feedback_repo.create(
                memory_id=memory_id,
                verdict=payload.verdict,
                actor_type=payload.actor_type,
                actor_id=payload.actor_id,
                comment=payload.comment,
                score_delta=delta,
            )

            self.history_repo.create(
                memory_id=memory_id,
                event_type="feedback_applied",
                actor_type=payload.actor_type,
                actor_id=payload.actor_id,
                old_value={
                    "confidence_score": old_confidence,
                },
                new_value={
                    "confidence_score": updated_memory.confidence_score,
                    "verdict": payload.verdict,
                    "score_delta": delta,
                    "comment": payload.comment,
                },
            )

            span.set_attribute("feedback.delta", delta)
            span.set_attribute("feedback.old_confidence", old_confidence)
            span.set_attribute("feedback.new_confidence", float(updated_memory.confidence_score))

            return updated_memory, feedback

    def get_feedback_for_memory(self, memory_id: UUID):
        memory = self.repo.get_by_id(memory_id)
        if not memory:
            return None, None

        items = self.feedback_repo.list_by_memory_id(memory_id)
        return memory, items

    def get_memory_history(self, memory_id: UUID):
        return self.history_repo.list_by_memory_id(memory_id)
    
    def compact_memories(self, payload: MemoryCompactionRequest):
        with self.tracer.start_as_current_span("memory.compaction") as span:
            span.set_attribute("compaction.memory_type", payload.memory_type or "")
            span.set_attribute("compaction.scope", payload.scope or "")
            span.set_attribute("compaction.tag", payload.tag or "")
            span.set_attribute("compaction.tenant_id", payload.tenant_id or "")
            span.set_attribute("compaction.max_memories", payload.max_memories)
            span.set_attribute("compaction.min_required", payload.min_memories_required)
            span.set_attribute("compaction.use_llm_summary", payload.use_llm_summary)

            memories = self.repo.list_memories(
                memory_type=payload.memory_type,
                agent_id=payload.agent_id,
                status="active",
                scope=payload.scope,
                tag=payload.tag,
            )

            if payload.tenant_id is not None:
                memories = [m for m in memories if m.tenant_id == payload.tenant_id]

            memories = memories[: payload.max_memories]
            span.set_attribute("compaction.source_count", len(memories))

            if len(memories) < payload.min_memories_required:
                return {
                    "ok": False,
                    "job_id": str(uuid.uuid4()),
                    "compacted_memory_id": None,
                    "compacted_title": None,
                    "source_memories": [
                        {
                            "memory_id": m.memory_id,
                            "title": m.title,
                            "memory_type": m.memory_type,
                            "scope": m.scope,
                            "status": m.status,
                        }
                        for m in memories
                    ],
                    "total_source_memories": len(memories),
                    "message": f"Not enough memories to compact. Found {len(memories)}, required at least {payload.min_memories_required}.",
                }

            compacted_payload = self.compaction_service.build_compacted_memory_payload(
                payload=payload,
                memories=memories,
            )

            compacted_memory = self.create_memory(compacted_payload)

            for memory in memories:
                old_status = memory.status
                self.repo.supersede(memory)

                self.history_repo.create(
                    memory_id=memory.memory_id,
                    event_type="compacted",
                    actor_type=payload.source,
                    actor_id=payload.agent_id,
                    old_value={
                        "status": old_status,
                    },
                    new_value={
                        "status": "superseded",
                        "compacted_into_memory_id": str(compacted_memory.memory_id),
                    },
                )

            self.history_repo.create(
                memory_id=compacted_memory.memory_id,
                event_type="created_from_compaction",
                actor_type=payload.source,
                actor_id=payload.agent_id,
                old_value=None,
                new_value={
                    "source_memory_ids": [str(m.memory_id) for m in memories],
                    "source_count": len(memories),
                },
            )

            span.set_attribute("compaction.result_memory_id", str(compacted_memory.memory_id))

            return {
                "ok": True,
                "job_id": str(uuid.uuid4()),
                "compacted_memory_id": compacted_memory.memory_id,
                "compacted_title": compacted_memory.title,
                "source_memories": [
                    {
                        "memory_id": m.memory_id,
                        "title": m.title,
                        "memory_type": m.memory_type,
                        "scope": m.scope,
                        "status": "superseded",
                    }
                    for m in memories
                ],
                "total_source_memories": len(memories),
                "message": "Memory compaction completed successfully.",
            }
        
    def expire_memory(
        self,
        memory_id: UUID,
        actor_type: str,
        actor_id: str | None = None,
        reason: str | None = None,
    ):
        memory = self.repo.get_by_id(memory_id)
        if not memory:
            return None

        old_value = {
            "status": memory.status,
            "valid_until": memory.valid_until.isoformat() if memory.valid_until else None,
        }

        updated = self.repo.expire(memory)

        self.history_repo.create(
            memory_id=updated.memory_id,
            event_type="expired",
            actor_type=actor_type,
            actor_id=actor_id,
            old_value=old_value,
            new_value={
                "status": updated.status,
                "reason": reason,
            },
        )

        return updated

    def expire_due_memories(
        self,
        actor_type: str,
        actor_id: str | None = None,
        limit: int = 100,
    ):
        due_memories = self.repo.list_due_for_expiration(limit=limit)
        expired_ids = []

        for memory in due_memories:
            old_value = {
                "status": memory.status,
                "valid_until": memory.valid_until.isoformat() if memory.valid_until else None,
            }

            updated = self.repo.expire(memory)
            expired_ids.append(updated.memory_id)

            self.history_repo.create(
                memory_id=updated.memory_id,
                event_type="expired_due",
                actor_type=actor_type,
                actor_id=actor_id,
                old_value=old_value,
                new_value={
                    "status": updated.status,
                },
            )

        return {
            "ok": True,
            "expired_count": len(expired_ids),
            "expired_memory_ids": expired_ids,
            "message": f"Expired {len(expired_ids)} memories due for expiration.",
        }
    
    def add_contradiction(
        self,
        memory_id: UUID,
        payload: MemoryContradictionCreate,
    ):
        source_memory = self.repo.get_by_id(memory_id)
        target_memory = self.repo.get_by_id(payload.target_memory_id)

        if not source_memory or not target_memory:
            return None, None, None

        relation = self.relation_repo.create(
            from_memory_id=memory_id,
            to_memory_id=payload.target_memory_id,
            relation_type="contradicts",
            actor_type=payload.actor_type,
            actor_id=payload.actor_id,
            comment=payload.comment,
        )

        self.history_repo.create(
            memory_id=memory_id,
            event_type="contradiction_created",
            actor_type=payload.actor_type,
            actor_id=payload.actor_id,
            old_value=None,
            new_value={
                "target_memory_id": str(payload.target_memory_id),
                "relation_type": "contradicts",
                "comment": payload.comment,
            },
        )

        return source_memory, target_memory, relation

    def get_memory_relations(self, memory_id: UUID):
        memory = self.repo.get_by_id(memory_id)
        if not memory:
            return None, None

        items = self.relation_repo.list_by_memory_id(memory_id)
        return memory, items

    def get_contradiction_count(self, memory_id: UUID, active_memory_ids: set[str]) -> int:
        return self.relation_repo.count_active_contradictions_against_memory(
            memory_id=memory_id,
            active_memory_ids=active_memory_ids,
        )