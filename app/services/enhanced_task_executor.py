import json
import asyncio
import time
import random
from typing import Dict, Any
from app.core.logging import logger
from app.core.config import settings
from app.models.task_model import Task, TaskStatus
from app.services.task_queue import task_queue
from app.services.retry_handler import retry_handler, dead_letter_queue


class EnhancedTaskExecutor:
    """Enhanced task executor with advanced retry logic"""
    
    def __init__(self):
        self.execution_stats = {
            "total_executed": 0,
            "successful": 0,
            "failed": 0,
            "retried": 0
        }
    
    async def execute_task(self, task: Task) -> Dict[str, Any]:
        """Execute a task with enhanced retry logic"""
        logger.info(f"Executing task {task.id} of type {task.task_type}")
        
        self.execution_stats["total_executed"] += 1
        
        try:
            # Update status to running
            await task_queue.update_task_status(task.id, TaskStatus.RUNNING)
            
            # Execute based on task type with error simulation
            if task.task_type == "text_processing":
                result = await self._process_text_with_errors(task)
            elif task.task_type == "ai_summarization":
                result = await self._ai_summarize_with_errors(task)
            elif task.task_type == "batch_processing":
                result = await self._batch_process_with_errors(task)
            elif task.task_type == "image_processing":
                result = await self._process_image_with_errors(task)
            else:
                raise ValueError(f"Unknown task type: {task.task_type}")
            
            # Mark as completed
            await task_queue.update_task_status(
                task.id, 
                TaskStatus.COMPLETED, 
                result=json.dumps(result)
            )
            
            # Record success for circuit breaker
            await retry_handler.record_success(task.task_type)
            
            self.execution_stats["successful"] += 1
            logger.info(f"Task {task.id} completed successfully")
            return result
            
        except Exception as e:
            logger.error(f"Task {task.id} failed: {str(e)}")
            
            # Record failure for circuit breaker
            await retry_handler.record_failure(task.task_type)
            
            # Check if we should retry
            should_retry, delay = await retry_handler.should_retry(task, e)
            
            if should_retry:
                # Schedule retry
                await self._schedule_retry(task, delay)
                self.execution_stats["retried"] += 1
            else:
                # Mark as permanently failed and add to dead letter queue
                await task_queue.update_task_status(
                    task.id, 
                    TaskStatus.FAILED, 
                    error_message=str(e)
                )
                await dead_letter_queue.add_dead_letter(task, e)
                self.execution_stats["failed"] += 1
            
            raise
    
    async def _schedule_retry(self, task: Task, delay: int):
        """Schedule task for retry after delay"""
        logger.info(f"Scheduling task {task.id} for retry in {delay}s")
        
        # Update task status to retrying
        await task_queue.update_task_status(task.id, TaskStatus.RETRYING)
        
        # Increment retry count
        task.retry_count += 1
        
        # Schedule the retry
        asyncio.create_task(self._retry_after_delay(task, delay))
    
    async def _retry_after_delay(self, task: Task, delay: int):
        """Execute retry after specified delay"""
        await asyncio.sleep(delay)
        
        try:
            # Re-add task to queue
            from app.services.redis_queue import redis_queue
            payload = json.loads(task.payload)
            await redis_queue.create_task(task.task_type, payload)
            
            logger.info(f"Task {task.id} requeued for retry")
        except Exception as e:
            logger.error(f"Failed to requeue task {task.id} for retry: {str(e)}")
    
    async def _process_text_with_errors(self, task: Task) -> Dict[str, Any]:
        """Text processing with simulated errors"""
        payload = json.loads(task.payload)
        text = payload.get("text", "")
        
        # Simulate occasional failures (10% chance)
        if random.random() < 0.1:
            if random.random() < 0.5:
                raise ConnectionError("Simulated network error during text processing")
            else:
                raise TimeoutError("Simulated timeout during text processing")
        
        # Simulate processing time
        await asyncio.sleep(3)
        
        # Simple text processing
        word_count = len(text.split())
        char_count = len(text)
        
        return {
            "word_count": word_count,
            "char_count": char_count,
            "processed_text": text.upper(),
            "processing_time": 3.0
        }
    
    async def _ai_summarize_with_errors(self, task: Task) -> Dict[str, Any]:
        """AI summarization with simulated errors"""
        payload = json.loads(task.payload)
        document = payload.get("document", "")
        
        # Simulate rate limiting (5% chance)
        if random.random() < 0.05:
            raise Exception("RateLimitError: API rate limit exceeded")
        
        # Simulate processing time
        await asyncio.sleep(5)
        
        # Mock summarization
        summary = f"Summary of {len(document)} character document: This is a simulated AI summary."
        
        return {
            "summary": summary,
            "original_length": len(document),
            "summary_length": len(summary),
            "processing_time": 5.0
        }
    
    async def _batch_process_with_errors(self, task: Task) -> Dict[str, Any]:
        """Batch processing with simulated errors"""
        payload = json.loads(task.payload)
        data = payload.get("data", [])
        
        # Simulate database errors (8% chance)
        if random.random() < 0.08:
            raise Exception("DatabaseError: Connection pool exhausted")
        
        # Simulate processing time based on data size
        processing_time = min(len(data) * 0.1, 10)  # Max 10 seconds
        await asyncio.sleep(processing_time)
        
        # Simple data transformation
        processed_data = [{"item": item, "processed": True} for item in data]
        
        return {
            "processed_count": len(processed_data),
            "processing_time": processing_time,
            "data": processed_data[:5]  # Return first 5 items as sample
        }
    
    async def _process_image_with_errors(self, task: Task) -> Dict[str, Any]:
        """Image processing with simulated errors"""
        payload = json.loads(task.payload)
        image_url = payload.get("image_url", "")
        
        # Simulate service errors (7% chance)
        if random.random() < 0.07:
            raise Exception("ServiceUnavailableError: Image processing service down")
        
        # Simulate image processing
        await asyncio.sleep(4)
        
        return {
            "original_url": image_url,
            "resized_url": f"resized_{image_url}",
            "compressed_url": f"compressed_{image_url}",
            "analysis": {"faces": 1, "objects": 5},
            "processing_time": 4.0
        }
    
    def get_execution_stats(self) -> Dict[str, Any]:
        """Get execution statistics"""
        total = self.execution_stats["total_executed"]
        if total == 0:
            return self.execution_stats.copy()
        
        stats = self.execution_stats.copy()
        stats["success_rate"] = (stats["successful"] / total) * 100
        stats["failure_rate"] = (stats["failed"] / total) * 100
        stats["retry_rate"] = (stats["retried"] / total) * 100
        
        return stats
    
    def reset_stats(self):
        """Reset execution statistics"""
        self.execution_stats = {
            "total_executed": 0,
            "successful": 0,
            "failed": 0,
            "retried": 0
        }


# Global enhanced executor instance
enhanced_task_executor = EnhancedTaskExecutor()
