from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field


MemoryType = Literal["short_term", "semantic", "episodic", "procedural", "relational"]
MemoryScope = Literal["private", "shared", "global"]
MemoryStatus = Literal["active", "invalidated", "superseded", "expired"]
MemorySource = Literal["agent", "human", "system", "tool"]


class MemoryCreate(BaseModel):
    tenant_id: str | None = None
    agent_id: str | None = None
    user_id: str | None = None
    session_id: str | None = None

    memory_type: MemoryType
    scope: MemoryScope = "private"

    title: str = Field(..., min_length=3, max_length=255)
    content: str = Field(..., min_length=3)
    summary: str | None = None
    structured_payload: dict[str, Any] | None = None

    confidence_score: float = Field(default=0.5, ge=0.0, le=1.0)
    importance_score: float = Field(default=0.5, ge=0.0, le=1.0)

    source: MemorySource = "agent"
    source_event_id: str | None = None

    tags: list[str] = Field(default_factory=list)

    valid_from: datetime | None = None
    valid_until: datetime | None = None
    parent_memory_id: UUID | None = None


class MemoryResponse(BaseModel):
    memory_id: UUID
    tenant_id: str | None
    agent_id: str | None
    user_id: str | None
    session_id: str | None

    memory_type: MemoryType
    scope: MemoryScope

    title: str
    content: str
    summary: str | None
    structured_payload: dict[str, Any] | None

    confidence_score: float
    importance_score: float

    source: MemorySource
    source_event_id: str | None

    status: MemoryStatus
    version: int
    parent_memory_id: UUID | None

    valid_from: datetime | None
    valid_until: datetime | None

    tags: list[str]

    created_at: datetime
    updated_at: datetime
    last_accessed_at: datetime | None
    access_count: int

    model_config = {"from_attributes": True}


class MemoryListResponse(BaseModel):
    items: list[MemoryResponse]
    total: int

class MemorySearchRequest(BaseModel):
    query: str = Field(..., min_length=3)
    memory_type: MemoryType | None = None
    agent_id: str | None = None
    user_id: str | None = None
    session_id: str | None = None
    status: MemoryStatus | None = "active"
    scope: MemoryScope | None = None
    tag: str | None = None
    limit: int = Field(default=5, ge=1, le=50)


class MemorySearchResult(BaseModel):
    memory: MemoryResponse
    similarity_score: float


class MemorySearchResponse(BaseModel):
    items: list[MemorySearchResult]
    total: int

class RetrievalWeights(BaseModel):
    semantic: float = 0.50
    recency: float = 0.15
    confidence: float = 0.15
    importance: float = 0.10
    feedback: float = 0.10


class RetrieveContextRequest(BaseModel):
    query: str = Field(..., min_length=3)
    memory_type: MemoryType | None = None
    agent_id: str | None = None
    user_id: str | None = None
    session_id: str | None = None
    status: MemoryStatus | None = "active"
    scope: MemoryScope | None = None
    tag: str | None = None
    limit: int = Field(default=8, ge=1, le=50)
    top_k: int = Field(default=5, ge=1, le=20)
    weights: RetrievalWeights = RetrievalWeights()


class RetrievedMemoryItem(BaseModel):
    memory: MemoryResponse
    semantic_similarity: float
    recency_score: float
    confidence_score: float
    importance_score: float
    feedback_score: float
    contradiction_penalty: float
    final_score: float


class RetrievalContextResponse(BaseModel):
    query: str
    total_candidates: int
    total_selected: int
    items: list[RetrievedMemoryItem]
    summary: str
    facts: list[str]
    episodes: list[str]
    procedures: list[str]

class MemoryUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=3, max_length=255)
    content: str | None = Field(default=None, min_length=3)
    summary: str | None = None
    structured_payload: dict[str, Any] | None = None
    confidence_score: float | None = Field(default=None, ge=0.0, le=1.0)
    importance_score: float | None = Field(default=None, ge=0.0, le=1.0)
    tags: list[str] | None = None
    valid_from: datetime | None = None
    valid_until: datetime | None = None


class MemoryInvalidateRequest(BaseModel):
    actor_type: Literal["agent", "human", "system", "tool"] = "system"
    actor_id: str | None = None
    reason: str | None = None


class MemorySupersedeRequest(BaseModel):
    actor_type: Literal["agent", "human", "system", "tool"] = "system"
    actor_id: str | None = None
    replacement: MemoryCreate


class MemoryHistoryResponse(BaseModel):
    history_id: UUID
    memory_id: UUID
    event_type: str
    actor_type: str
    actor_id: str | None
    old_value: dict[str, Any] | None
    new_value: dict[str, Any] | None
    created_at: datetime

    model_config = {"from_attributes": True}


class MemoryHistoryListResponse(BaseModel):
    items: list[MemoryHistoryResponse]
    total: int

class ShortTermMessage(BaseModel):
    role: str
    content: str
    timestamp: datetime | None = None


class ShortTermToolCall(BaseModel):
    tool_name: str
    input: dict[str, Any] | None = None
    output: dict[str, Any] | None = None
    timestamp: datetime | None = None


