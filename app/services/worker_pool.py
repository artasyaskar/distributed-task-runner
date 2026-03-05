import asyncio
import time
import signal
import sys
from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass, field
from enum import Enum
from app.core.logging import logger
from app.workers.enhanced_worker import EnhancedWorker
from app.services.enhanced_task_executor import enhanced_task_executor
from app.services.redis_queue import redis_queue
from app.services.task_queue import task_queue


class WorkerStatus(Enum):
    """Worker status states"""
    STARTING = "starting"
    IDLE = "idle"
    BUSY = "busy"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"


class TaskPriority(Enum):
    """Task priority levels"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class WorkerInstance:
    """Individual worker instance tracking"""
    worker_id: str
    worker: EnhancedWorker
    status: WorkerStatus = WorkerStatus.STARTING
    pid: Optional[int] = None
    tasks_processed: int = 0
    start_time: float = field(default_factory=time.time)
    last_heartbeat: float = field(default_factory=time.time)
    error_count: int = 0
    current_task_id: Optional[int] = None


class WorkerPool:
    """Advanced worker pool with auto-scaling and load balancing"""
    
    def __init__(self, min_workers: int = 2, max_workers: int = 10):
        self.min_workers = min_workers
        self.max_workers = max_workers
        self.workers: Dict[str, WorkerInstance] = {}
        self.running = False
        self.scaling_enabled = True
        
        # Auto-scaling configuration
        self.scale_up_threshold = 5      # Queue size to trigger scale up
        self.scale_down_threshold = 2    # Queue size to trigger scale down
        self.scale_up_cooldown = 60      # Seconds between scale up events
        self.scale_down_cooldown = 120    # Seconds between scale down events
        self.last_scale_time = 0
        
        # Load balancing
        self.round_robin_index = 0
        self.load_balancing_strategy = "round_robin"  # round_robin, least_loaded, random
        
        # Worker health monitoring
        self.heartbeat_interval = 30      # Seconds
        self.worker_timeout = 120         # Seconds without heartbeat before restart
        
        # Task prioritization
        self.priority_queues = {
            TaskPriority.CRITICAL: asyncio.Queue(),
            TaskPriority.HIGH: asyncio.Queue(),
            TaskPriority.NORMAL: asyncio.Queue(),
            TaskPriority.LOW: asyncio.Queue()
        }
        
        # Performance tracking
        self.pool_metrics = {
            "total_tasks_processed": 0,
            "avg_processing_time": 0.0,
            "workers_created": 0,
            "workers_destroyed": 0,
            "scale_up_events": 0,
            "scale_down_events": 0,
            "last_scale_time": None
        }
    
    async def initialize(self):
        """Initialize the worker pool"""
        logger.info(f"Initializing worker pool with {self.min_workers}-{self.max_workers} workers")
        
        # Initialize task queue and Redis
        await task_queue.initialize()
        try:
            await redis_queue.initialize()
        except Exception as e:
            logger.warning(f"Redis not available: {str(e)}")
        
        # Start with minimum workers
        await self._scale_to_workers(self.min_workers)
        
        # Start background tasks
        self.running = True
        asyncio.create_task(self._auto_scaling_loop())
        asyncio.create_task(self._health_monitoring_loop())
        asyncio.create_task(self._priority_dispatcher_loop())
        
        logger.info("Worker pool initialized successfully")
    
    async def start(self):
        """Start the worker pool"""
        if not self.running:
            await self.initialize()
        
        logger.info("Worker pool started")
    
    async def stop(self):
        """Stop the worker pool"""
        logger.info("Stopping worker pool")
        self.running = False
        self.scaling_enabled = False
        
        # Stop all workers gracefully
        for worker_id, worker_instance in self.workers.items():
            await self._stop_worker(worker_id)
        
        logger.info("Worker pool stopped")
    
    async def _create_worker(self) -> str:
        """Create a new worker instance"""
        worker_id = f"worker-{int(time.time())}-{len(self.workers)}"
        
        try:
            # Create enhanced worker
            worker = EnhancedWorker(worker_id)
            
            # Track worker instance
            worker_instance = WorkerInstance(
                worker_id=worker_id,
                worker=worker,
                status=WorkerStatus.STARTING
            )
            
            self.workers[worker_id] = worker_instance
            
            # Start worker in background
            asyncio.create_task(self._run_worker(worker_instance))
            
            # Update metrics
            self.pool_metrics["workers_created"] += 1
            
            logger.info(f"Created worker {worker_id}")
            return worker_id
            
        except Exception as e:
            logger.error(f"Failed to create worker {worker_id}: {str(e)}")
            raise
    
    async def _run_worker(self, worker_instance: WorkerInstance):
        """Run a worker instance with monitoring"""
        try:
            worker_instance.status = WorkerStatus.IDLE
            worker_instance.last_heartbeat = time.time()
            
            # Start the worker
            await worker_instance.worker.start()
            
        except Exception as e:
            worker_instance.status = WorkerStatus.ERROR
            worker_instance.error_count += 1
            logger.error(f"Worker {worker_instance.worker_id} crashed: {str(e)}")
            
            # Restart worker if error count is low
            if worker_instance.error_count < 3:
                logger.info(f"Restarting worker {worker_instance.worker_id}")
                await asyncio.sleep(5)  # Brief delay before restart
                asyncio.create_task(self._run_worker(worker_instance))
            else:
                logger.error(f"Worker {worker_instance.worker_id} exceeded error threshold, removing")
                await self._remove_worker(worker_instance.worker_id)
    
    async def _stop_worker(self, worker_id: str):
        """Stop a specific worker"""
        if worker_id not in self.workers:
            return
        
        worker_instance = self.workers[worker_id]
        worker_instance.status = WorkerStatus.STOPPING
        
        try:
            worker_instance.worker.stop()
            worker_instance.status = WorkerStatus.STOPPED
            logger.info(f"Stopped worker {worker_id}")
        except Exception as e:
            logger.error(f"Error stopping worker {worker_id}: {str(e)}")
    
    async def _remove_worker(self, worker_id: str):
        """Remove a worker from the pool"""
        if worker_id in self.workers:
            await self._stop_worker(worker_id)
            del self.workers[worker_id]
            self.pool_metrics["workers_destroyed"] += 1
            logger.info(f"Removed worker {worker_id}")
    
    async def _scale_to_workers(self, target_count: int):
        """Scale worker pool to target count"""
        current_count = len(self.workers)
        
        if target_count > current_count:
            # Scale up
            workers_to_add = min(target_count - current_count, self.max_workers - current_count)
            for _ in range(workers_to_add):
                await self._create_worker()
            
        elif target_count < current_count:
            # Scale down (remove idle workers)
            workers_to_remove = current_count - target_count
            idle_workers = [
                w_id for w_id, w in self.workers.items() 
                if w.status == WorkerStatus.IDLE
            ]
            
            for worker_id in idle_workers[:workers_to_remove]:
                await self._remove_worker(worker_id)
    
    async def _auto_scaling_loop(self):
        """Auto-scaling based on queue size and load"""
        while self.running:
            try:
                if not self.scaling_enabled:
                    await asyncio.sleep(10)
                    continue
                
                # Get current queue size
                queue_size = 0
                try:
                    queue_size = await redis_queue.get_queue_size()
                except:
                    pass  # Redis might not be available
                
                current_workers = len(self.workers)
                
                # Check scale up conditions
                if (queue_size > self.scale_up_threshold and 
                    current_workers < self.max_workers and
                    time.time() - self.last_scale_time > self.scale_up_cooldown):
                    
                    # Calculate new worker count
                    new_workers = min(current_workers + 2, self.max_workers)
                    await self._scale_to_workers(new_workers)
                    
                    self.last_scale_time = time.time()
                    self.pool_metrics["scale_up_events"] += 1
                    self.pool_metrics["last_scale_time"] = time.time()
                    
                    logger.info(f"Scaled up to {new_workers} workers (queue size: {queue_size})")
                
                # Check scale down conditions
                elif (queue_size < self.scale_down_threshold and 
                      current_workers > self.min_workers and
                      time.time() - self.last_scale_time > self.scale_down_cooldown):
                    
                    # Calculate new worker count
                    new_workers = max(current_workers - 1, self.min_workers)
                    await self._scale_to_workers(new_workers)
                    
                    self.last_scale_time = time.time()
                    self.pool_metrics["scale_down_events"] += 1
                    self.pool_metrics["last_scale_time"] = time.time()
                    
                    logger.info(f"Scaled down to {new_workers} workers (queue size: {queue_size})")
                
                await asyncio.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                logger.error(f"Error in auto-scaling loop: {str(e)}")
                await asyncio.sleep(10)
    
    async def _health_monitoring_loop(self):
        """Monitor worker health and restart unhealthy workers"""
        while self.running:
            try:
                current_time = time.time()
                workers_to_restart = []
                
                for worker_id, worker_instance in self.workers.items():
                    # Check for timeout
                    if (current_time - worker_instance.last_heartbeat > self.worker_timeout and
                        worker_instance.status != WorkerStatus.STOPPED):
                        
                        logger.warning(f"Worker {worker_id} timeout, marking for restart")
                        workers_to_restart.append(worker_id)
                    
                    # Check for error state
                    elif worker_instance.status == WorkerStatus.ERROR:
                        if worker_instance.error_count >= 3:
                            logger.error(f"Worker {worker_id} has too many errors, removing")
                            await self._remove_worker(worker_id)
                        else:
                            workers_to_restart.append(worker_id)
                
                # Restart unhealthy workers
                for worker_id in workers_to_restart:
                    if worker_id in self.workers:
                        logger.info(f"Restarting unhealthy worker {worker_id}")
                        await self._remove_worker(worker_id)
                        await self._create_worker()
                
                await asyncio.sleep(self.heartbeat_interval)
                
            except Exception as e:
                logger.error(f"Error in health monitoring loop: {str(e)}")
                await asyncio.sleep(10)
    
    async def _collect_current_metrics(self) -> Dict[str, Any]:
        """Collect current system metrics"""
        metrics = {}
        
        # Queue metrics - fallback to in-memory if Redis not available
        try:
            metrics["queue_size"] = await redis_queue.get_queue_size()
            metrics["processing_count"] = await redis_queue.get_processing_count()
        except:
            # Fallback to in-memory queue
            metrics["queue_size"] = len(self._get_in_memory_queue())
            metrics["processing_count"] = len([w for w in self.workers.values() if w.status == WorkerStatus.BUSY])
        
        # System metrics
        try:
            system_metrics = metrics_collector.get_system_metrics_summary(5)  # Last 5 minutes
            if system_metrics:
                metrics["avg_cpu"] = system_metrics.get("avg_cpu_usage", 0)
                metrics["avg_memory"] = system_metrics.get("avg_memory_usage", 0)
                metrics["max_cpu"] = system_metrics.get("max_cpu_usage", 0)
                metrics["max_memory"] = system_metrics.get("max_memory_usage", 0)
        except:
            metrics["avg_cpu"] = 0.3  # Mock values for demo
            metrics["avg_memory"] = 0.4
            metrics["max_cpu"] = 0.5
            metrics["max_memory"] = 0.6
        
        # Worker metrics
        pool_status = self.get_pool_status()
        metrics["current_workers"] = pool_status["total_workers"]
        metrics["idle_workers"] = pool_status["workers_by_status"].get("idle", 0)
        metrics["busy_workers"] = pool_status["workers_by_status"].get("busy", 0)
        
        # Task metrics
        task_stats = metrics_collector.get_task_type_stats()
        if task_stats:
            total_tasks = sum(stats.get("total", 0) for stats in task_stats.values())
            total_time = sum(stats.get("avg_execution_time", 0) * stats.get("total", 0) 
                           for stats in task_stats.values())
            metrics["total_tasks_processed"] = total_tasks
            metrics["avg_task_time"] = total_time / total_tasks if total_tasks > 0 else 0
        else:
            metrics["total_tasks_processed"] = 0
            metrics["avg_task_time"] = 0
        
        return metrics
    
    async def add_task_to_queue(self, task_data: Dict[str, Any]):
        """Add task to queue for testing"""
        in_memory_queue = self._get_in_memory_queue()
        in_memory_queue.append(task_data)
        logger.info(f"Added task to in-memory queue: {task_data.get('id', 'unknown')}")
    
    def _get_in_memory_queue(self) -> List:
        """Get in-memory queue for fallback"""
        # Simple in-memory queue for demo purposes
        if not hasattr(self, '_in_memory_queue'):
            self._in_memory_queue = []
        return self._in_memory_queue

    async def _priority_dispatcher_loop(self):
        """Dispatch tasks based on priority"""
        while self.running:
            try:
                # Get next task by priority
                task_data = await self._get_next_priority_task()
                
                if task_data:
                    # Assign to best worker
                    worker_id = await self._select_worker()
                    if worker_id:
                        worker_instance = self.workers[worker_id]
                        worker_instance.current_task_id = task_data.get('id')
                        worker_instance.status = WorkerStatus.BUSY
                        
                        # Process task
                        await self._process_task_with_worker(worker_instance, task_data)
                        
                        # Update worker status
                        worker_instance.status = WorkerStatus.IDLE
                        worker_instance.current_task_id = None
                        worker_instance.tasks_processed += 1
                        worker_instance.last_heartbeat = time.time()
                        
                        self.pool_metrics["total_tasks_processed"] += 1
                
                await asyncio.sleep(0.1)  # Brief pause
                
            except Exception as e:
                logger.error(f"Error in priority dispatcher loop: {str(e)}")
                await asyncio.sleep(1)
    
    async def _get_next_priority_task(self) -> Optional[Dict[str, Any]]:
        """Get next task based on priority"""
        # Check queues in priority order
        for priority in [TaskPriority.CRITICAL, TaskPriority.HIGH, TaskPriority.NORMAL, TaskPriority.LOW]:
            try:
                queue = self.priority_queues[priority]
                if not queue.empty():
                    return queue.get_nowait()
            except asyncio.QueueEmpty:
                continue
        
        # Fall back to in-memory queue or Redis queue
        try:
            return await redis_queue.get_next_task()
        except:
            # Fallback to in-memory queue
            in_memory_queue = self._get_in_memory_queue()
            if in_memory_queue:
                return in_memory_queue.pop(0)
            return None
    
    async def _select_worker(self) -> Optional[str]:
        """Select best worker for task using configured strategy"""
        available_workers = [
            w_id for w_id, w in self.workers.items() 
            if w.status == WorkerStatus.IDLE
        ]
        
        if not available_workers:
            return None
        
        if self.load_balancing_strategy == "round_robin":
            worker_id = available_workers[self.round_robin_index % len(available_workers)]
            self.round_robin_index += 1
            return worker_id
        
        elif self.load_balancing_strategy == "least_loaded":
            # Select worker with least tasks processed
            best_worker = min(available_workers, 
                            key=lambda w_id: self.workers[w_id].tasks_processed)
            return best_worker
        
        elif self.load_balancing_strategy == "random":
            import random
            return random.choice(available_workers)
        
        return available_workers[0]
    
    async def _process_task_with_worker(self, worker_instance: WorkerInstance, task_data: Dict[str, Any]):
        """Process task using specific worker"""
        try:
            task_id = task_data['id']
            task_type = task_data['task_type']
            payload = task_data['payload']
            
            logger.info(f"Worker {worker_instance.worker_id} processing task {task_id}")
            
            # Get task from database
            task = await task_queue.get_task(task_id)
            if not task:
                logger.error(f"Task {task_id} not found in database")
                return
            
            # Execute task
            result = await enhanced_task_executor.execute_task(task)
            
            # Mark as completed in Redis
            try:
                await redis_queue.complete_task(task_id)
            except:
                pass  # Redis might not be available
            
            logger.info(f"Worker {worker_instance.worker_id} completed task {task_id}")
            
        except Exception as e:
            logger.error(f"Worker {worker_instance.worker_id} failed task: {str(e)}")
            worker_instance.error_count += 1
    
    def get_pool_status(self) -> Dict[str, Any]:
        """Get current pool status"""
        workers_by_status = {}
        for status in WorkerStatus:
            workers_by_status[status.value] = len([
                w for w in self.workers.values() if w.status == status
            ])
        
        return {
            "total_workers": len(self.workers),
            "min_workers": self.min_workers,
            "max_workers": self.max_workers,
            "workers_by_status": workers_by_status,
            "scaling_enabled": self.scaling_enabled,
            "load_balancing_strategy": self.load_balancing_strategy,
            "metrics": self.pool_metrics.copy(),
            "last_scale_time": self.pool_metrics.get("last_scale_time")
        }
    
    def get_worker_details(self) -> List[Dict[str, Any]]:
        """Get detailed information about all workers"""
        return [
            {
                "worker_id": w.worker_id,
                "status": w.status.value,
                "tasks_processed": w.tasks_processed,
                "error_count": w.error_count,
                "start_time": w.start_time,
                "last_heartbeat": w.last_heartbeat,
                "current_task_id": w.current_task_id,
                "uptime": time.time() - w.start_time
            }
            for w in self.workers.values()
        ]
    
    async def update_scaling_config(self, **config):
        """Update scaling configuration"""
        if "min_workers" in config:
            self.min_workers = max(1, config["min_workers"])
        
        if "max_workers" in config:
            self.max_workers = max(self.min_workers, config["max_workers"])
        
        if "scale_up_threshold" in config:
            self.scale_up_threshold = config["scale_up_threshold"]
        
        if "scale_down_threshold" in config:
            self.scale_down_threshold = config["scale_down_threshold"]
        
        if "scaling_enabled" in config:
            self.scaling_enabled = config["scaling_enabled"]
        
        logger.info(f"Updated scaling config: {config}")
    
    async def set_load_balancing_strategy(self, strategy: str):
        """Set load balancing strategy"""
        if strategy in ["round_robin", "least_loaded", "random"]:
            self.load_balancing_strategy = strategy
            logger.info(f"Load balancing strategy set to {strategy}")
        else:
            raise ValueError(f"Invalid strategy: {strategy}")


# Global worker pool instance
worker_pool = WorkerPool()
