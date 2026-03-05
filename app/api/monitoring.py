from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from app.services.monitoring_service import monitoring_service
from app.services.metrics_collector import metrics_collector
from app.services.enhanced_logger import enhanced_logger


router = APIRouter(prefix="/monitoring", tags=["monitoring"])


class SystemHealth(BaseModel):
    overall: str
    components: Dict[str, Any]
    last_check: str
    issues: List[str]


class AlertThreshold(BaseModel):
    cpu_warning: float = 0.7
    cpu_critical: float = 0.9
    memory_warning: float = 0.8
    memory_critical: float = 0.95
    disk_warning: float = 0.8
    disk_critical: float = 0.9
    queue_size_warning: int = 50
    queue_size_critical: int = 100
    failure_rate_warning: float = 0.05
    failure_rate_critical: float = 0.15
    response_time_warning: float = 5.0
    response_time_critical: float = 10.0


@router.get("/health", response_model=SystemHealth)
async def get_system_health():
    """Get comprehensive system health status"""
    try:
        health = monitoring_service.get_system_health()
        return SystemHealth(**health)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dashboard")
async def get_monitoring_dashboard():
    """Get comprehensive monitoring dashboard data"""
    try:
        dashboard = monitoring_service.get_monitoring_dashboard()
        return dashboard
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/metrics/system")
async def get_system_metrics(minutes: int = Query(60, ge=1, le=1440)):
    """Get system metrics for the last N minutes"""
    try:
        metrics = metrics_collector.get_system_metrics_summary(minutes)
        if not metrics:
            return {"message": "No system metrics available for the specified time range"}
        return metrics
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/metrics/tasks")
async def get_task_metrics(task_type: Optional[str] = None):
    """Get task execution metrics"""
    try:
        metrics = metrics_collector.get_task_type_stats(task_type)
        if not metrics:
            return {"message": "No task metrics available"}
        return metrics
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/metrics/performance")
async def get_performance_metrics(task_type: str, hours: int = Query(24, ge=1, le=168)):
    """Get performance trends for a specific task type"""
    try:
        trends = metrics_collector.get_performance_trends(task_type, hours)
        if not trends:
            return {"message": f"No performance data available for {task_type}"}
        return trends
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/alerts")
async def get_alerts(
    minutes: int = Query(60, ge=1, le=1440),
    severity: Optional[str] = Query(None, regex="^(warning|critical|info)$")
):
    """Get recent alerts"""
    try:
        alerts = metrics_collector.get_recent_alerts(minutes, severity)
        return {
            "alerts": alerts,
            "count": len(alerts),
            "time_range_minutes": minutes,
            "severity_filter": severity
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/errors")
async def get_error_patterns():
    """Get error patterns and frequencies"""
    try:
        error_patterns = metrics_collector.get_error_patterns()
        return {
            "error_patterns": error_patterns,
            "total_error_types": len(error_patterns),
            "most_common": max(error_patterns.items(), key=lambda x: x[1]) if error_patterns else None
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/logs/stats")
async def get_logging_statistics():
    """Get logging system statistics"""
    try:
        stats = enhanced_logger.get_log_stats()
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/alerts/thresholds", response_model=AlertThreshold)
async def get_alert_thresholds():
    """Get current alert thresholds"""
    try:
        thresholds = monitoring_service.get_alert_thresholds()
        return AlertThreshold(**thresholds)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/alerts/thresholds")
async def update_alert_thresholds(thresholds: AlertThreshold):
    """Update alert thresholds"""
    try:
        monitoring_service.update_alert_thresholds(**thresholds.dict())
        return {"message": "Alert thresholds updated successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/metrics/cleanup")
async def cleanup_old_metrics(days: int = Query(7, ge=1, le=30)):
    """Clean up old metrics and alerts"""
    try:
        cleared = metrics_collector.clear_old_metrics(days)
        return {
            "message": f"Cleaned up metrics older than {days} days",
            "cleared": cleared
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status/overview")
async def get_system_overview():
    """Get high-level system status overview"""
    try:
        health = monitoring_service.get_system_health()
        task_stats = metrics_collector.get_task_type_stats()
        system_metrics = metrics_collector.get_system_metrics_summary(60)
        recent_alerts = metrics_collector.get_recent_alerts(60, severity="critical")
        
        # Calculate summary statistics
        total_tasks = sum(stats.get('total', 0) for stats in task_stats.values())
        successful_tasks = sum(stats.get('successful', 0) for stats in task_stats.values())
        failed_tasks = sum(stats.get('failed', 0) for stats in task_stats.values())
        
        success_rate = (successful_tasks / total_tasks * 100) if total_tasks > 0 else 0
        
        overview = {
            "system_status": health['overall'],
            "uptime": "N/A",  # Would calculate from start time in production
            "task_summary": {
                "total_tasks": total_tasks,
                "successful_tasks": successful_tasks,
                "failed_tasks": failed_tasks,
                "success_rate": round(success_rate, 2)
            },
            "current_performance": {
                "cpu_usage": system_metrics.get('avg_cpu_usage', 0) * 100,
                "memory_usage": system_metrics.get('avg_memory_usage', 0) * 100,
                "queue_size": system_metrics.get('avg_queue_size', 0),
                "active_workers": system_metrics.get('avg_active_workers', 0)
            },
            "recent_issues": {
                "critical_alerts": len(recent_alerts),
                "system_issues": len(health['issues']),
                "last_check": health['last_check']
            },
            "component_health": {
                component: status['status'] for component, status in health['components'].items()
            }
        }
        
        return overview
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/performance/summary")
async def get_performance_summary():
    """Get performance summary for all task types"""
    try:
        task_stats = metrics_collector.get_task_type_stats()
        
        summary = {}
        for task_type, stats in task_stats.items():
            summary[task_type] = {
                "total_executions": stats.get('total', 0),
                "success_rate": stats.get('success_rate', 0) * 100,
                "failure_rate": stats.get('failure_rate', 0) * 100,
                "avg_execution_time": stats.get('avg_execution_time', 0),
                "min_execution_time": stats.get('min_execution_time', 0),
                "max_execution_time": stats.get('max_execution_time', 0),
                "retry_rate": (stats.get('retried', 0) / stats.get('total', 1)) * 100,
                "last_updated": stats.get('last_updated')
            }
        
        return {
            "task_types": summary,
            "summary_generated": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/logs/recent")
async def get_recent_logs(
    lines: int = Query(100, ge=10, le=1000),
    component: Optional[str] = Query(None, regex="^(app|tasks|errors|performance|audit)$")
):
    """Get recent log entries"""
    try:
        log_file = f"logs/{component}.log" if component else "logs/application.log"
        
        try:
            with open(log_file, 'r') as f:
                all_lines = f.readlines()
                recent_lines = all_lines[-lines:] if len(all_lines) > lines else all_lines
                
                return {
                    "log_file": log_file,
                    "total_lines": len(all_lines),
                    "returned_lines": len(recent_lines),
                    "logs": [line.strip() for line in recent_lines]
                }
        except FileNotFoundError:
            return {"message": f"Log file {log_file} not found"}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error reading log file: {str(e)}")
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
