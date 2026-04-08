from openai import OpenAI

from app.core.config import settings


class EmbeddingService:
    def __init__(self):
        if not settings.openai_api_key:
            raise ValueError("OPENAI_API_KEY is required when embeddings are enabled")

        self.client = OpenAI(api_key=settings.openai_api_key)

    def build_memory_text(
        self,
        title: str,
        content: str,
        summary: str | None = None,
        tags: list[str] | None = None,
    ) -> str:
        parts = [
            f"title: {title}",
            f"content: {content}",
        ]

        if summary:
            parts.append(f"summary: {summary}")

        if tags:
            parts.append(f"tags: {', '.join(tags)}")

        return "\n".join(parts)

    def generate_embedding(self, text: str) -> list[float]:
        response = self.client.embeddings.create(
            model=settings.openai_embedding_model,
            input=text,
        )
        return response.data[0].embedding