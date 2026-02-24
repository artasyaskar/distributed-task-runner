import json
import asyncio
import aioredis
from typing import Dict, Any, Optional
from app.core.config import settings
from app.core.logging import logger
from app.models.task_model import Task, TaskStatus


class RedisTaskQueue:
    """Redis-based task queue for true distributed processing"""
    
    def __init__(self):
        self.redis_client = None
        self.task_queue_key = "task_queue"
        self.task_data_key_prefix = "task_data:"
        self.processing_key_prefix = "processing:"
    
    async def initialize(self):
        """Initialize Redis connection"""
        try:
            self.redis_client = aioredis.from_url(settings.redis_url)
            # Test connection
            await self.redis_client.ping()
            logger.info("Redis connection established")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {str(e)}")
            raise
    
    async def create_task(self, task_type: str, payload: Dict[str, Any]) -> Task:
        """Create task and add to Redis queue"""
        # First save task to database
        from app.services.task_queue import task_queue
        task = await task_queue.create_task(task_type, payload)
        
        # Add task ID to Redis queue
        task_data = {
            "id": task.id,
            "task_type": task_type,
            "payload": payload,
            "created_at": task.created_at.isoformat() if task.created_at else None
        }
        
        await self.redis_client.lpush(
            self.task_queue_key,
            json.dumps(task_data)
        )
        
        logger.info(f"Task {task.id} added to Redis queue")
        return task
    
    async def get_next_task(self) -> Optional[Dict[str, Any]]:
        """Get next task from Redis queue (blocking)"""
        try:
            # Use BRPOP for blocking operation with timeout
            result = await self.redis_client.brpop(
                self.task_queue_key,
                timeout=1  # 1 second timeout
            )
            
            if result:
                _, task_json = result
                task_data = json.loads(task_json)
                
                # Mark as processing
                await self.redis_client.set(
                    f"{self.processing_key_prefix}{task_data['id']}",
                    "processing",
                    ex=300  # 5 minute TTL
                )
                
                logger.info(f"Retrieved task {task_data['id']} from Redis queue")
                return task_data
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting task from Redis: {str(e)}")
            return None
    
    async def complete_task(self, task_id: int):
        """Mark task as completed in Redis"""
        await self.redis_client.delete(f"{self.processing_key_prefix}{task_id}")
        logger.info(f"Task {task_id} marked as completed in Redis")
    
    async def get_queue_size(self) -> int:
        """Get current queue size"""
        try:
            return await self.redis_client.llen(self.task_queue_key)
        except Exception as e:
            logger.error(f"Error getting queue size: {str(e)}")
            return 0
    
    async def get_processing_count(self) -> int:
        """Get count of currently processing tasks"""
        try:
            pattern = f"{self.processing_key_prefix}*"
            keys = await self.redis_client.keys(pattern)
            return len(keys)
        except Exception as e:
            logger.error(f"Error getting processing count: {str(e)}")
            return 0
    
    async def cleanup_stale_tasks(self):
        """Clean up tasks that have been processing too long"""
        try:
            pattern = f"{self.processing_key_prefix}*"
            keys = await self.redis_client.keys(pattern)
            
            for key in keys:
                ttl = await self.redis_client.ttl(key)
                if ttl == -1:  # No TTL set, stale task
                    await self.redis_client.delete(key)
                    logger.warning(f"Cleaned up stale processing task: {key}")
                    
        except Exception as e:
            logger.error(f"Error cleaning up stale tasks: {str(e)}")
    
    async def close(self):
        """Close Redis connection"""
        if self.redis_client:
            await self.redis_client.close()
            logger.info("Redis connection closed")


# Global Redis queue instance
redis_queue = RedisTaskQueue()
