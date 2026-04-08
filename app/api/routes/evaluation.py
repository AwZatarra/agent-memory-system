from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.services.evaluation_service import EvaluationService

router = APIRouter(prefix="/evaluation", tags=["evaluation"])


@router.post("/run")
def run_evaluation(db: Session = Depends(get_db)):
    service = EvaluationService()
    return service.run(db)


@router.get("/report")
def get_evaluation_report():
    service = EvaluationService()
    return service.read_report()