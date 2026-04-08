from fastapi import FastAPI
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

from app.api.routes.evaluation import router as evaluation_router
from app.api.routes.health import router as health_router
from app.api.routes.memories import router as memories_router
from app.api.routes.metrics import router as metrics_router
from app.api.routes.sessions import router as sessions_router
from app.core.config import settings
from app.core.tracing import setup_tracing

setup_tracing()

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="Persistent memory backend for LLM agents",
)

app.include_router(health_router)
app.include_router(memories_router)
app.include_router(sessions_router)
app.include_router(metrics_router)
app.include_router(evaluation_router)

FastAPIInstrumentor.instrument_app(app)