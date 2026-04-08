from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.schemas.memory import (
    MemoryCreate,
    MemoryHistoryListResponse,
    MemoryInvalidateRequest,
    MemoryListResponse,
    MemoryResponse,
    MemorySearchRequest,
    MemorySearchResponse,
    MemorySupersedeRequest,
    MemoryUpdate,
    RetrieveContextRequest,
    RetrievalContextResponse,
    AgentAccessibleMemoriesResponse,
    AgentMemoryCreateRequest,
    AgentRetrieveContextRequest,
    MemoryFeedbackCreate,
    MemoryFeedbackListResponse,
    MemoryCompactionRequest,
    MemoryCompactionResponse,
    MemoryExpireDueRequest,
    MemoryExpireDueResponse,
    MemoryExpireRequest,
    MemorySaveDecisionRequest,
    MemorySaveDecisionResponse,
    MemoryContradictionCreate,
    MemoryRelationListResponse
)
from app.services.memory_service import MemoryService
from app.services.retrieval_service import RetrievalService
from app.services.save_policy_service import SavePolicyService

import time
from app.services.metrics_service import MetricsService

router = APIRouter(prefix="/memories", tags=["memories"])


@router.post("", response_model=MemoryResponse, status_code=201)
def create_memory(payload: MemoryCreate, db: Session = Depends(get_db)):
    service = MemoryService(db)
    memory = service.create_memory(payload)
    return memory

@router.post("/agents/{agent_id}/memories", response_model=MemoryResponse, status_code=201)
def create_memory_for_agent(agent_id: str, payload: AgentMemoryCreateRequest, db: Session = Depends(get_db)):
    if payload.requesting_agent_id != agent_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="requesting_agent_id must match path agent_id",
        )

    service = MemoryService(db)

    base_payload = MemoryCreate(
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
        confidence_score=payload.confidence_score,
        importance_score=payload.importance_score,
        source=payload.source,
        source_event_id=payload.source_event_id,
        parent_memory_id=payload.parent_memory_id,
        tags=payload.tags,
        valid_from=payload.valid_from,
        valid_until=payload.valid_until,
    )

    try:
        memory = service.create_memory_for_agent(
            requesting_agent_id=payload.requesting_agent_id,
            requesting_tenant_id=payload.requesting_tenant_id,
            payload=base_payload,
        )
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))

    return memory


