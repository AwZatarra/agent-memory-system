from app.models.memory import MemoryRecord


class AccessControlService:
    def can_write_memory(
        self,
        requesting_agent_id: str,
        requesting_tenant_id: str | None,
        target_agent_id: str | None,
        target_tenant_id: str | None,
        scope: str,
        source: str,
    ) -> tuple[bool, str | None]:
        if target_agent_id and target_agent_id != requesting_agent_id:
            return False, "Agents can only write memories for themselves in MVP mode"

        if target_tenant_id != requesting_tenant_id:
            return False, "Tenant mismatch: cannot write memory for another tenant"

        if scope == "private":
            return True, None

        if scope == "shared":
            if not requesting_tenant_id:
                return False, "Shared memory requires a tenant_id"
            return True, None

        if scope == "global":
            if source not in {"human", "system"}:
                return False, "Only human or system sources can write global memory in MVP mode"
            return True, None

        return False, "Invalid scope"

    def can_read_memory(
        self,
        memory: MemoryRecord,
        requesting_agent_id: str,
        requesting_tenant_id: str | None,
    ) -> bool:
        if memory.status != "active":
            return False

        if memory.scope == "private":
            return memory.agent_id == requesting_agent_id

        if memory.scope == "shared":
            return (
                memory.tenant_id is not None
                and requesting_tenant_id is not None
                and memory.tenant_id == requesting_tenant_id
            )

        if memory.scope == "global":
            if memory.tenant_id is None:
                return True
            return requesting_tenant_id == memory.tenant_id

        return False