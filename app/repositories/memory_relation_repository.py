from sqlalchemy.orm import Session

from app.models.memory_relation import MemoryRelation


class MemoryRelationRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(
        self,
        from_memory_id,
        to_memory_id,
        relation_type: str,
        actor_type: str,
        actor_id: str | None = None,
        comment: str | None = None,
    ) -> MemoryRelation:
        item = MemoryRelation(
            from_memory_id=from_memory_id,
            to_memory_id=to_memory_id,
            relation_type=relation_type,
            actor_type=actor_type,
            actor_id=actor_id,
            comment=comment,
        )
        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)
        return item

    def list_by_memory_id(self, memory_id):
        return (
            self.db.query(MemoryRelation)
            .filter(
                (MemoryRelation.from_memory_id == memory_id)
                | (MemoryRelation.to_memory_id == memory_id)
            )
            .order_by(MemoryRelation.created_at.asc())
            .all()
        )

    def count_active_contradictions_against_memory(self, memory_id, active_memory_ids: set[str]) -> int:
        relations = (
            self.db.query(MemoryRelation)
            .filter(
                MemoryRelation.to_memory_id == memory_id,
                MemoryRelation.relation_type == "contradicts",
            )
            .all()
        )

        count = 0
        for relation in relations:
            if str(relation.from_memory_id) in active_memory_ids:
                count += 1

        return count