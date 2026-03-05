import time
import asyncio
from typing import Dict, List, Any, Optional
from collections import defaultdict, deque
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from app.core.logging import logger


@dataclass
class TaskMetric:
    """Individual task execution metric"""
    task_id: int
    task_type: str
    status: str
    execution_time: float
    retry_count: int
    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    error_type: Optional[str] = None


@dataclass
class SystemMetric:
    """System-level metric"""
    timestamp: datetime
    cpu_usage: float
    memory_usage: float
    queue_size: int
    processing_count: int
    active_workers: int


class MetricsCollector:
    """Advanced metrics collection and analysis"""
    
    def __init__(self):
        self.task_metrics: deque = deque(maxlen=10000)  # Keep last 10k metrics
        self.system_metrics: deque = deque(maxlen=1440)  # Keep last 24h (1 per minute)
        self.task_type_stats: Dict[str, Dict] = defaultdict(lambda: {
            'total': 0, 'successful': 0, 'failed': 0, 'retried': 0,
            'avg_execution_time': 0.0, 'min_execution_time': float('inf'),
            'max_execution_time': 0.0, 'last_updated': datetime.min
        })
        self.hourly_stats: Dict[str, List[Dict]] = defaultdict(list)
        self.error_patterns: Dict[str, int] = defaultdict(int)
        self.performance_alerts: List[Dict] = []
        
        # Alert thresholds
        self.alert_thresholds = {
            'failure_rate': 0.1,  # 10% failure rate
            'avg_execution_time': 30.0,  # 30 seconds
            'queue_size': 100,  # 100 tasks in queue
            'memory_usage': 0.8,  # 80% memory usage
            'cpu_usage': 0.8  # 80% CPU usage
        }
    
    async def record_task_metric(self, metric: TaskMetric):
        """Record a task execution metric"""
        self.task_metrics.append(metric)
        
        # Update task type statistics
        stats = self.task_type_stats[metric.task_type]
        stats['total'] += 1
        
        if metric.status == 'completed':
            stats['successful'] += 1
            self._update_execution_time_stats(metric.task_type, metric.execution_time)
        elif metric.status == 'failed':
            stats['failed'] += 1
            if metric.error_type:
                self.error_patterns[metric.error_type] += 1
        elif metric.status == 'retrying':
            stats['retried'] += 1
        
        stats['last_updated'] = datetime.now()
        
        # Update hourly stats
        hour_key = metric.created_at.strftime('%Y-%m-%d-%H')
        self.hourly_stats[hour_key].append(asdict(metric))
        
        # Check for performance alerts
        await self._check_performance_alerts(metric)
        
        logger.debug(f"Recorded metric for task {metric.task_id}: {metric.status}")
    
    def _update_execution_time_stats(self, task_type: str, execution_time: float):
        """Update execution time statistics for a task type"""
        stats = self.task_type_stats[task_type]
        
        # Update min/max
        stats['min_execution_time'] = min(stats['min_execution_time'], execution_time)
        stats['max_execution_time'] = max(stats['max_execution_time'], execution_time)
        
        # Update average (running average)
        total_successful = stats['successful']
        if total_successful == 1:
            stats['avg_execution_time'] = execution_time
        else:
            # Weighted average
            stats['avg_execution_time'] = (
                (stats['avg_execution_time'] * (total_successful - 1) + execution_time) / 
                total_successful
            )
    
    async def record_system_metric(self, metric: SystemMetric):
        """Record a system-level metric"""
        self.system_metrics.append(metric)
        
        # Check system alerts
        await self._check_system_alerts(metric)
    
    async def _check_performance_alerts(self, metric: TaskMetric):
        """Check for performance-related alerts"""
        alerts = []
        
        # Check execution time
        if metric.execution_time > self.alert_thresholds['avg_execution_time']:
            alerts.append({
                'type': 'slow_execution',
                'severity': 'warning',
                'message': f"Task {metric.task_id} took {metric.execution_time:.2f}s (threshold: {self.alert_thresholds['avg_execution_time']}s)",
                'timestamp': datetime.now(),
                'task_id': metric.task_id,
                'task_type': metric.task_type
            })
        
        # Check failure patterns
        if metric.status == 'failed':
            failure_rate = self._calculate_failure_rate(metric.task_type)
            if failure_rate > self.alert_thresholds['failure_rate']:
                alerts.append({
                    'type': 'high_failure_rate',
                    'severity': 'critical',
                    'message': f"High failure rate for {metric.task_type}: {failure_rate:.2%}",
                    'timestamp': datetime.now(),
                    'task_type': metric.task_type,
                    'failure_rate': failure_rate
                })
        
        # Store alerts
        for alert in alerts:
            self.performance_alerts.append(alert)
            logger.warning(f"Performance alert: {alert['message']}")
    
    async def _check_system_alerts(self, metric: SystemMetric):
        """Check for system-level alerts"""
        alerts = []
        
        # Check memory usage
        if metric.memory_usage > self.alert_thresholds['memory_usage']:
            alerts.append({
                'type': 'high_memory_usage',
                'severity': 'critical',
                'message': f"High memory usage: {metric.memory_usage:.2%}",
                'timestamp': datetime.now(),
                'value': metric.memory_usage
            })
        
        # Check CPU usage
        if metric.cpu_usage > self.alert_thresholds['cpu_usage']:
            alerts.append({
                'type': 'high_cpu_usage',
                'severity': 'warning',
                'message': f"High CPU usage: {metric.cpu_usage:.2%}",
                'timestamp': datetime.now(),
                'value': metric.cpu_usage
            })
        
        # Check queue size
        if metric.queue_size > self.alert_thresholds['queue_size']:
            alerts.append({
                'type': 'large_queue',
                'severity': 'warning',
                'message': f"Large queue size: {metric.queue_size} tasks",
                'timestamp': datetime.now(),
                'value': metric.queue_size
            })
        
        # Store alerts
        for alert in alerts:
            self.performance_alerts.append(alert)
            logger.warning(f"System alert: {alert['message']}")
    
    def _calculate_failure_rate(self, task_type: str, minutes: int = 10) -> float:
        """Calculate failure rate for a task type in the last N minutes"""
        cutoff_time = datetime.now() - timedelta(minutes=minutes)
        
        recent_tasks = [
            m for m in self.task_metrics 
            if m.task_type == task_type and m.created_at > cutoff_time
        ]
        
        if not recent_tasks:
            return 0.0
        
        failed_count = sum(1 for m in recent_tasks if m.status == 'failed')
        return failed_count / len(recent_tasks)
    
    def get_task_type_stats(self, task_type: str = None) -> Dict[str, Any]:
        """Get statistics for task types"""
        if task_type:
            if task_type not in self.task_type_stats:
                return {}
            stats = self.task_type_stats[task_type].copy()
            # Calculate success rate
            if stats['total'] > 0:
                stats['success_rate'] = stats['successful'] / stats['total']
                stats['failure_rate'] = stats['failed'] / stats['total']
            else:
                stats['success_rate'] = 0.0
                stats['failure_rate'] = 0.0
            return stats
        else:
            # Return all task type stats
            result = {}
            for tt, stats in self.task_type_stats.items():
                result[tt] = self.get_task_type_stats(tt)
            return result
    
    def get_system_metrics_summary(self, minutes: int = 60) -> Dict[str, Any]:
        """Get summary of system metrics for the last N minutes"""
        cutoff_time = datetime.now() - timedelta(minutes=minutes)
        
        recent_system_metrics = [
            m for m in self.system_metrics 
            if m.timestamp > cutoff_time
        ]
        
        if not recent_system_metrics:
            return {}
        
        # Calculate averages
        avg_cpu = sum(m.cpu_usage for m in recent_system_metrics) / len(recent_system_metrics)
        avg_memory = sum(m.memory_usage for m in recent_system_metrics) / len(recent_system_metrics)
        avg_queue_size = sum(m.queue_size for m in recent_system_metrics) / len(recent_system_metrics)
        avg_workers = sum(m.active_workers for m in recent_system_metrics) / len(recent_system_metrics)
        
        return {
            'time_range_minutes': minutes,
            'avg_cpu_usage': avg_cpu,
            'avg_memory_usage': avg_memory,
            'avg_queue_size': avg_queue_size,
            'avg_active_workers': avg_workers,
            'max_cpu_usage': max(m.cpu_usage for m in recent_system_metrics),
            'max_memory_usage': max(m.memory_usage for m in recent_system_metrics),
            'max_queue_size': max(m.queue_size for m in recent_system_metrics),
            'max_active_workers': max(m.active_workers for m in recent_system_metrics),
            'sample_count': len(recent_system_metrics)
        }
    
    def get_error_patterns(self) -> Dict[str, int]:
        """Get error patterns (most common errors)"""
        return dict(sorted(self.error_patterns.items(), key=lambda x: x[1], reverse=True))
    
    def get_recent_alerts(self, minutes: int = 60, severity: str = None) -> List[Dict]:
        """Get recent alerts"""
        cutoff_time = datetime.now() - timedelta(minutes=minutes)
        
        alerts = [
            alert for alert in self.performance_alerts
            if alert['timestamp'] > cutoff_time
        ]
        
        if severity:
            alerts = [a for a in alerts if a['severity'] == severity]
        
        return sorted(alerts, key=lambda x: x['timestamp'], reverse=True)
    
    def get_performance_trends(self, task_type: str, hours: int = 24) -> Dict[str, List]:
        """Get performance trends for a task type"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        relevant_metrics = [
            m for m in self.task_metrics
            if m.task_type == task_type and m.created_at > cutoff_time
        ]
        
        if not relevant_metrics:
            return {}
        
        # Group by hour
        hourly_data = defaultdict(lambda: {'execution_times': [], 'success_count': 0, 'total_count': 0})
        
        for metric in relevant_metrics:
            hour_key = metric.created_at.strftime('%Y-%m-%d-%H')
            hourly_data[hour_key]['execution_times'].append(metric.execution_time)
            hourly_data[hour_key]['total_count'] += 1
            if metric.status == 'completed':
                hourly_data[hour_key]['success_count'] += 1
        
        # Calculate hourly averages
        trends = {
            'hours': sorted(hourly_data.keys()),
            'avg_execution_times': [],
            'success_rates': []
        }
        
        for hour in trends['hours']:
            data = hourly_data[hour]
            avg_time = sum(data['execution_times']) / len(data['execution_times'])
            success_rate = data['success_count'] / data['total_count']
            
            trends['avg_execution_times'].append(avg_time)
            trends['success_rates'].append(success_rate)
        
        return trends
    
    def clear_old_metrics(self, days: int = 7):
        """Clear metrics older than specified days"""
        cutoff_time = datetime.now() - timedelta(days=days)
        
        # Clear old task metrics
        original_size = len(self.task_metrics)
        self.task_metrics = deque(
            (m for m in self.task_metrics if m.created_at > cutoff_time),
            maxlen=10000
        )
        
        # Clear old system metrics
        original_system_size = len(self.system_metrics)
        self.system_metrics = deque(
            (m for m in self.system_metrics if m.timestamp > cutoff_time),
            maxlen=1440
        )
        
        # Clear old alerts
        original_alerts_size = len(self.performance_alerts)
        self.performance_alerts = [
            alert for alert in self.performance_alerts
            if alert['timestamp'] > cutoff_time
        ]
        
        cleared_task = original_size - len(self.task_metrics)
        cleared_system = original_system_size - len(self.system_metrics)
        cleared_alerts = original_alerts_size - len(self.performance_alerts)
        
        logger.info(f"Cleared old metrics: {cleared_task} task metrics, {cleared_system} system metrics, {cleared_alerts} alerts")
        
        return {
            'task_metrics_cleared': cleared_task,
            'system_metrics_cleared': cleared_system,
            'alerts_cleared': cleared_alerts
        }


# Global metrics collector instance
metrics_collector = MetricsCollector()
