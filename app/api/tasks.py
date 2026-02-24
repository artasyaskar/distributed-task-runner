from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional
from app.services.task_queue import task_queue
from app.services.redis_queue import redis_queue
from app.models.task_model import Task


router = APIRouter(prefix="/tasks", tags=["tasks"])


class TaskRequest(BaseModel):
    task_type: str = Field(..., description="Type of task to execute")
    payload: Dict[str, Any] = Field(..., description="Task payload data")


class TaskResponse(BaseModel):
    id: int
    task_type: str
    status: str
    created_at: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    result: Optional[str] = None
    error_message: Optional[str] = None
    retry_count: int
    max_retries: int


@router.post("/", response_model=TaskResponse, status_code=201)
async def create_task(task_request: TaskRequest):
    """Create a new task"""
    try:
        # Validate task type
        valid_task_types = ["text_processing", "ai_summarization", "batch_processing", "image_processing"]
        if task_request.task_type not in valid_task_types:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid task_type. Must be one of: {valid_task_types}"
            )
        
        # Create task and add to Redis queue
        task = await redis_queue.create_task(task_request.task_type, task_request.payload)
        
        return TaskResponse(**task.to_dict())
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(task_id: int):
    """Get task by ID"""
    try:
        task = await task_queue.get_task(task_id)
        
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        
        return TaskResponse(**task.to_dict())
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/", response_model=list[TaskResponse])
async def list_tasks(limit: int = 50, offset: int = 0):
    """List all tasks with pagination"""
    try:
        # This is a simplified implementation
        # In a real system, you'd query the database with pagination
        all_tasks = list(task_queue._tasks.values())
        
        # Simple pagination
        paginated_tasks = all_tasks[offset:offset + limit]
        
        return [TaskResponse(**task.to_dict()) for task in paginated_tasks]
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/queue/stats")
async def get_queue_stats():
    """Get queue statistics"""
    try:
        queue_size = await redis_queue.get_queue_size()
        processing_count = await redis_queue.get_processing_count()
        
        return {
            "queue_size": queue_size,
            "processing": processing_count,
            "total_pending": queue_size + processing_count
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/queue/cleanup")
async def cleanup_queue():
    """Clean up stale processing tasks"""
    try:
        await redis_queue.cleanup_stale_tasks()
        return {"message": "Queue cleanup completed"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