@router.get("/agents/{agent_id}/accessible-memories", response_model=AgentAccessibleMemoriesResponse)
def list_accessible_memories(
    agent_id: str,
    tenant_id: str | None = Query(default=None),
    memory_type: str | None = Query(default=None),
    user_id: str | None = Query(default=None),
    session_id: str | None = Query(default=None),
    tag: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    service = MemoryService(db)
    items = service.list_accessible_memories(
        requesting_agent_id=agent_id,
        requesting_tenant_id=tenant_id,
        memory_type=memory_type,
        user_id=user_id,
        session_id=session_id,
        tag=tag,
    )
    return {"items": items, "total": len(items)}

@router.post("/agents/{agent_id}/retrieve-context", response_model=RetrievalContextResponse)
def retrieve_context_for_agent(
    agent_id: str,
    payload: AgentRetrieveContextRequest,
    db: Session = Depends(get_db),
):
    started_at = time.perf_counter()

    service = MemoryService(db)
    retrieval_service = RetrievalService()
    metrics_service = MetricsService()

    candidates = service.semantic_search_accessible_candidates(
        requesting_agent_id=agent_id,
        requesting_tenant_id=payload.requesting_tenant_id,
        query_text=payload.query,
        memory_type=payload.memory_type,
        user_id=payload.user_id,
        session_id=payload.session_id,
        tag=payload.tag,
        limit=payload.limit,
    )

    active_memory_ids = {str(memory.memory_id) for memory, _ in candidates}
    scored_items = []

    for memory, semantic_similarity in candidates:
        semantic_similarity = float(semantic_similarity)
        recency_score = retrieval_service.calculate_recency_score(memory.created_at)
        confidence_score = float(memory.confidence_score)
        importance_score = float(memory.importance_score)

        feedback_summary = service.get_feedback_summary(memory.memory_id)
        feedback_score = retrieval_service.calculate_feedback_score(feedback_summary)

        contradiction_count = service.get_contradiction_count(
            memory.memory_id,
            active_memory_ids=active_memory_ids,
        )
        contradiction_penalty = retrieval_service.calculate_contradiction_penalty(
            contradiction_count
        )

        final_score = retrieval_service.calculate_final_score(
            semantic_similarity=semantic_similarity,
            recency_score=recency_score,
            confidence_score=confidence_score,
            importance_score=importance_score,
            feedback_score=feedback_score,
            contradiction_penalty=contradiction_penalty,
            weights=payload.weights,
        )

        scored_items.append(
            {
                "memory": memory,
                "semantic_similarity": semantic_similarity,
                "recency_score": recency_score,
                "confidence_score": confidence_score,
                "importance_score": importance_score,
                "feedback_score": feedback_score,
                "contradiction_penalty": contradiction_penalty,
                "final_score": final_score,
            }
        )

    scored_items.sort(key=lambda x: x["final_score"], reverse=True)
    selected_items = scored_items[: payload.top_k]

    latency_ms = (time.perf_counter() - started_at) * 1000
    metrics_service.record_retrieval(
        latency_ms=latency_ms,
        total_candidates=len(scored_items),
        total_selected=len(selected_items),
    )

    summary = retrieval_service.build_context_summary(selected_items)
    facts = retrieval_service.extract_facts(selected_items)
    episodes = retrieval_service.extract_episodes(selected_items)
    procedures = retrieval_service.extract_procedures(selected_items)

    return {
        "query": payload.query,
        "total_candidates": len(scored_items),
        "total_selected": len(selected_items),
        "items": selected_items,
        "summary": summary,
        "facts": facts,
        "episodes": episodes,
        "procedures": procedures,
    }
@router.post("/search", response_model=MemorySearchResponse)
def search_memories(payload: MemorySearchRequest, db: Session = Depends(get_db)):
    service = MemoryService(db)
    results = service.search_memories(
        query_text=payload.query,
        memory_type=payload.memory_type,
        agent_id=payload.agent_id,
        user_id=payload.user_id,
        session_id=payload.session_id,
        status=payload.status,
        scope=payload.scope,
        tag=payload.tag,
        limit=payload.limit,
    )

    items = [
        {
            "memory": memory,
            "similarity_score": float(similarity_score),
        }
        for memory, similarity_score in results
    ]

    return {
        "items": items,
        "total": len(items),
    }


@router.post("/retrieve-context", response_model=RetrievalContextResponse)
def retrieve_context(payload: RetrieveContextRequest, db: Session = Depends(get_db)):
    started_at = time.perf_counter()

    memory_service = MemoryService(db)
    retrieval_service = RetrievalService()
    metrics_service = MetricsService()

    candidates = memory_service.semantic_search_candidates(
        query_text=payload.query,
        memory_type=payload.memory_type,
        agent_id=payload.agent_id,
        user_id=payload.user_id,
        session_id=payload.session_id,
        status=payload.status,
        scope=payload.scope,
        tag=payload.tag,
        limit=payload.limit,
    )

    active_memory_ids = {str(memory.memory_id) for memory, _ in candidates}
    scored_items = []

    for memory, semantic_similarity in candidates:
        semantic_similarity = float(semantic_similarity)
        recency_score = retrieval_service.calculate_recency_score(memory.created_at)
        confidence_score = float(memory.confidence_score)
        importance_score = float(memory.importance_score)

        feedback_summary = memory_service.get_feedback_summary(memory.memory_id)
        feedback_score = retrieval_service.calculate_feedback_score(feedback_summary)

        contradiction_count = memory_service.get_contradiction_count(
            memory.memory_id,
            active_memory_ids=active_memory_ids,
        )
        contradiction_penalty = retrieval_service.calculate_contradiction_penalty(
            contradiction_count
        )

        final_score = retrieval_service.calculate_final_score(
            semantic_similarity=semantic_similarity,
            recency_score=recency_score,
            confidence_score=confidence_score,
            importance_score=importance_score,
            feedback_score=feedback_score,
            contradiction_penalty=contradiction_penalty,
            weights=payload.weights,
        )

        scored_items.append(
            {
                "memory": memory,
                "semantic_similarity": semantic_similarity,
                "recency_score": recency_score,
                "confidence_score": confidence_score,
                "importance_score": importance_score,
                "feedback_score": feedback_score,
                "contradiction_penalty": contradiction_penalty,
                "final_score": final_score,
            }
        )

    scored_items.sort(key=lambda x: x["final_score"], reverse=True)
    selected_items = scored_items[: payload.top_k]

    latency_ms = (time.perf_counter() - started_at) * 1000
    metrics_service.record_retrieval(
        latency_ms=latency_ms,
        total_candidates=len(scored_items),
        total_selected=len(selected_items),
    )

    summary = retrieval_service.build_context_summary(selected_items)
    facts = retrieval_service.extract_facts(selected_items)
    episodes = retrieval_service.extract_episodes(selected_items)
    procedures = retrieval_service.extract_procedures(selected_items)

    return {
        "query": payload.query,
        "total_candidates": len(scored_items),
        "total_selected": len(selected_items),
        "items": selected_items,
        "summary": summary,
        "facts": facts,
        "episodes": episodes,
        "procedures": procedures,
    }
@router.patch("/{memory_id}", response_model=MemoryResponse)
def update_memory(memory_id: UUID, payload: MemoryUpdate, db: Session = Depends(get_db)):
    service = MemoryService(db)
    memory = service.update_memory(memory_id, payload)

    if not memory:
        raise HTTPException(status_code=404, detail="Memory not found")

    return memory


@router.post("/{memory_id}/invalidate", response_model=MemoryResponse)
def invalidate_memory(memory_id: UUID, payload: MemoryInvalidateRequest, db: Session = Depends(get_db)):
    service = MemoryService(db)
    memory = service.invalidate_memory(
        memory_id=memory_id,
        actor_type=payload.actor_type,
        actor_id=payload.actor_id,
        reason=payload.reason,
    )

    if not memory:
        raise HTTPException(status_code=404, detail="Memory not found")

    return memory


@router.post("/{memory_id}/supersede")
def supersede_memory(memory_id: UUID, payload: MemorySupersedeRequest, db: Session = Depends(get_db)):
    service = MemoryService(db)
    old_memory, new_memory = service.supersede_memory(
        memory_id=memory_id,
        actor_type=payload.actor_type,
        actor_id=payload.actor_id,
        replacement=payload.replacement,
    )

    if not old_memory:
        raise HTTPException(status_code=404, detail="Memory not found")

    return {
        "superseded_memory_id": str(old_memory.memory_id),
        "new_memory_id": str(new_memory.memory_id),
        "old_status": old_memory.status,
        "new_status": new_memory.status,
    }


@router.get("/{memory_id}/history", response_model=MemoryHistoryListResponse)
def get_memory_history(memory_id: UUID, db: Session = Depends(get_db)):
    service = MemoryService(db)
    items = service.get_memory_history(memory_id)
    return {"items": items, "total": len(items)}

@router.post("/{memory_id}/feedback")
def add_feedback_to_memory(
    memory_id: UUID,
    payload: MemoryFeedbackCreate,
    db: Session = Depends(get_db),
):
    service = MemoryService(db)
    memory, feedback = service.add_feedback(memory_id, payload)

    if not memory:
        raise HTTPException(status_code=404, detail="Memory not found")

    return {
        "memory_id": str(memory.memory_id),
        "updated_confidence_score": memory.confidence_score,
        "feedback": {
            "feedback_id": str(feedback.feedback_id),
            "verdict": feedback.verdict,
            "actor_type": feedback.actor_type,
            "actor_id": feedback.actor_id,
            "comment": feedback.comment,
            "score_delta": feedback.score_delta,
            "created_at": feedback.created_at,
        },
    }


@router.get("/{memory_id}/feedback", response_model=MemoryFeedbackListResponse)
def get_memory_feedback(memory_id: UUID, db: Session = Depends(get_db)):
    service = MemoryService(db)
    memory, items = service.get_feedback_for_memory(memory_id)

    if not memory:
        raise HTTPException(status_code=404, detail="Memory not found")

    return {
        "items": items,
        "total": len(items),
    }

@router.post("/compact", response_model=MemoryCompactionResponse)
def compact_memories(payload: MemoryCompactionRequest, db: Session = Depends(get_db)):
    service = MemoryService(db)
    result = service.compact_memories(payload)
    return result

@router.post("/{memory_id}/expire", response_model=MemoryResponse)
def expire_memory(
    memory_id: UUID,
    payload: MemoryExpireRequest,
    db: Session = Depends(get_db),
):
    service = MemoryService(db)
    memory = service.expire_memory(
        memory_id=memory_id,
        actor_type=payload.actor_type,
        actor_id=payload.actor_id,
        reason=payload.reason,
    )

    if not memory:
        raise HTTPException(status_code=404, detail="Memory not found")

    return memory


@router.post("/expire-due", response_model=MemoryExpireDueResponse)
def expire_due_memories(
    payload: MemoryExpireDueRequest,
    db: Session = Depends(get_db),
):
    service = MemoryService(db)
    result = service.expire_due_memories(
        actor_type=payload.actor_type,
        actor_id=payload.actor_id,
        limit=payload.limit,
    )
    return result

@router.post("/decide-save", response_model=MemorySaveDecisionResponse)
def decide_save_policy(payload: MemorySaveDecisionRequest):
    service = SavePolicyService()
    result = service.decide(
        title=payload.title,
        content=payload.content,
        memory_type=payload.memory_type,
        scope=payload.scope,
        importance_score=payload.importance_score,
        confidence_score=payload.confidence_score,
        tags=payload.tags,
        agent_id=payload.agent_id,
        tenant_id=payload.tenant_id,
        session_id=payload.session_id,
        structured_payload=payload.structured_payload,
    )
    return result

@router.post("/{memory_id}/contradict")
def contradict_memory(
    memory_id: UUID,
    payload: MemoryContradictionCreate,
    db: Session = Depends(get_db),
):
    service = MemoryService(db)
    source_memory, target_memory, relation = service.add_contradiction(memory_id, payload)

    if not source_memory or not target_memory:
        raise HTTPException(status_code=404, detail="Source or target memory not found")

    return {
        "ok": True,
        "source_memory_id": str(source_memory.memory_id),
        "target_memory_id": str(target_memory.memory_id),
        "relation_id": str(relation.relation_id),
        "relation_type": relation.relation_type,
        "message": "Contradiction relation created successfully.",
    }


@router.get("/{memory_id}/relations", response_model=MemoryRelationListResponse)
def get_memory_relations(memory_id: UUID, db: Session = Depends(get_db)):
    service = MemoryService(db)
    memory, items = service.get_memory_relations(memory_id)

    if not memory:
        raise HTTPException(status_code=404, detail="Memory not found")

    return {
        "items": items,
        "total": len(items),
    }

@router.get("/{memory_id}", response_model=MemoryResponse)
def get_memory(memory_id: UUID, db: Session = Depends(get_db)):
    service = MemoryService(db)
    memory = service.get_memory(memory_id)

    if not memory:
        raise HTTPException(status_code=404, detail="Memory not found")

    return memory


@router.get("", response_model=MemoryListResponse)
def list_memories(
    memory_type: str | None = Query(default=None),
    agent_id: str | None = Query(default=None),
    user_id: str | None = Query(default=None),
    session_id: str | None = Query(default=None),
    status: str | None = Query(default=None),
    scope: str | None = Query(default=None),
    tag: str | None = Query(default=None),
    enforce_validity: bool = Query(default=False),
    db: Session = Depends(get_db),
):
    service = MemoryService(db)
    items = service.list_memories(
        memory_type=memory_type,
        agent_id=agent_id,
        user_id=user_id,
        session_id=session_id,
        status=status,
        scope=scope,
        tag=tag,
        enforce_validity=enforce_validity,
    )
    return {"items": items, "total": len(items)}