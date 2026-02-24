import asyncio
import signal
import sys
import json
from typing import Dict, Any
from app.core.logging import logger
from app.services.redis_queue import redis_queue
from app.services.task_queue import task_queue
from app.services.task_executor import task_executor


class RedisWorker:
    """Redis-based worker for distributed task processing"""
    
    def __init__(self, worker_id: str = None):
        self.worker_id = worker_id or f"redis-worker-{id(self)}"
        self.running = False
    
    async def start(self):
        """Start the Redis worker"""
        logger.info(f"Starting Redis worker {self.worker_id}")
        self.running = True
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        # Initialize Redis connection
        await redis_queue.initialize()
        await task_queue.initialize()
        
        # Main worker loop
        while self.running:
            try:
                # Get next task from Redis queue
                task_data = await redis_queue.get_next_task()
                
                if task_data:
                    await self._process_task(task_data)
                else:
                    # No task available, brief pause
                    await asyncio.sleep(0.1)
                    
            except Exception as e:
                logger.error(f"Redis worker {self.worker_id} error: {str(e)}")
                await asyncio.sleep(1)  # Brief pause on error
    
    async def _process_task(self, task_data: Dict[str, Any]):
        """Process a single task"""
        task_id = task_data['id']
        task_type = task_data['task_type']
        payload = task_data['payload']
        
        logger.info(f"Redis worker {self.worker_id} processing task {task_id} ({task_type})")
        
        try:
            # Get task from database
            task = await task_queue.get_task(task_id)
            if not task:
                logger.error(f"Task {task_id} not found in database")
                return
            
            # Execute task
            result = await task_executor.execute_task(task)
            
            # Mark as completed in Redis
            await redis_queue.complete_task(task_id)
            
            logger.info(f"Redis worker {self.worker_id} completed task {task_id}")
            
        except Exception as e:
            logger.error(f"Redis worker {self.worker_id} failed task {task_id}: {str(e)}")
            
            # Mark task as failed in database
            try:
                await task_queue.update_task_status(
                    task_id, 
                    TaskStatus.FAILED, 
                    error_message=str(e)
                )
                
                # Check if we should retry
                if task.retry_count < task.max_retries:
                    logger.info(f"Retrying task {task_id} (attempt {task.retry_count + 1})")
                    await task_queue.retry_task(task_id)
                    
            except Exception as retry_error:
                logger.error(f"Failed to handle retry for task {task_id}: {str(retry_error)}")
    
    def stop(self):
        """Stop the worker"""
        logger.info(f"Stopping Redis worker {self.worker_id}")
        self.running = False
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        logger.info(f"Redis worker {self.worker_id} received signal {signum}")
        self.stop()
        sys.exit(0)


async def main():
    """Main entry point for Redis worker process"""
    worker = RedisWorker()
    
    try:
        await worker.start()
    except KeyboardInterrupt:
        logger.info("Redis worker interrupted by user")
    except Exception as e:
        logger.error(f"Redis worker crashed: {str(e)}")
    finally:
        await redis_queue.close()


if __name__ == "__main__":
    asyncio.run(main())
