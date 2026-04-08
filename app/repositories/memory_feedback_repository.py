from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.memory_feedback import MemoryFeedback


class MemoryFeedbackRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(
        self,
        memory_id,
        verdict: str,
        actor_type: str,
        actor_id: str | None,
        comment: str | None,
        score_delta: float,
    ) -> MemoryFeedback:
        item = MemoryFeedback(
            memory_id=memory_id,
            verdict=verdict,
            actor_type=actor_type,
            actor_id=actor_id,
            comment=comment,
            score_delta=score_delta,
        )
        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)
        return item

    def list_by_memory_id(self, memory_id):
        return (
            self.db.query(MemoryFeedback)
            .filter(MemoryFeedback.memory_id == memory_id)
            .order_by(MemoryFeedback.created_at.asc())
            .all()
        )

    def get_feedback_summary(self, memory_id) -> dict:
        items = (
            self.db.query(MemoryFeedback.verdict, func.count(MemoryFeedback.feedback_id))
            .filter(MemoryFeedback.memory_id == memory_id)
            .group_by(MemoryFeedback.verdict)
            .all()
        )

        counts = {
            "useful": 0,
            "partially_useful": 0,
            "not_useful": 0,
        }

        total = 0
        for verdict, count in items:
            counts[verdict] = count
            total += count

        return {
            "total_feedback": total,
            "counts": counts,
        }