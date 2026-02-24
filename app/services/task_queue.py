import asyncio
import json
import uuid
from typing import Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import func
from app.core.config import settings
from app.core.logging import logger
from app.models.task_model import Task, TaskStatus


class TaskQueue:
    """Simple in-memory task queue for Phase 1"""
    
    def __init__(self):
        self._queue = asyncio.Queue()
        self._tasks: Dict[str, Task] = {}
        self._engine = create_async_engine(
            settings.database_url.replace("sqlite://", "sqlite+aiosqlite://"),
            echo=settings.debug
        )
        self._session_factory = sessionmaker(
            self._engine, class_=AsyncSession, expire_on_commit=False
        )
    
    async def initialize(self):
        """Initialize database tables"""
        async with self._engine.begin() as conn:
            await conn.run_sync(Task.metadata.create_all)
    
    async def create_task(self, task_type: str, payload: Dict[str, Any]) -> Task:
        """Create a new task and add it to the queue"""
        async with self._session_factory() as session:
            task = Task(
                task_type=task_type,
                payload=json.dumps(payload),
                status=TaskStatus.PENDING,
                max_retries=settings.max_retries
            )
            
            session.add(task)
            await session.commit()
            await session.refresh(task)
            
            # Add to queue
            await self._queue.put(task.id)
            self._tasks[str(task.id)] = task
            
            logger.info(f"Created task {task.id} of type {task_type}")
            return task
    
    async def get_task(self, task_id: int) -> Optional[Task]:
        """Get task by ID"""
        async with self._session_factory() as session:
            result = await session.get(Task, task_id)
            return result
    
    async def update_task_status(self, task_id: int, status: TaskStatus, 
                                result: Optional[str] = None, 
                                error_message: Optional[str] = None) -> Task:
        """Update task status and optional result/error"""
        async with self._session_factory() as session:
            task = await session.get(Task, task_id)
            if not task:
                raise ValueError(f"Task {task_id} not found")
            
            task.status = status
            if result is not None:
                task.result = result
            if error_message is not None:
                task.error_message = error_message
            
            if status == TaskStatus.RUNNING and task.started_at is None:
                from datetime import datetime
                task.started_at = datetime.utcnow()
            elif status in [TaskStatus.COMPLETED, TaskStatus.FAILED]:
                from datetime import datetime
                task.completed_at = datetime.utcnow()
            
            await session.commit()
            await session.refresh(task)
            
            # Update in-memory cache
            self._tasks[str(task_id)] = task
            
            logger.info(f"Updated task {task_id} status to {status.value}")
            return task
    
    async def get_next_task(self) -> Optional[Task]:
        """Get next task from queue (blocking)"""
        try:
            task_id = await asyncio.wait_for(self._queue.get(), timeout=1.0)
            return await self.get_task(task_id)
        except asyncio.TimeoutError:
            return None
    
    async def retry_task(self, task_id: int) -> Task:
        """Retry a failed task"""
        async with self._session_factory() as session:
            task = await session.get(Task, task_id)
            if not task:
                raise ValueError(f"Task {task_id} not found")
            
            if task.retry_count >= task.max_retries:
                # Mark as permanently failed
                task.status = TaskStatus.FAILED
                task.error_message = f"Max retries ({task.max_retries}) exceeded"
            else:
                # Increment retry count and requeue
                task.retry_count += 1
                task.status = TaskStatus.RETRYING
                task.error_message = None
                await self._queue.put(task.id)
            
            await session.commit()
            await session.refresh(task)
            
            logger.info(f"Retrying task {task_id} (attempt {task.retry_count})")
            return task


# Global task queue instance
task_queue = TaskQueue()
