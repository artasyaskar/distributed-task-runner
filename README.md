# Distributed Task Processing System

A production-ready system for processing long-running tasks asynchronously without blocking your API.

## Architecture

This system demonstrates real-world distributed architecture with:
- **FastAPI** for the API layer (fast, non-blocking)
- **Async Workers** for heavy task processing
- **Message Queue** for decoupling API from workers
- **Database** for task persistence and state tracking
- **Retry Logic** for fault tolerance
- **Logging & Monitoring** for observability

## Quick Start

### Prerequisites
- Python 3.11+
- Redis (optional for Phase 2+)
- SQLite (included) or PostgreSQL

### Installation

1. Clone and install dependencies:
```bash
pip install -r requirements.txt
```

2. Copy environment file:
```bash
cp .env.example .env
```

3. Start the API server:
```bash
python -m app.main
```

4. In a separate terminal, start the worker:
```bash
python -m app.workers.worker
```

## API Usage

### Create a Task
```bash
curl -X POST "http://localhost:8000/tasks/" \
  -H "Content-Type: application/json" \
  -d '{
    "task_type": "text_processing",
    "payload": {
      "text": "This is a sample text for processing."
    }
  }'
```

### Check Task Status
```bash
curl "http://localhost:8000/tasks/1"
```

### List All Tasks
```bash
curl "http://localhost:8000/tasks/"
```

## Task Types

- **text_processing**: Simple text manipulation (3s)
- **ai_summarization**: Mock AI summarization (5s)
- **batch_processing**: Batch data processing (variable time)
- **image_processing**: Mock image processing (4s)

## Development Phases

### Phase 1: Basic Async Job System ✅
- Task submission via API
- Background worker processing
- Status polling
- SQLite persistence

### Phase 2: Message Queue Integration
- Redis queue for true decoupling
- Worker listens continuously
- API just pushes jobs

### Phase 3: Retry Logic & Failure Handling
- Configurable retry attempts
- Exponential backoff
- Permanent failure handling

### Phase 4: Logging & Monitoring
- Task execution metrics
- Performance tracking
- Failure rate analysis

### Phase 5: Concurrency & Scaling
- Multiple worker processes
- Task prioritization
- Load balancing

### Phase 6: Dockerized Distributed Setup
- Multi-container setup
- Production deployment
- Horizontal scaling

## Key Concepts Demonstrated

- **Non-blocking API**: Fast response times
- **Task States**: Pending → Running → Completed/Failed
- **Fault Tolerance**: Retry logic and error handling
- **Observability**: Comprehensive logging and metrics
- **Horizontal Scaling**: Multiple workers support
- **Distributed Architecture**: Separation of concerns

## Testing

Run the test suite:
```bash
python -m pytest tests/
```

## Docker (Phase 6)

```bash
docker-compose up
```

This will start:
- API server (port 8000)
- Redis (port 6379)
- Worker process
- Database (PostgreSQL)

## Why This Matters

This system demonstrates the exact patterns used in production at companies like:
- **Stripe**: Payment processing
- **Netflix**: Video encoding
- **OpenAI**: AI model inference
- **Airbnb**: Data pipelines

You'll learn:
- Async programming patterns
- Queue mechanics
- Fault tolerance
- System observability
- Distributed architecture

## Performance Metrics

- API response time: <50ms (task submission)
- Task processing: Non-blocking
- Concurrent tasks: Limited by worker count
- Memory usage: Efficient with async patterns
