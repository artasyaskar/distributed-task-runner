import json
import asyncio
import time
from typing import Dict, Any
from app.core.logging import logger
from app.core.config import settings
from app.models.task_model import Task, TaskStatus
from app.services.task_queue import task_queue


class TaskExecutor:
    """Handles execution of different task types"""
    
    async def execute_task(self, task: Task) -> Dict[str, Any]:
        """Execute a task and return the result"""
        logger.info(f"Executing task {task.id} of type {task.task_type}")
        
        try:
            # Update status to running
            await task_queue.update_task_status(task.id, TaskStatus.RUNNING)
            
            # Execute based on task type
            if task.task_type == "text_processing":
                result = await self._process_text(task)
            elif task.task_type == "ai_summarization":
                result = await self._ai_summarize(task)
            elif task.task_type == "batch_processing":
                result = await self._batch_process(task)
            elif task.task_type == "image_processing":
                result = await self._process_image(task)
            else:
                raise ValueError(f"Unknown task type: {task.task_type}")
            
            # Mark as completed
            await task_queue.update_task_status(
                task.id, 
                TaskStatus.COMPLETED, 
                result=json.dumps(result)
            )
            
            logger.info(f"Task {task.id} completed successfully")
            return result
            
        except Exception as e:
            logger.error(f"Task {task.id} failed: {str(e)}")
            
            # Mark as failed
            await task_queue.update_task_status(
                task.id, 
                TaskStatus.FAILED, 
                error_message=str(e)
            )
            
            # Check if we should retry
            if task.retry_count < task.max_retries:
                await asyncio.sleep(settings.retry_delay)
                await task_queue.retry_task(task.id)
            
            raise
    
    async def _process_text(self, task: Task) -> Dict[str, Any]:
        """Simulate text processing task"""
        payload = json.loads(task.payload)
        text = payload.get("text", "")
        
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
    
    async def _ai_summarize(self, task: Task) -> Dict[str, Any]:
        """Simulate AI summarization task"""
        payload = json.loads(task.payload)
        document = payload.get("document", "")
        
        # Simulate AI processing time
        await asyncio.sleep(5)
        
        # Mock summarization
        summary = f"Summary of {len(document)} character document: This is a simulated AI summary."
        
        return {
            "summary": summary,
            "original_length": len(document),
            "summary_length": len(summary),
            "processing_time": 5.0
        }
    
    async def _batch_process(self, task: Task) -> Dict[str, Any]:
        """Simulate batch data processing"""
        payload = json.loads(task.payload)
        data = payload.get("data", [])
        
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
    
    async def _process_image(self, task: Task) -> Dict[str, Any]:
        """Simulate image processing task"""
        payload = json.loads(task.payload)
        image_url = payload.get("image_url", "")
        
        # Simulate image processing
        await asyncio.sleep(4)
        
        return {
            "original_url": image_url,
            "resized_url": f"resized_{image_url}",
            "compressed_url": f"compressed_{image_url}",
            "analysis": {"faces": 1, "objects": 5},
            "processing_time": 4.0
        }


# Global executor instance
task_executor = TaskExecutor()
