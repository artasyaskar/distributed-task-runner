from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List
from app.services.worker_pool import worker_pool, WorkerStatus
from app.services.auto_scaler import auto_scaler, ScalingPolicy, ScalingRule


router = APIRouter(prefix="/scaling", tags=["scaling"])


class WorkerPoolStatus(BaseModel):
    total_workers: int
    min_workers: int
    max_workers: int
    workers_by_status: Dict[str, int]
    scaling_enabled: bool
    load_balancing_strategy: str
    last_scale_time: Optional[float]


class WorkerDetails(BaseModel):
    worker_id: str
    status: str
    tasks_processed: int
    error_count: int
    start_time: float
    last_heartbeat: float
    current_task_id: Optional[int]
    uptime: float


class ScalingConfig(BaseModel):
    min_workers: int = Field(ge=1, le=20)
    max_workers: int = Field(ge=1, le=50)
    scale_up_threshold: int = Field(ge=1, le=100)
    scale_down_threshold: int = Field(ge=0, le=50)
    scaling_enabled: bool = True


class LoadBalancingConfig(BaseModel):
    strategy: str = Field(pattern="^(round_robin|least_loaded|random)$")


class CustomRule(BaseModel):
    name: str
    policy: str = Field(pattern="^(queue_based|cpu_based|memory_based|custom|predictive)$")
    scale_up_condition: str
    scale_down_condition: str
    cooldown_period: int = Field(ge=30, le=3600)
    max_scale_up_step: int = Field(ge=1, le=10)
    max_scale_down_step: int = Field(ge=1, le=10)
    enabled: bool = True


@router.get("/pool/status", response_model=WorkerPoolStatus)
async def get_pool_status():
    """Get current worker pool status"""
    try:
        status = worker_pool.get_pool_status()
        return WorkerPoolStatus(**status)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/workers", response_model=List[WorkerDetails])
async def get_worker_details():
    """Get detailed information about all workers"""
    try:
        workers = worker_pool.get_worker_details()
        return [WorkerDetails(**worker) for worker in workers]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/workers/{worker_id}", response_model=WorkerDetails)
async def get_worker_detail(worker_id: str):
    """Get detailed information about a specific worker"""
    try:
        workers = worker_pool.get_worker_details()
        for worker in workers:
            if worker["worker_id"] == worker_id:
                return WorkerDetails(**worker)
        
        raise HTTPException(status_code=404, detail="Worker not found")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/pool/scale")
