import asyncio
import time
import math
import random
from typing import Optional, Dict, Any
from enum import Enum
from app.core.config import settings
from app.core.logging import logger
from app.models.task_model import Task, TaskStatus


class RetryStrategy(Enum):
    """Retry strategy types"""
    FIXED = "fixed"
    EXPONENTIAL = "exponential"
    LINEAR = "linear"
    JITTER = "jitter"


class RetryHandler:
    """Advanced retry logic with multiple strategies"""
    
    def __init__(self):
        self.circuit_breakers: Dict[str, Dict] = {}
        self.failure_threshold = 5  # Failures before circuit breaker opens
        self.recovery_timeout = 60  # Seconds to wait before recovery
    
    async def should_retry(self, task: Task, error: Exception) -> tuple[bool, Optional[int]]:
        """
        Determine if a task should be retried and calculate delay
        
        Returns:
            (should_retry, delay_seconds)
        """
        # Check if task has exceeded max retries
        if task.retry_count >= task.max_retries:
            logger.info(f"Task {task.id} exceeded max retries ({task.max_retries})")
            return False, None
        
        # Check circuit breaker for this task type
        if not await self._check_circuit_breaker(task.task_type):
            logger.warning(f"Circuit breaker open for task type {task.task_type}")
            return False, None
        
        # Calculate retry delay based on strategy
        delay = await self._calculate_retry_delay(task, error)
        
        logger.info(f"Task {task.id} will retry in {delay}s (attempt {task.retry_count + 1})")
        return True, delay
    
    async def _calculate_retry_delay(self, task: Task, error: Exception) -> int:
        """Calculate retry delay based on strategy and error type"""
        strategy = self._get_retry_strategy(task.task_type, error)
        base_delay = settings.retry_delay
        
        if strategy == RetryStrategy.FIXED:
            return base_delay
        
        elif strategy == RetryStrategy.EXPONENTIAL:
            # Exponential backoff: delay = base * 2^attempt
            delay = base_delay * (2 ** task.retry_count)
            return min(delay, 300)  # Cap at 5 minutes
        
        elif strategy == RetryStrategy.LINEAR:
            # Linear backoff: delay = base * attempt
            delay = base_delay * (task.retry_count + 1)
            return min(delay, 120)  # Cap at 2 minutes
        
        elif strategy == RetryStrategy.JITTER:
            # Exponential with jitter to prevent thundering herd
            exponential_delay = base_delay * (2 ** task.retry_count)
            jitter = random.uniform(0.1, 0.3) * exponential_delay
            delay = exponential_delay + jitter
            return min(int(delay), 300)  # Cap at 5 minutes
        
        return base_delay
    
    def _get_retry_strategy(self, task_type: str, error: Exception) -> RetryStrategy:
        """Determine retry strategy based on task type and error"""
        error_type = type(error).__name__
        
        # Network errors use exponential backoff
        if error_type in ["ConnectionError", "TimeoutError", "NetworkError"]:
            return RetryStrategy.EXPONENTIAL
        
        # Rate limiting uses jitter
        if error_type in ["RateLimitError", "TooManyRequestsError"]:
            return RetryStrategy.JITTER
        
        # Database errors use linear backoff
        if error_type in ["DatabaseError", "ConnectionPoolError"]:
            return RetryStrategy.LINEAR
        
        # Default to exponential for unknown errors
        return RetryStrategy.EXPONENTIAL
    
    async def _check_circuit_breaker(self, task_type: str) -> bool:
        """Check if circuit breaker is open for this task type"""
        if task_type not in self.circuit_breakers:
            self.circuit_breakers[task_type] = {
                "failures": 0,
                "last_failure": None,
                "state": "closed"  # closed, open, half_open
            }
        
        breaker = self.circuit_breakers[task_type]
        
        # If circuit is open, check if recovery timeout has passed
        if breaker["state"] == "open":
            if breaker["last_failure"] and \
               (time.time() - breaker["last_failure"]) > self.recovery_timeout:
                # Try to close circuit (half-open state)
                breaker["state"] = "half_open"
                logger.info(f"Circuit breaker for {task_type} entering half-open state")
                return True
            else:
                return False  # Circuit still open
        
        return True  # Circuit is closed or half-open
    
    async def record_success(self, task_type: str):
        """Record successful task execution"""
        if task_type in self.circuit_breakers:
            breaker = self.circuit_breakers[task_type]
            
            # Reset circuit breaker on success
            if breaker["state"] == "half_open":
                breaker["state"] = "closed"
                breaker["failures"] = 0
                logger.info(f"Circuit breaker for {task_type} closed after successful execution")
    
    async def record_failure(self, task_type: str):
        """Record failed task execution"""
        if task_type not in self.circuit_breakers:
            self.circuit_breakers[task_type] = {
                "failures": 0,
                "last_failure": None,
                "state": "closed"
            }
        
        breaker = self.circuit_breakers[task_type]
        breaker["failures"] += 1
        breaker["last_failure"] = time.time()
        
        # Open circuit breaker if threshold reached
        if breaker["failures"] >= self.failure_threshold and breaker["state"] != "open":
            breaker["state"] = "open"
            logger.warning(f"Circuit breaker opened for {task_type} after {breaker['failures']} failures")
    
    async def get_circuit_breaker_status(self) -> Dict[str, Dict]:
        """Get status of all circuit breakers"""
        return self.circuit_breakers.copy()
    
    async def reset_circuit_breaker(self, task_type: str):
        """Manually reset circuit breaker for a task type"""
        if task_type in self.circuit_breakers:
            self.circuit_breakers[task_type] = {
                "failures": 0,
                "last_failure": None,
                "state": "closed"
            }
            logger.info(f"Circuit breaker for {task_type} manually reset")


