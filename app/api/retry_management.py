from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from app.services.retry_handler import retry_handler, dead_letter_queue
from app.services.enhanced_task_executor import enhanced_task_executor


router = APIRouter(prefix="/retry", tags=["retry-management"])


class CircuitBreakerStatus(BaseModel):
    task_type: str
    state: str
    failures: int
    last_failure: Optional[float]


class DeadLetterTask(BaseModel):
    task_id: int
    task_type: str
    error_message: str
    error_type: str
    retry_count: int
    max_retries: int
    failed_at: float


@router.get("/circuit-breakers", response_model=List[CircuitBreakerStatus])
async def get_circuit_breakers():
    """Get status of all circuit breakers"""
    try:
        circuit_breakers = await retry_handler.get_circuit_breaker_status()
        
        result = []
        for task_type, breaker in circuit_breakers.items():
            result.append(CircuitBreakerStatus(
                task_type=task_type,
                state=breaker["state"],
                failures=breaker["failures"],
                last_failure=breaker["last_failure"]
            ))
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/circuit-breakers/{task_type}/reset")
async def reset_circuit_breaker(task_type: str):
    """Reset circuit breaker for a specific task type"""
    try:
        await retry_handler.reset_circuit_breaker(task_type)
        return {"message": f"Circuit breaker for {task_type} reset successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dead-letters", response_model=List[DeadLetterTask])
async def get_dead_letters(task_type: Optional[str] = None):
    """Get dead letter tasks"""
    try:
        dead_letters = await dead_letter_queue.get_dead_letters(task_type)
        
        result = []
        for dead_task in dead_letters:
            result.append(DeadLetterTask(**dead_task))
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/dead-letters/{task_id}/retry")
async def retry_dead_letter(task_id: int):
    """Retry a dead letter task"""
    try:
        success = await dead_letter_queue.retry_dead_letter(task_id)
        
        if success:
            return {"message": f"Dead letter task {task_id} requeued for retry"}
        else:
            raise HTTPException(status_code=404, detail=f"Dead letter task {task_id} not found")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/dead-letters")
async def purge_dead_letters(task_type: Optional[str] = None, older_than_hours: int = 24):
    """Purge old dead letter tasks"""
    try:
        purged_count = await dead_letter_queue.purge_dead_letters(task_type, older_than_hours)
        return {"message": f"Purged {purged_count} dead letter tasks"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def get_retry_stats():
    """Get retry and execution statistics"""
    try:
        execution_stats = enhanced_task_executor.get_execution_stats()
        circuit_breakers = await retry_handler.get_circuit_breaker_status()
        dead_letters = await dead_letter_queue.get_dead_letters()
        
        # Calculate circuit breaker stats
        cb_stats = {
            "total_circuit_breakers": len(circuit_breakers),
            "open_circuits": len([cb for cb in circuit_breakers.values() if cb["state"] == "open"]),
            "half_open_circuits": len([cb for cb in circuit_breakers.values() if cb["state"] == "half_open"]),
            "closed_circuits": len([cb for cb in circuit_breakers.values() if cb["state"] == "closed"])
        }
        
        # Dead letter stats
        dl_stats = {
            "total_dead_letters": len(dead_letters),
            "by_task_type": {}
        }
        
        for dead_task in dead_letters:
            task_type = dead_task["task_type"]
            if task_type not in dl_stats["by_task_type"]:
                dl_stats["by_task_type"][task_type] = 0
            dl_stats["by_task_type"][task_type] += 1
        
        return {
            "execution_stats": execution_stats,
            "circuit_breaker_stats": cb_stats,
            "dead_letter_stats": dl_stats
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/simulate-failure")
async def simulate_failure(task_type: str, error_type: str = "NetworkError"):
    """Simulate a failure for testing circuit breakers"""
    try:
        # Record a failure to trigger circuit breaker
        await retry_handler.record_failure(task_type)
        return {"message": f"Simulated {error_type} for {task_type}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
