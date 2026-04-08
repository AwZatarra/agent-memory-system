# 🧠 Sistema de Memoria para Agentes LLM

Backend que funciona como un **cerebro persistente para agentes**.

Permite que uno o varios agentes puedan:

- guardar conocimiento útil
- recuperar contexto por similitud semántica
- compartir memoria entre agentes
- recordar decisiones previas
- aprender con feedback
- expirar, invalidar y versionar conocimiento
- separar memoria de corto plazo y memoria de largo plazo

En pocas palabras: este proyecto busca que los agentes **no empiecen de cero en cada ejecución**.

---

## 🚀 Qué hace

El sistema combina dos tipos de memoria:

### Short-term memory
Memoria temporal de sesión usando Redis.

Ejemplos:
- últimos mensajes
- objetivo actual
- estado de ejecución
- herramientas usadas recientemente

### Long-term memory
Memoria persistente usando PostgreSQL + pgvector.

Ejemplos:
- hechos importantes
- decisiones previas
- incidentes
- playbooks
- conocimiento consolidado

Además, el sistema soporta:

- búsqueda semántica
- ranking híbrido
- feedback sobre memorias útiles o no útiles
- compaction de memorias viejas
- manejo de contradicciones
- expiración de conocimiento obsoleto

---

## 🛠️ Tecnologías

- **Python**
- **FastAPI**
- **PostgreSQL**
- **pgvector**
- **Redis**
- **OpenAI**
- **Docker Compose**
- **OpenTelemetry**

---

## 📦 Instalación

### 1. Clonar el repositorio

```bash
git clone https://github.com/TU_USUARIO/TU_REPO.git
cd TU_REPO
```

### 2. Crear el archivo `.env`

```bash
cp .env.example .env
```

En Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

### 3. Completar variables importantes

Ejemplo:

```env
OPENAI_API_KEY=tu_api_key
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
OPENAI_CHAT_MODEL=gpt-4.1-mini

DATABASE_URL=postgresql://postgres:postgres@db:5432/agent_memory

REDIS_HOST=redis
REDIS_PORT=6379
REDIS_DB=0
```

---

## ▶️ Cómo arrancarlo

Levanta todo con Docker Compose:

```bash
docker compose up --build
```

Cuando termine de levantar:

- API: `http://localhost:8000`
- Swagger: `http://localhost:8000/docs`

---

# 📂 Estructura del proyecto

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

## 📌 Flujo general

1. guardar memorias
2. recuperar contexto relevante
3. aplicar feedback
4. versionar o invalidar conocimiento
5. compactar memorias viejas
6. seguir reutilizando conocimiento útil entre ejecuciones

---

## 💡 Valor del proyecto

Este proyecto demuestra experiencia en:

- backend engineering
- diseño de sistemas
- retrieval systems
- memory systems para agentes
- lifecycle de conocimiento
- observabilidad y evaluación

---

## 👨‍💻 Autor

**Pool Rivera Molina**

- LinkedIn: [Pool Rivera Molina](https://www.linkedin.com/in/pool-rivera-molina/)
- GitHub: [Git Pool Rivera](https://github.com/AwZatarra)

