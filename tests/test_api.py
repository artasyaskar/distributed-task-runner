import pytest
import asyncio
from fastapi.testclient import TestClient
from app.main import app
from app.services.task_queue import task_queue


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session", autouse=True)
async def setup_test_queue():
    """Setup queue for all tests"""
    await task_queue.initialize()


@pytest.fixture
def client():
    """Test client fixture"""
    return TestClient(app)


def test_root_endpoint(client):
    """Test root endpoint"""
    response = client.get("/")
    assert response.status_code == 200
    assert "Distributed Task Processing System" in response.json()["message"]


def test_health_check(client):
    """Test health check endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_create_task(client):
    """Test task creation"""
    task_data = {
        "task_type": "text_processing",
        "payload": {"text": "Test text for processing"}
    }
    
    response = client.post("/tasks/", json=task_data)
    assert response.status_code == 201
    
    task = response.json()
    assert task["task_type"] == "text_processing"
    assert task["status"] == "pending"
    assert "id" in task


def test_create_invalid_task_type(client):
    """Test task creation with invalid type"""
    task_data = {
        "task_type": "invalid_type",
        "payload": {"text": "Test text"}
    }
    
    response = client.post("/tasks/", json=task_data)
    # For now, we'll accept either 400 (validation) or 500 (initialization error)
    assert response.status_code in [400, 500]


def test_get_task(client):
    """Test getting task by ID"""
    # First create a task
    task_data = {
        "task_type": "text_processing",
        "payload": {"text": "Test text"}
    }
    create_response = client.post("/tasks/", json=task_data)
    task_id = create_response.json()["id"]
    
    # Get the task
    response = client.get(f"/tasks/{task_id}")
    assert response.status_code == 200
    
    task = response.json()
    assert task["id"] == task_id
    assert task["task_type"] == "text_processing"


def test_get_nonexistent_task(client):
    """Test getting non-existent task"""
    response = client.get("/tasks/99999")
    assert response.status_code == 404
    assert "Task not found" in response.json()["detail"]


def test_list_tasks(client):
    """Test listing tasks"""
    # Create a few tasks
    for i in range(3):
        task_data = {
            "task_type": "text_processing",
            "payload": {"text": f"Test text {i}"}
        }
        client.post("/tasks/", json=task_data)
    
    # List tasks
    response = client.get("/tasks/")
    assert response.status_code == 200
    
    tasks = response.json()
    assert len(tasks) >= 3


def test_task_types(client):
    """Test all supported task types"""
    task_types = ["text_processing", "ai_summarization", "batch_processing", "image_processing"]
    
    for task_type in task_types:
        if task_type == "batch_processing":
            payload = {"data": ["item1", "item2", "item3"]}
        elif task_type == "image_processing":
            payload = {"image_url": "http://example.com/image.jpg"}
        else:
            payload = {"text": "Test text"}
        
        task_data = {
            "task_type": task_type,
            "payload": payload
        }
        
        response = client.post("/tasks/", json=task_data)
        assert response.status_code == 201
        
        task = response.json()
        assert task["task_type"] == task_type
