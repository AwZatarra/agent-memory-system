from sqlalchemy.orm import Session

from app.models.memory_history import MemoryHistory


class MemoryHistoryRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(
        self,
        memory_id,
        event_type: str,
        actor_type: str,
        actor_id: str | None = None,
        old_value: dict | None = None,
        new_value: dict | None = None,
    ) -> MemoryHistory:
        item = MemoryHistory(
            memory_id=memory_id,
            event_type=event_type,
            actor_type=actor_type,
            actor_id=actor_id,
            old_value=old_value,
            new_value=new_value,
        )
        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)
        return item

    def list_by_memory_id(self, memory_id):
        return (
            self.db.query(MemoryHistory)
            .filter(MemoryHistory.memory_id == memory_id)
            .order_by(MemoryHistory.created_at.asc())
            .all()
        )