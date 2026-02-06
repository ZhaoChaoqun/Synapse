# InsightSentinel Backend

FastAPI backend for the InsightSentinel AI Intelligence Agent.

## Tech Stack

- **Framework**: FastAPI
- **Database**: PostgreSQL + pgvector
- **Cache**: Redis
- **LLM**: Google Gemini API

## Project Structure

```
backend/
├── app/
│   ├── api/              # API endpoints
│   │   └── v1/
│   │       ├── endpoints/
│   │       └── schemas/
│   ├── core/             # Core business logic
│   │   ├── agent/        # Agentic Loop
│   │   ├── llm/          # LLM abstraction
│   │   ├── tools/        # Agent tools
│   │   └── resilience/   # Error recovery
│   ├── crawlers/         # Platform crawlers
│   │   ├── wechat/
│   │   ├── zhihu/
│   │   ├── xiaohongshu/
│   │   ├── douyin/
│   │   └── anti_detect/
│   ├── memory/           # Memory system
│   ├── models/           # Database models
│   ├── services/         # Business services
│   └── utils/            # Utilities
├── migrations/           # Alembic migrations
├── tests/                # Tests
└── pyproject.toml        # Dependencies
```

## Setup

### Prerequisites

- Python 3.11+
- PostgreSQL 15+ with pgvector extension
- Redis 7+

### Installation

1. Create virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -e ".[dev]"
```

3. Copy environment file:
```bash
cp .env.example .env
# Edit .env with your configuration
```

4. Run database migrations:
```bash
alembic upgrade head
```

5. Start the server:
```bash
uvicorn app.main:app --reload
```

## API Documentation

Once the server is running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## API Endpoints

### Agent
- `POST /api/v1/agent/execute` - Execute agent command (SSE)
- `GET /api/v1/agent/tasks/{task_id}` - Get task details
- `GET /api/v1/agent/tasks` - List tasks

### Intelligence
- `POST /api/v1/intelligence/search` - Search intelligence
- `GET /api/v1/intelligence/timeline` - Get timeline events

### Platforms
- `GET /api/v1/platforms/stats` - Get platform statistics
- `GET /api/v1/platforms/network` - Get knowledge graph

## Development

### Running Tests

```bash
pytest
```

### Code Formatting

```bash
black app/
ruff check app/ --fix
```

### Type Checking

```bash
mypy app/
```
