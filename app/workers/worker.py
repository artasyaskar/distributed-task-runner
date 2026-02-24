import asyncio
import signal
import sys
from app.core.logging import logger
from app.services.task_queue import task_queue
from app.services.task_executor import task_executor


class Worker:
    """Background worker that processes tasks from the queue"""
    
    def __init__(self):
        self.running = False
        self.worker_id = f"worker-{id(self)}"
    
    async def start(self):
        """Start the worker"""
        logger.info(f"Starting worker {self.worker_id}")
        self.running = True
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        # Main worker loop
        while self.running:
            try:
                # Get next task from queue
                task = await task_queue.get_next_task()
                
                if task:
                    logger.info(f"Worker {self.worker_id} processing task {task.id}")
                    await task_executor.execute_task(task)
                else:
                    # No task available, brief pause
                    await asyncio.sleep(0.1)
                    
            except Exception as e:
                logger.error(f"Worker {self.worker_id} error: {str(e)}")
                await asyncio.sleep(1)  # Brief pause on error
    
    def stop(self):
        """Stop the worker"""
        logger.info(f"Stopping worker {self.worker_id}")
        self.running = False
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        logger.info(f"Worker {self.worker_id} received signal {signum}")
        self.stop()
        sys.exit(0)


async def main():
    """Main entry point for worker process"""
    # Initialize the task queue
    await task_queue.initialize()
    
    # Create and start worker
    worker = Worker()
    await worker.start()


if __name__ == "__main__":
    asyncio.run(main())
