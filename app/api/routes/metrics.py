from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.services.metrics_service import MetricsService

router = APIRouter(prefix="/metrics", tags=["metrics"])


@router.get("/memory-stats")
def get_memory_stats(db: Session = Depends(get_db)):
    service = MetricsService()
    return service.get_memory_stats(db)