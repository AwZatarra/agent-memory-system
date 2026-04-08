from fastapi import APIRouter, HTTPException, Query

from app.schemas.memory import (
    ContextWindowRequest,
    ContextWindowResponse,
    ShortTermMemoryResponse,
    ShortTermMemoryWriteRequest,
)
from app.services.short_term_memory_service import ShortTermMemoryService

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.post("/{session_id}/short-term", response_model=ShortTermMemoryResponse)
def write_short_term_memory(session_id: str, payload: ShortTermMemoryWriteRequest):
    service = ShortTermMemoryService()
    return service.write(session_id, payload)


@router.get("/{session_id}/short-term", response_model=ShortTermMemoryResponse)
def get_short_term_memory(session_id: str, agent_id: str = Query(...)):
    service = ShortTermMemoryService()
    result = service.get(agent_id=agent_id, session_id=session_id)

    if not result:
        raise HTTPException(status_code=404, detail="Short-term memory not found")

    return result


@router.delete("/{session_id}/short-term")
def delete_short_term_memory(session_id: str, agent_id: str = Query(...)):
    service = ShortTermMemoryService()
    deleted = service.delete(agent_id=agent_id, session_id=session_id)

    if not deleted:
        raise HTTPException(status_code=404, detail="Short-term memory not found")

    return {
        "ok": True,
        "session_id": session_id,
        "agent_id": agent_id,
        "deleted": True,
    }


@router.post("/{session_id}/context-window", response_model=ContextWindowResponse)
def build_context_window(session_id: str, payload: ContextWindowRequest):
    service = ShortTermMemoryService()
    result = service.build_context_window(session_id=session_id, payload=payload)

    if not result:
        raise HTTPException(status_code=404, detail="Short-term memory not found")

    return result