# Distributed Task Processing System - Usage Guide

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Virtual environment (recommended)

### Installation

1. **Clone and setup environment:**
```bash
git clone <repository>
cd distributed-task-runner
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

2. **Copy environment file:**
```bash
cp .env.example .env
```

### Running the System

#### Option 1: API + Worker (Separate Processes)
```bash
# Terminal 1: Start API server
python run_api.py

# Terminal 2: Start worker
python run_worker.py
```

#### Option 2: Integrated Demo (Single Process)
```bash
# Run integrated demo showing full system
python integrated_demo.py
```

#### Option 3: API Testing Only
```bash
# Test API functionality (worker processes tasks in same process)
python demo.py
```

## 📋 API Endpoints

### Create Task
```bash
POST /tasks/
Content-Type: application/json

{
  "task_type": "text_processing",
  "payload": {"text": "Your text here"}
}
```

### Get Task Status
```bash
GET /tasks/{task_id}
```

### List All Tasks
```bash
GET /tasks/?limit=50&offset=0
```

### Retry Failed Task
```bash
POST /tasks/{task_id}/retry
```

### Health Check
```bash
GET /health
```

## 🎯 Supported Task Types

### 1. Text Processing
- **Purpose**: Simple text manipulation
- **Processing Time**: ~3 seconds
- **Payload**: `{"text": "string"}`
- **Result**: Word count, character count, processed text

### 2. AI Summarization
- **Purpose**: Mock AI document summarization
- **Processing Time**: ~5 seconds
- **Payload**: `{"document": "long text"}`
- **Result**: Summary, length metrics

### 3. Batch Processing
- **Purpose**: Process data arrays
- **Processing Time**: Variable (0.1s per item, max 10s)
- **Payload**: `{"data": ["item1", "item2", ...]}`
- **Result**: Processed data sample, count

### 4. Image Processing
- **Purpose**: Mock image manipulation
- **Processing Time**: ~4 seconds
- **Payload**: `{"image_url": "url"}`
- **Result**: Resized/compressed URLs, analysis

## 🔄 Task States

1. **PENDING**: Task created, waiting for worker
2. **RUNNING**: Worker is processing the task
3. **COMPLETED**: Task finished successfully
4. **FAILED**: Task failed (may retry)
5. **RETRYING**: Task being retried after failure

## 📊 System Architecture

```
Client → FastAPI → Task Queue → Worker → Database
         ↑              ↓
         └── Status Polling ←──┘
```

### Components

- **FastAPI Server**: Handles HTTP requests, returns immediately
- **Task Queue**: Manages task distribution (in-memory for Phase 1)
- **Worker**: Processes tasks asynchronously
- **Database**: Persists task state and results

## 🧪 Testing

### Run Unit Tests
```bash
python -m pytest tests/
```

### Run Integration Tests
```bash
python test_system.py
```

### Run Full Demo
```bash
python integrated_demo.py
```

## 📈 Performance Characteristics

- **API Response Time**: <50ms (task submission)
- **Task Processing**: Non-blocking
- **Concurrent Tasks**: Limited by worker count
- **Memory Usage**: Efficient with async patterns

## 🔧 Configuration

Edit `.env` file:
```env
DATABASE_URL=sqlite:///./tasks.db
REDIS_URL=redis://localhost:6379
SECRET_KEY=your-secret-key-here
DEBUG=True
```

## 🚨 Common Issues

### Worker Not Processing Tasks
- API and worker run in separate processes
- Tasks created via API won't be processed by separate worker in Phase 1
- Use `integrated_demo.py` for full system demonstration

### Pydantic Import Error
- Install: `pip install pydantic-settings`
- Fixed in requirements.txt

### Database Connection Issues
- Check DATABASE_URL in .env
- SQLite works out of the box
- PostgreSQL requires connection string

## 🎯 Learning Objectives

After completing this system, you'll understand:

- **Async Programming**: Non-blocking task execution
- **Queue Mechanics**: Task distribution patterns
- **API Design**: Fast response times with background processing
- **State Management**: Task lifecycle tracking
- **Error Handling**: Retry logic and fault tolerance
- **System Architecture**: Separation of concerns

## 🏗️ Development Phases

### ✅ Phase 1: Basic Async Job System
- Task submission and background execution
- Status polling pattern
- SQLite persistence

### 🔄 Phase 2: Redis Message Queue (Next)
- True process decoupling
- Redis queue integration
- Multiple worker support

### 🔄 Phase 3: Retry Logic & Failure Handling (Next)
- Configurable retry attempts
- Exponential backoff
- Permanent failure handling

### 🔄 Phase 4: Logging & Monitoring (Next)
- Task execution metrics
- Performance tracking
- Failure rate analysis

### 🔄 Phase 5: Concurrency & Scaling (Next)
- Multiple worker processes
- Task prioritization
- Load balancing

### 🔄 Phase 6: Dockerized Setup (Next)
- Multi-container deployment
- Production configuration
- Horizontal scaling

## 💡 Real-World Applications

This system demonstrates patterns used by:
- **Stripe**: Payment processing
- **Netflix**: Video encoding
- **OpenAI**: Model inference
- **Airbnb**: Data pipelines
- **Twitter**: Timeline generation

## 🎓 Next Steps

1. **Study the code**: Understand each component
2. **Run the demos**: See the system in action
3. **Extend functionality**: Add new task types
4. **Implement Phase 2**: Add Redis queue
5. **Deploy to production**: Docker setup

This system gives you hands-on experience with the exact patterns used in production distributed systems!
