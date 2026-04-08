import json
import os
from datetime import datetime, timezone

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.memory import MemoryRecord


class MetricsService:
    def __init__(self):
        self.metrics_file = settings.retrieval_metrics_file

    def _ensure_file(self):
        os.makedirs(os.path.dirname(self.metrics_file), exist_ok=True)
        if not os.path.exists(self.metrics_file):
            with open(self.metrics_file, "w", encoding="utf-8") as f:
                json.dump(
                    {
                        "retrieval_requests_total": 0,
                        "retrieval_total_latency_ms": 0.0,
                        "retrieval_avg_latency_ms": 0.0,
                        "retrieval_total_candidates": 0,
                        "retrieval_avg_candidates": 0.0,
                        "retrieval_total_selected": 0,
                        "retrieval_avg_selected": 0.0,
                        "retrieval_last_run_at": None,
                    },
                    f,
                    indent=2,
                )

    def read_retrieval_metrics(self) -> dict:
        self._ensure_file()
        with open(self.metrics_file, "r", encoding="utf-8") as f:
            return json.load(f)

    def record_retrieval(self, latency_ms: float, total_candidates: int, total_selected: int) -> dict:
        metrics = self.read_retrieval_metrics()

        metrics["retrieval_requests_total"] += 1
        metrics["retrieval_total_latency_ms"] += latency_ms
        metrics["retrieval_total_candidates"] += total_candidates
        metrics["retrieval_total_selected"] += total_selected
        metrics["retrieval_last_run_at"] = datetime.now(timezone.utc).isoformat()

        total = metrics["retrieval_requests_total"]
        metrics["retrieval_avg_latency_ms"] = metrics["retrieval_total_latency_ms"] / total
        metrics["retrieval_avg_candidates"] = metrics["retrieval_total_candidates"] / total
        metrics["retrieval_avg_selected"] = metrics["retrieval_total_selected"] / total

        with open(self.metrics_file, "w", encoding="utf-8") as f:
            json.dump(metrics, f, indent=2)

        return metrics

    def get_memory_stats(self, db: Session) -> dict:
        total_memories = db.query(func.count(MemoryRecord.memory_id)).scalar() or 0

        status_rows = (
            db.query(MemoryRecord.status, func.count(MemoryRecord.memory_id))
            .group_by(MemoryRecord.status)
            .all()
        )
        type_rows = (
            db.query(MemoryRecord.memory_type, func.count(MemoryRecord.memory_id))
            .group_by(MemoryRecord.memory_type)
            .all()
        )
        scope_rows = (
            db.query(MemoryRecord.scope, func.count(MemoryRecord.memory_id))
            .group_by(MemoryRecord.scope)
            .all()
        )
        tenant_rows = (
            db.query(MemoryRecord.tenant_id, func.count(MemoryRecord.memory_id))
            .group_by(MemoryRecord.tenant_id)
            .all()
        )

        retrieval_metrics = self.read_retrieval_metrics()

        return {
            "total_memories": total_memories,
            "by_status": {status or "null": count for status, count in status_rows},
            "by_memory_type": {memory_type or "null": count for memory_type, count in type_rows},
            "by_scope": {scope or "null": count for scope, count in scope_rows},
            "by_tenant": {(tenant_id or "null"): count for tenant_id, count in tenant_rows},
            "retrieval_metrics": retrieval_metrics,
        }