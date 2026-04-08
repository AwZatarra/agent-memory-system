import json
from datetime import datetime, timezone

from app.core.config import settings
from app.core.redis_client import get_redis_client
from app.schemas.memory import (
    ContextWindowRequest,
    ContextWindowResponse,
    ShortTermMemoryResponse,
    ShortTermMemoryWriteRequest,
)
from app.core.tracing import get_tracer


class ShortTermMemoryService:
    def __init__(self):
        self.redis = get_redis_client()
        self.tracer = get_tracer("short-term-memory-service")

    def _key(self, agent_id: str, session_id: str) -> str:
        return f"stm:{agent_id}:{session_id}"

    def write(self, session_id: str, payload: ShortTermMemoryWriteRequest) -> ShortTermMemoryResponse:
        with self.tracer.start_as_current_span("short_term_memory.write") as span:
            now = datetime.now(timezone.utc)

            messages = payload.messages[-settings.short_term_max_messages :]
            tool_calls = payload.tool_calls[-settings.short_term_max_tool_calls :]

            data = {
                "agent_id": payload.agent_id,
                "session_id": session_id,
                "messages": [m.model_dump(mode="json") for m in messages],
                "tool_calls": [t.model_dump(mode="json") for t in tool_calls],
                "current_goal": payload.current_goal,
                "execution_state": payload.execution_state,
                "last_updated_at": now.isoformat(),
            }

            key = self._key(payload.agent_id, session_id)

            self.redis.set(key, json.dumps(data))
            self.redis.expire(key, settings.short_term_ttl_seconds)

            ttl = self.redis.ttl(key)

            span.set_attribute("session.id", session_id)
            span.set_attribute("agent.id", payload.agent_id)
            span.set_attribute("messages.count", len(messages))
            span.set_attribute("tool_calls.count", len(tool_calls))
            span.set_attribute("ttl.seconds", ttl if ttl > 0 else settings.short_term_ttl_seconds)

            return ShortTermMemoryResponse(
                agent_id=payload.agent_id,
                session_id=session_id,
                messages=messages,
                tool_calls=tool_calls,
                current_goal=payload.current_goal,
                execution_state=payload.execution_state,
                ttl_seconds=ttl if ttl > 0 else settings.short_term_ttl_seconds,
                last_updated_at=now,
            )
        
    def get(self, agent_id: str, session_id: str) -> ShortTermMemoryResponse | None:
        with self.tracer.start_as_current_span("short_term_memory.get") as span:
            key = self._key(agent_id, session_id)
            raw = self.redis.get(key)

            span.set_attribute("session.id", session_id)
            span.set_attribute("agent.id", agent_id)

            if not raw:
                span.set_attribute("short_term_memory.found", False)
                return None

            span.set_attribute("short_term_memory.found", True)

            data = json.loads(raw)
            ttl = self.redis.ttl(key)

            return ShortTermMemoryResponse(
                agent_id=data["agent_id"],
                session_id=data["session_id"],
                messages=data.get("messages", []),
                tool_calls=data.get("tool_calls", []),
                current_goal=data.get("current_goal"),
                execution_state=data.get("execution_state"),
                ttl_seconds=ttl if ttl > 0 else 0,
                last_updated_at=datetime.fromisoformat(data["last_updated_at"]),
            )
        
    def delete(self, agent_id: str, session_id: str) -> bool:
        key = self._key(agent_id, session_id)
        deleted = self.redis.delete(key)
        return deleted > 0

    def build_context_window(self, session_id: str, payload: ContextWindowRequest) -> ContextWindowResponse | None:
        stm = self.get(payload.agent_id, session_id)

        if not stm:
            return None

        lines: list[str] = []

        if payload.include_goal and stm.current_goal:
            lines.append(f"Current goal: {stm.current_goal}")

        if payload.include_execution_state and stm.execution_state:
            lines.append(f"Execution state: {json.dumps(stm.execution_state, ensure_ascii=False)}")

        if payload.include_messages and stm.messages:
            lines.append("Recent messages:")
            for msg in stm.messages:
                lines.append(f"- [{msg.role}] {msg.content}")

        if payload.include_tool_calls and stm.tool_calls:
            lines.append("Recent tool calls:")
            for call in stm.tool_calls:
                lines.append(
                    f"- {call.tool_name} | input={json.dumps(call.input, ensure_ascii=False)} "
                    f"| output={json.dumps(call.output, ensure_ascii=False)}"
                )

        return ContextWindowResponse(
            agent_id=stm.agent_id,
            session_id=stm.session_id,
            context_window="\n".join(lines) if lines else "No short-term context available.",
            message_count=len(stm.messages),
            tool_call_count=len(stm.tool_calls),
            current_goal=stm.current_goal,
            execution_state=stm.execution_state,
        )