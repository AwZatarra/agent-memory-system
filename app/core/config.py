from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Agent Memory System"
    app_env: str = "development"
    app_port: int = 8000

    postgres_host: str = "db"
    postgres_port: int = 5432
    postgres_db: str = "agent_memory"
    postgres_user: str = "postgres"
    postgres_password: str = "postgres"
    database_url: str = "postgresql://postgres:postgres@db:5432/agent_memory"

    openai_api_key: str = ""
    openai_embedding_model: str = "text-embedding-3-small"
    openai_chat_model: str = "gpt-4.1-mini"
    embedding_dimensions: int = 1536
    enable_embeddings: bool = True
    enable_llm_compaction: bool = True

    redis_host: str = "redis"
    redis_port: int = 6379
    redis_db: int = 0

    short_term_ttl_seconds: int = 7200
    short_term_max_messages: int = 20
    short_term_max_tool_calls: int = 20

    retrieval_metrics_file: str = "data/retrieval_metrics.json"
    evaluation_dataset_file: str = "data/evaluation_dataset.json"
    evaluation_report_file: str = "data/evaluation_report.json"

    otel_service_name: str = "agent-memory-system"
    otel_enable_console_exporter: bool = True

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()