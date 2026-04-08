import uuid
from collections import OrderedDict

from app.core.config import settings
from app.schemas.memory import MemoryCompactionRequest, MemoryCreate
from app.services.llm_summarization_service import LlmSummarizationService


class CompactionService:
    def __init__(self):
        self.llm_service = (
            LlmSummarizationService()
            if settings.enable_llm_compaction
            else None
        )

    def build_compacted_title(self, payload: MemoryCompactionRequest, memories: list) -> str:
        if payload.title:
            return payload.title

        if payload.tag and payload.tenant_id:
            return f"Compacted memory for {payload.tag} in {payload.tenant_id}"

        if payload.tag:
            return f"Compacted memory for {payload.tag}"

        if payload.memory_type:
            return f"Compacted {payload.memory_type} memory"

        return "Compacted memory"

    def build_compacted_summary(self, payload: MemoryCompactionRequest, memories: list) -> str:
        if payload.summary:
            return payload.summary

        summaries = []
        for memory in memories:
            text = memory.summary or memory.content
            if text:
                summaries.append(text.strip())

        unique_summaries = list(OrderedDict.fromkeys(summaries))
        compacted = " | ".join(unique_summaries[:5])

        return compacted[:1000] if compacted else "Compacted memory summary"

    def build_compacted_content(self, memories: list) -> str:
        chunks = []

        for idx, memory in enumerate(memories, start=1):
            text = memory.summary or memory.content
            chunks.append(f"{idx}. {memory.title}: {text}")

        content = "\n".join(chunks)
        return content[:5000]

    def build_compacted_tags(self, memories: list) -> list[str]:
        tags = []
        for memory in memories:
            tags.extend(memory.tags or [])

        unique_tags = list(OrderedDict.fromkeys(tags))
        return unique_tags[:20]

    def build_llm_compacted_fields(
        self,
        payload: MemoryCompactionRequest,
        memories: list,
    ) -> dict | None:
        if not payload.use_llm_summary:
            return None

        if not settings.enable_llm_compaction or not self.llm_service:
            return None

        return self.llm_service.summarize_memories(memories)

    def build_compacted_memory_payload(
        self,
        payload: MemoryCompactionRequest,
        memories: list,
    ) -> MemoryCreate:
        first_memory = memories[0]
        llm_fields = self.build_llm_compacted_fields(payload, memories)

        title = (
            payload.title
            or (llm_fields["title"] if llm_fields else self.build_compacted_title(payload, memories))
        )

        summary = (
            payload.summary
            or (llm_fields["summary"] if llm_fields else self.build_compacted_summary(payload, memories))
        )

        content = (
            llm_fields["content"] if llm_fields else self.build_compacted_content(memories)
        )

        return MemoryCreate(
            tenant_id=payload.tenant_id if payload.tenant_id is not None else first_memory.tenant_id,
            agent_id=payload.agent_id if payload.agent_id is not None else first_memory.agent_id,
            user_id=None,
            session_id=None,
            memory_type=payload.target_memory_type,
            scope=payload.scope if payload.scope is not None else first_memory.scope,
            title=title,
            content=content,
            summary=summary,
            structured_payload={
                "compacted_from_memory_ids": [str(memory.memory_id) for memory in memories],
                "source_count": len(memories),
                "used_llm_summary": bool(llm_fields),
            },
            confidence_score=0.8,
            importance_score=0.8,
            source=payload.source,
            source_event_id=f"compaction-{uuid.uuid4()}",
            parent_memory_id=None,
            tags=self.build_compacted_tags(memories),
            valid_from=None,
            valid_until=None,
        )