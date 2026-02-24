import asyncio
import signal
import sys
import json
from typing import Dict, Any
from app.core.logging import logger
from app.services.redis_queue import redis_queue
from app.services.task_queue import task_queue
from app.services.enhanced_task_executor import enhanced_task_executor
from app.services.retry_handler import retry_handler, dead_letter_queue


class EnhancedWorker:
    """Enhanced worker with advanced retry logic and monitoring"""
    
    def __init__(self, worker_id: str = None):
        self.worker_id = worker_id or f"enhanced-worker-{id(self)}"
        self.running = False
        self.tasks_processed = 0
        self.start_time = None
    
    async def start(self):
        """Start the enhanced worker"""
        logger.info(f"Starting enhanced worker {self.worker_id}")
        self.running = True
        self.start_time = time.time()
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        # Initialize connections
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
                logger.error(f"Enhanced worker {self.worker_id} error: {str(e)}")
                await asyncio.sleep(1)  # Brief pause on error
    
    async def _process_task(self, task_data: Dict[str, Any]):
        """Process a single task with enhanced logic"""
        task_id = task_data['id']
        task_type = task_data['task_type']
        payload = task_data['payload']
        
        logger.info(f"Enhanced worker {self.worker_id} processing task {task_id} ({task_type})")
        
        try:
            # Get task from database
            task = await task_queue.get_task(task_id)
            if not task:
                logger.error(f"Task {task_id} not found in database")
                return
            
            # Execute task with enhanced retry logic
            result = await enhanced_task_executor.execute_task(task)
            
            # Mark as completed in Redis
            await redis_queue.complete_task(task_id)
            
            self.tasks_processed += 1
            logger.info(f"Enhanced worker {self.worker_id} completed task {task_id}")
            
        except Exception as e:
            logger.error(f"Enhanced worker {self.worker_id} failed task {task_id}: {str(e)}")
            # Enhanced executor handles retry logic and dead letter queue
    
    def stop(self):
        """Stop the worker"""
        logger.info(f"Stopping enhanced worker {self.worker_id}")
        self.running = False
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        logger.info(f"Enhanced worker {self.worker_id} received signal {signum}")
        self.stop()
        sys.exit(0)
    
    def get_worker_stats(self) -> Dict[str, Any]:
        """Get worker statistics"""
        runtime = time.time() - self.start_time if self.start_time else 0
        return {
            "worker_id": self.worker_id,
            "tasks_processed": self.tasks_processed,
            "runtime_seconds": runtime,
            "tasks_per_second": self.tasks_processed / runtime if runtime > 0 else 0,
            "is_running": self.running
        }


async def main():
    """Main entry point for enhanced worker process"""
    worker = EnhancedWorker()
    
    try:
        await worker.start()
    except KeyboardInterrupt:
        logger.info("Enhanced worker interrupted by user")
    except Exception as e:
        logger.error(f"Enhanced worker crashed: {str(e)}")
    finally:
        # Print final statistics
        stats = worker.get_worker_stats()
        logger.info(f"Worker final stats: {json.dumps(stats, indent=2)}")
        await redis_queue.close()


if __name__ == "__main__":
    import time
    asyncio.run(main())