async def scale_pool(target_workers: int = Query(..., ge=1, le=50)):
    """Manually scale worker pool to specific number of workers"""
    try:
        current_status = worker_pool.get_pool_status()
        current_workers = current_status["total_workers"]
        
        if target_workers < current_status["min_workers"]:
            raise HTTPException(
                status_code=400, 
                detail=f"Cannot scale below minimum workers ({current_status['min_workers']})"
            )
        
        if target_workers > current_status["max_workers"]:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot scale above maximum workers ({current_status['max_workers']})"
            )
        
        await worker_pool._scale_to_workers(target_workers)
        
        return {
            "message": f"Pool scaled from {current_workers} to {target_workers} workers",
            "previous_workers": current_workers,
            "new_workers": target_workers
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/pool/config", response_model=ScalingConfig)
async def update_pool_config(config: ScalingConfig):
    """Update worker pool configuration"""
    try:
        if config.min_workers >= config.max_workers:
            raise HTTPException(
                status_code=400,
                detail="min_workers must be less than max_workers"
            )
        
        await worker_pool.update_scaling_config(**config.dict())
        
        return config
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/pool/load-balancing")
async def update_load_balancing(config: LoadBalancingConfig):
    """Update load balancing strategy"""
    try:
        await worker_pool.set_load_balancing_strategy(config.strategy)
        return {"message": f"Load balancing strategy set to {config.strategy}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/auto-scaler/status")
async def get_auto_scaler_status():
    """Get auto-scaler status and configuration"""
    try:
        status = auto_scaler.get_scaling_status()
        return status
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/auto-scaler/enable")
async def enable_auto_scaler():
    """Enable auto-scaler"""
    try:
        auto_scaler.enabled = True
        return {"message": "Auto-scaler enabled"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/auto-scaler/disable")
async def disable_auto_scaler():
    """Disable auto-scaler"""
    try:
        auto_scaler.enabled = False
        return {"message": "Auto-scaler disabled"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/auto-scaler/policy")
async def set_scaling_policy(policy: str = Query(..., pattern="^(queue_based|cpu_based|memory_based|custom|predictive)$")):
    """Set auto-scaling policy"""
    try:
        policy_enum = ScalingPolicy(policy)
        await auto_scaler.set_policy(policy_enum)
        return {"message": f"Scaling policy set to {policy}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/auto-scaler/rules")
async def get_scaling_rules():
    """Get all scaling rules"""
    try:
        rules = {}
        for name, rule in auto_scaler.rules.items():
            rules[name] = {
                "name": rule.name,
                "policy": rule.policy.value,
                "scale_up_condition": rule.scale_up_condition,
                "scale_down_condition": rule.scale_down_condition,
                "cooldown_period": rule.cooldown_period,
                "max_scale_up_step": rule.max_scale_up_step,
                "max_scale_down_step": rule.max_scale_down_step,
                "enabled": rule.enabled
            }
        return rules
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/auto-scaler/rules", response_model=CustomRule)
async def add_custom_rule(rule: CustomRule):
    """Add a custom scaling rule"""
    try:
        scaling_rule = ScalingRule(
            name=rule.name,
            policy=ScalingPolicy(rule.policy),
            scale_up_condition=rule.scale_up_condition,
            scale_down_condition=rule.scale_down_condition,
            cooldown_period=rule.cooldown_period,
            max_scale_up_step=rule.max_scale_up_step,
            max_scale_down_step=rule.max_scale_down_step,
            enabled=rule.enabled
        )
        
        await auto_scaler.add_custom_rule(scaling_rule)
        return rule
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/auto-scaler/rules/{rule_name}/enable")
async def enable_scaling_rule(rule_name: str):
    """Enable a specific scaling rule"""
    try:
        await auto_scaler.enable_rule(rule_name)
        return {"message": f"Rule {rule_name} enabled"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/auto-scaler/rules/{rule_name}/disable")
async def disable_scaling_rule(rule_name: str):
    """Disable a specific scaling rule"""
    try:
        await auto_scaler.disable_rule(rule_name)
        return {"message": f"Rule {rule_name} disabled"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/metrics/performance")
async def get_performance_metrics(minutes: int = Query(60, ge=1, le=1440)):
    """Get performance metrics for scaling decisions"""
    try:
        from app.services.metrics_collector import metrics_collector
        
        # Get system metrics
        system_metrics = metrics_collector.get_system_metrics_summary(minutes)
        
        # Get task statistics
        task_stats = metrics_collector.get_task_type_stats()
        
        # Calculate performance indicators
        total_tasks = sum(stats.get("total", 0) for stats in task_stats.values())
        successful_tasks = sum(stats.get("successful", 0) for stats in task_stats.values())
        success_rate = (successful_tasks / total_tasks * 100) if total_tasks > 0 else 0
        
        avg_execution_time = 0
        if task_stats:
            total_time = sum(stats.get("avg_execution_time", 0) * stats.get("total", 0) 
                           for stats in task_stats.values())
            total_processed = sum(stats.get("total", 0) for stats in task_stats.values())
            avg_execution_time = total_time / total_processed if total_processed > 0 else 0
        
        return {
            "time_range_minutes": minutes,
            "system_metrics": system_metrics,
            "task_metrics": {
                "total_tasks": total_tasks,
                "successful_tasks": successful_tasks,
                "success_rate": success_rate,
                "avg_execution_time": avg_execution_time
            },
            "performance_indicators": {
                "throughput": total_tasks / (minutes / 60) if minutes > 0 else 0,  # tasks per hour
                "error_rate": (total_tasks - successful_tasks) / total_tasks * 100 if total_tasks > 0 else 0,
                "avg_tasks_per_worker": total_tasks / worker_pool.get_pool_status()["total_workers"] if worker_pool.get_pool_status()["total_workers"] > 0 else 0
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def get_scaling_health():
    """Get scaling system health"""
    try:
        pool_status = worker_pool.get_pool_status()
        scaler_status = auto_scaler.get_scaling_status()
        
        # Determine overall health
        health_issues = []
        
        if not auto_scaler.enabled:
            health_issues.append("Auto-scaler is disabled")
        
        if pool_status["total_workers"] == 0:
            health_issues.append("No workers available")
        
        if pool_status["workers_by_status"].get("error", 0) > 0:
            health_issues.append(f"{pool_status['workers_by_status']['error']} workers in error state")
        
        overall_health = "healthy" if not health_issues else "degraded"
        
        return {
            "overall_health": overall_health,
            "issues": health_issues,
            "worker_pool": pool_status,
            "auto_scaler": scaler_status
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/workers/{worker_id}/restart")
async def restart_worker(worker_id: str):
    """Restart a specific worker"""
    try:
        if worker_id not in worker_pool.workers:
            raise HTTPException(status_code=404, detail="Worker not found")
        
        # Remove and recreate worker
        await worker_pool._remove_worker(worker_id)
        new_worker_id = await worker_pool._create_worker()
        
        return {
            "message": f"Worker {worker_id} restarted as {new_worker_id}",
            "old_worker_id": worker_id,
            "new_worker_id": new_worker_id
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
