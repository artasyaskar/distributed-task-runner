#!/usr/bin/env python3
"""
Pool worker that runs as part of the worker pool system
"""
import asyncio
import signal
import sys
import os
from app.services.worker_pool import worker_pool
from app.core.logging import logger


class PoolWorkerProcess:
    """Worker process that can be managed by the worker pool"""
    
    def __init__(self):
        self.worker_id = os.environ.get("WORKER_ID", f"pool-worker-{os.getpid()}")
        self.running = False
    
    async def start(self):
        """Start the pool worker"""
        logger.info(f"Starting pool worker process {self.worker_id}")
        self.running = True
        
        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        try:
            # Initialize worker pool (this will connect to existing pool)
            await worker_pool.initialize()
            
            # The worker pool will manage this worker
            # This process will be managed by the pool's worker instances
            
            logger.info(f"Pool worker {self.worker_id} ready")
            
            # Keep process alive
            while self.running:
                await asyncio.sleep(1)
                
        except Exception as e:
            logger.error(f"Pool worker {self.worker_id} error: {str(e)}")
        finally:
            logger.info(f"Pool worker {self.worker_id} stopped")
    
    def stop(self):
        """Stop the pool worker"""
        logger.info(f"Stopping pool worker {self.worker_id}")
        self.running = False
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        logger.info(f"Pool worker {self.worker_id} received signal {signum}")
        self.stop()
        sys.exit(0)


async def main():
    """Main entry point for pool worker process"""
    worker = PoolWorkerProcess()
    
    try:
        await worker.start()
    except KeyboardInterrupt:
        logger.info("Pool worker interrupted by user")
    except Exception as e:
        logger.error(f"Pool worker crashed: {str(e)}")
    finally:
        worker.stop()


if __name__ == "__main__":
    asyncio.run(main())