class DeadLetterQueue:
    """Handle tasks that have permanently failed"""
    
    def __init__(self):
        self.dead_tasks: Dict[int, Dict] = {}
    
    async def add_dead_letter(self, task: Task, error: Exception):
        """Add task to dead letter queue"""
        dead_letter = {
            "task_id": task.id,
            "task_type": task.task_type,
            "payload": task.payload,
            "error_message": str(error),
            "error_type": type(error).__name__,
            "retry_count": task.retry_count,
            "max_retries": task.max_retries,
            "created_at": task.created_at.isoformat() if task.created_at else None,
            "failed_at": time.time()
        }
        
        self.dead_tasks[task.id] = dead_letter
        logger.error(f"Task {task.id} added to dead letter queue: {str(error)}")
    
    async def get_dead_letters(self, task_type: str = None) -> list:
        """Get dead letter tasks"""
        if task_type:
            return [task for task in self.dead_tasks.values() if task["task_type"] == task_type]
        return list(self.dead_tasks.values())
    
    async def retry_dead_letter(self, task_id: int) -> bool:
        """Retry a dead letter task"""
        if task_id not in self.dead_tasks:
            return False
        
        dead_task = self.dead_tasks[task_id]
        
        # Reset retry count and requeue
        from app.services.task_queue import task_queue
        from app.services.redis_queue import redis_queue
        
        try:
            # Get the task from database
            task = await task_queue.get_task(task_id)
            if task:
                task.retry_count = 0
                task.status = TaskStatus.PENDING
                await task_queue.update_task_status(task_id, TaskStatus.PENDING)
                
                # Re-add to Redis queue
                await redis_queue.create_task(task.task_type, dead_task["payload"])
                
                # Remove from dead letter queue
                del self.dead_tasks[task_id]
                
                logger.info(f"Dead letter task {task_id} requeued for retry")
                return True
        except Exception as e:
            logger.error(f"Failed to retry dead letter task {task_id}: {str(e)}")
        
        return False
    
    async def purge_dead_letters(self, task_type: str = None, older_than_hours: int = 24):
        """Purge old dead letter tasks"""
        cutoff_time = time.time() - (older_than_hours * 3600)
        
        to_remove = []
        for task_id, dead_task in self.dead_tasks.items():
            if task_type and dead_task["task_type"] != task_type:
                continue
            
            if dead_task["failed_at"] < cutoff_time:
                to_remove.append(task_id)
        
        for task_id in to_remove:
            del self.dead_tasks[task_id]
        
        logger.info(f"Purged {len(to_remove)} dead letter tasks older than {older_than_hours}h")
        return len(to_remove)


# Global instances
retry_handler = RetryHandler()
dead_letter_queue = DeadLetterQueue()