class ShortTermMemoryWriteRequest(BaseModel):
    agent_id: str
    messages: list[ShortTermMessage] = Field(default_factory=list)
    tool_calls: list[ShortTermToolCall] = Field(default_factory=list)
    current_goal: str | None = None
    execution_state: dict[str, Any] | None = None


class ShortTermMemoryResponse(BaseModel):
    agent_id: str
    session_id: str
    messages: list[ShortTermMessage]
    tool_calls: list[ShortTermToolCall]
    current_goal: str | None
    execution_state: dict[str, Any] | None
    ttl_seconds: int
    last_updated_at: datetime


class ContextWindowRequest(BaseModel):
    agent_id: str
    include_messages: bool = True
    include_tool_calls: bool = True
    include_goal: bool = True
    include_execution_state: bool = True


class ContextWindowResponse(BaseModel):
    agent_id: str
    session_id: str
    context_window: str
    message_count: int
    tool_call_count: int
    current_goal: str | None
    execution_state: dict[str, Any] | None

class AgentMemoryCreateRequest(MemoryCreate):
    requesting_agent_id: str
    requesting_tenant_id: str | None = None


class AgentAccessibleMemoriesResponse(BaseModel):
    items: list[MemoryResponse]
    total: int


class AgentRetrieveContextRequest(BaseModel):
    requesting_tenant_id: str | None = None
    query: str = Field(..., min_length=3)
    memory_type: MemoryType | None = None
    user_id: str | None = None
    session_id: str | None = None
    tag: str | None = None
    limit: int = Field(default=8, ge=1, le=50)
    top_k: int = Field(default=5, ge=1, le=20)
    weights: RetrievalWeights = RetrievalWeights()

class MemoryFeedbackCreate(BaseModel):
    verdict: Literal["useful", "partially_useful", "not_useful"]
    actor_type: Literal["agent", "human", "system", "tool"] = "human"
    actor_id: str | None = None
    comment: str | None = None


class MemoryFeedbackResponse(BaseModel):
    feedback_id: UUID
    memory_id: UUID
    verdict: str
    actor_type: str
    actor_id: str | None
    comment: str | None
    score_delta: float
    created_at: datetime

    model_config = {"from_attributes": True}


class MemoryFeedbackListResponse(BaseModel):
    items: list[MemoryFeedbackResponse]
    total: int

class MemoryCompactionRequest(BaseModel):
    tenant_id: str | None = None
    agent_id: str | None = None
    memory_type: MemoryType | None = None
    scope: MemoryScope | None = None
    tag: str | None = None
    max_memories: int = Field(default=10, ge=2, le=50)
    min_memories_required: int = Field(default=2, ge=2, le=20)
    target_memory_type: MemoryType = "semantic"
    title: str | None = None
    summary: str | None = None
    source: MemorySource = "system"
    use_llm_summary: bool = True


class CompactedSourceMemory(BaseModel):
    memory_id: UUID
    title: str
    memory_type: str
    scope: str
    status: str


class MemoryCompactionResponse(BaseModel):
    ok: bool
    job_id: str
    compacted_memory_id: UUID | None = None
    compacted_title: str | None = None
    source_memories: list[CompactedSourceMemory]
    total_source_memories: int
    message: str

class MemoryExpireRequest(BaseModel):
    actor_type: Literal["agent", "human", "system", "tool"] = "system"
    actor_id: str | None = None
    reason: str | None = None


class MemoryExpireDueRequest(BaseModel):
    actor_type: Literal["agent", "human", "system", "tool"] = "system"
    actor_id: str | None = None
    limit: int = Field(default=100, ge=1, le=1000)


class MemoryExpireDueResponse(BaseModel):
    ok: bool
    expired_count: int
    expired_memory_ids: list[UUID]
    message: str

class SaveDecision(str):
    SAVE_LONG_TERM = "save_long_term"
    SAVE_SHORT_TERM_ONLY = "save_short_term_only"
    SKIP = "skip"


class MemorySaveDecisionRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    content: str = Field(..., min_length=1)
    memory_type: MemoryType | None = None
    scope: MemoryScope | None = None
    importance_score: float = Field(default=0.5, ge=0.0, le=1.0)
    confidence_score: float = Field(default=0.5, ge=0.0, le=1.0)
    tags: list[str] = Field(default_factory=list)
    agent_id: str | None = None
    tenant_id: str | None = None
    session_id: str | None = None
    structured_payload: dict[str, Any] | None = None


class MemorySaveDecisionResponse(BaseModel):
    decision: Literal["save_long_term", "save_short_term_only", "skip"]
    reasons: list[str]
    recommended_memory_type: MemoryType | None = None
    suggested_scope: MemoryScope | None = None

class MemoryContradictionCreate(BaseModel):
    target_memory_id: UUID
    actor_type: Literal["agent", "human", "system", "tool"] = "human"
    actor_id: str | None = None
    comment: str | None = None


class MemoryRelationResponse(BaseModel):
    relation_id: UUID
    from_memory_id: UUID
    to_memory_id: UUID
    relation_type: str
    actor_type: str
    actor_id: str | None
    comment: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class MemoryRelationListResponse(BaseModel):
    items: list[MemoryRelationResponse]
    total: int