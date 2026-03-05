#!/usr/bin/env python3
"""
Run the worker pool manager with auto-scaling
"""
import asyncio
import signal
import sys
from app.services.worker_pool import worker_pool
from app.services.auto_scaler import auto_scaler
from app.core.logging import logger


class PoolManager:
    """Manages the worker pool and auto-scaler"""
    
    def __init__(self):
        self.running = False
    
    async def start(self):
        """Start the pool manager"""
        logger.info("Starting worker pool manager")
        self.running = True
        
        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        try:
            # Initialize worker pool
            await worker_pool.initialize()
            logger.info("Worker pool initialized")
            
            # Start auto-scaler
            await auto_scaler.start()
            logger.info("Auto-scaler started")
            
            # Keep manager running
            while self.running:
                await asyncio.sleep(10)
                
                # Log status periodically
                status = worker_pool.get_pool_status()
                logger.info(f"Pool status: {status['total_workers']} workers, "
                           f"auto-scaler: {'enabled' if auto_scaler.enabled else 'disabled'}")
                
        except Exception as e:
            logger.error(f"Pool manager error: {str(e)}")
        finally:
            await self.shutdown()
    
    async def shutdown(self):
        """Shutdown the pool manager"""
        logger.info("Shutting down pool manager")
        
        # Stop auto-scaler
        try:
            await auto_scaler.stop()
        except:
            pass
        
        # Stop worker pool
        try:
            await worker_pool.stop()
        except:
            pass
        
        logger.info("Pool manager shutdown complete")
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        logger.info(f"Pool manager received signal {signum}")
        self.running = False
        sys.exit(0)


async def main():
    """Main entry point for pool manager"""
    manager = PoolManager()
    
    try:
        await manager.start()
    except KeyboardInterrupt:
        logger.info("Pool manager interrupted by user")
    except Exception as e:
        logger.error(f"Pool manager crashed: {str(e)}")
    finally:
        await manager.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
