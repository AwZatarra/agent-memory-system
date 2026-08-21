# 🧠 Memory System for LLM Agents

Backend that works as a **persistent brain for agents**.

It allows one or multiple agents to:

- store useful knowledge
- retrieve context through semantic similarity
- share memory between agents
- remember previous decisions
- learn from feedback
- expire, invalidate, and version knowledge
- separate short-term memory from long-term memory

In short: this project aims to ensure that agents **do not start from scratch on every execution**.

---

## 🚀 What it does

The system combines two types of memory:

### Short-term memory
Temporary session memory using Redis.

Examples:
- latest messages
- current goal
- execution state
- recently used tools

### Long-term memory
Persistent memory using PostgreSQL + pgvector.

Examples:
- important facts
- previous decisions
- incidents
- playbooks
- consolidated knowledge

In addition, the system supports:

- semantic search
- hybrid ranking
- feedback on useful or non-useful memories
- compaction of old memories
- contradiction handling
- expiration of obsolete knowledge

---

## 🛠️ Technologies

- **Python**
- **FastAPI**
- **PostgreSQL**
- **pgvector**
- **Redis**
- **OpenAI**
- **Docker Compose**
- **OpenTelemetry**

---

## 📦 Installation

### 1. Clone the repository

```bash
git clone https://github.com/AwZatarra/agent-memory-system.git
cd agent-memory-system
```

### 2. Create the `.env` file

```bash
cp .env.example .env
```

On Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

### 3. Fill in the important variables

Example:

```env
APP_NAME=Agent Memory System
APP_ENV=development
APP_PORT=8000

POSTGRES_HOST=db
POSTGRES_PORT=5432
POSTGRES_DB=agent_memory
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres

DATABASE_URL=postgresql://postgres:postgres@db:5432/agent_memory

OPENAI_API_KEY=api_key
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
EMBEDDING_DIMENSIONS=1536
ENABLE_EMBEDDINGS=true
OPENAI_CHAT_MODEL=gpt-4.1-mini
ENABLE_LLM_COMPACTION=true

REDIS_HOST=redis
REDIS_PORT=6379
REDIS_DB=0
SHORT_TERM_TTL_SECONDS=7200
SHORT_TERM_MAX_MESSAGES=20
SHORT_TERM_MAX_TOOL_CALLS=20

OTEL_SERVICE_NAME=agent-memory-system
OTEL_ENABLE_CONSOLE_EXPORTER=true
```

---

## ▶️ How to run it

Start everything with Docker Compose:

```bash
docker compose up --build
```

Once everything is up and running:

- API: `http://localhost:8000`
- Swagger: `http://localhost:8000/docs`

---

# 📂 Project structure

```bash
app/
├── api/
│   └── routes/
├── core/
├── models/
├── repositories/
├── schemas/
├── services/
├── main.py
sql/
data/
tests/
docker-compose.yml
Dockerfile
requirements.txt
README.md
```

---

## 📌 General flow

1. store memories
2. retrieve relevant context
3. apply feedback
4. version or invalidate knowledge
5. compact old memories
6. continue reusing useful knowledge across executions

---

## 💡 Project value

This project demonstrates experience in:

- backend engineering
- system design
- retrieval systems
- memory systems for agents
- knowledge lifecycle
- observability and evaluation

---

## 👨‍💻 Author

**Pool Rivera Molina**

- LinkedIn: [Pool Rivera Molina](https://www.linkedin.com/in/pool-rivera-molina/)
- GitHub: [poolriveramolina](https://github.com/AwZatarra)
