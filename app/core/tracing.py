from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter

from app.core.config import settings


def setup_tracing():
    resource = Resource.create(
        {
            "service.name": settings.otel_service_name,
        }
    )

    provider = TracerProvider(resource=resource)

    if settings.otel_enable_console_exporter:
        processor = BatchSpanProcessor(ConsoleSpanExporter())
        provider.add_span_processor(processor)

    trace.set_tracer_provider(provider)


def get_tracer(name: str = "agent-memory-system"):
    return trace.get_tracer(name)