CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS memory_records (
    memory_id UUID PRIMARY KEY,
    tenant_id VARCHAR(100),
    agent_id VARCHAR(100),
    user_id VARCHAR(100),
    session_id VARCHAR(100),
    memory_type VARCHAR(50) NOT NULL,
    scope VARCHAR(50) NOT NULL DEFAULT 'private',
    title VARCHAR(255) NOT NULL,
    content TEXT NOT NULL,
    summary TEXT,
    structured_payload JSONB,
    embedding VECTOR(1536),
    confidence_score DOUBLE PRECISION NOT NULL DEFAULT 0.5,
    importance_score DOUBLE PRECISION NOT NULL DEFAULT 0.5,
    source VARCHAR(50) NOT NULL DEFAULT 'agent',
    source_event_id VARCHAR(100),
    status VARCHAR(50) NOT NULL DEFAULT 'active',
    version INTEGER NOT NULL DEFAULT 1,
    parent_memory_id UUID NULL,
    valid_from TIMESTAMP NULL,
    valid_until TIMESTAMP NULL,
    tags TEXT[] DEFAULT '{}',
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    last_accessed_at TIMESTAMP NULL,
    access_count INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_memory_type ON memory_records(memory_type);
CREATE INDEX IF NOT EXISTS idx_agent_id ON memory_records(agent_id);
CREATE INDEX IF NOT EXISTS idx_user_id ON memory_records(user_id);
CREATE INDEX IF NOT EXISTS idx_session_id ON memory_records(session_id);
CREATE INDEX IF NOT EXISTS idx_status ON memory_records(status);
CREATE INDEX IF NOT EXISTS idx_scope ON memory_records(scope);

CREATE INDEX IF NOT EXISTS idx_memory_embedding
ON memory_records
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

CREATE TABLE IF NOT EXISTS memory_history (
    history_id UUID PRIMARY KEY,
    memory_id UUID NOT NULL,
    event_type VARCHAR(50) NOT NULL,
    actor_type VARCHAR(50) NOT NULL,
    actor_id VARCHAR(100),
    old_value JSONB,
    new_value JSONB,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_memory_history_memory_id ON memory_history(memory_id);
CREATE INDEX IF NOT EXISTS idx_memory_history_event_type ON memory_history(event_type);

CREATE TABLE IF NOT EXISTS memory_feedback (
    feedback_id UUID PRIMARY KEY,
    memory_id UUID NOT NULL,
    verdict VARCHAR(50) NOT NULL,
    actor_type VARCHAR(50) NOT NULL,
    actor_id VARCHAR(100),
    comment TEXT,
    score_delta DOUBLE PRECISION NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_memory_feedback_memory_id ON memory_feedback(memory_id);
CREATE INDEX IF NOT EXISTS idx_memory_feedback_verdict ON memory_feedback(verdict);

CREATE TABLE IF NOT EXISTS memory_relations (
    relation_id UUID PRIMARY KEY,
    from_memory_id UUID NOT NULL,
    to_memory_id UUID NOT NULL,
    relation_type VARCHAR(50) NOT NULL,
    actor_type VARCHAR(50) NOT NULL,
    actor_id VARCHAR(100),
    comment TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_memory_relations_from_memory_id
ON memory_relations(from_memory_id);

CREATE INDEX IF NOT EXISTS idx_memory_relations_to_memory_id
ON memory_relations(to_memory_id);

CREATE INDEX IF NOT EXISTS idx_memory_relations_relation_type
ON memory_relations(relation_type);