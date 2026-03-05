import asyncio
import time
import psutil
import json
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from app.services.metrics_collector import metrics_collector, TaskMetric, SystemMetric
from app.services.enhanced_logger import enhanced_logger
from app.services.redis_queue import redis_queue
from app.services.task_queue import task_queue
from app.services.retry_handler import retry_handler, dead_letter_queue


class MonitoringService:
    """Comprehensive monitoring service for the distributed task system"""
    
    def __init__(self):
        self.running = False
        self.monitoring_interval = 60  # seconds
        self.health_checks = {}
        self.alert_thresholds = {
            'cpu_warning': 0.7,
            'cpu_critical': 0.9,
            'memory_warning': 0.8,
            'memory_critical': 0.95,
            'disk_warning': 0.8,
            'disk_critical': 0.9,
            'queue_size_warning': 50,
            'queue_size_critical': 100,
            'failure_rate_warning': 0.05,
            'failure_rate_critical': 0.15,
            'response_time_warning': 5.0,
            'response_time_critical': 10.0
        }
        self.system_health = {
            'overall': 'healthy',
            'components': {},
            'last_check': None,
            'issues': []
        }
    
    async def start_monitoring(self):
        """Start the monitoring service"""
        enhanced_logger.info("Starting monitoring service")
        self.running = True
        
        # Start background monitoring tasks
        asyncio.create_task(self._system_monitoring_loop())
        asyncio.create_task(self._health_check_loop())
        asyncio.create_task(self._performance_analysis_loop())
        asyncio.create_task(self._alert_management_loop())
    
    async def stop_monitoring(self):
        """Stop the monitoring service"""
        enhanced_logger.info("Stopping monitoring service")
        self.running = False
    
    async def _system_monitoring_loop(self):
        """Main system monitoring loop"""
        while self.running:
            try:
                # Collect system metrics
                await self._collect_system_metrics()
                
                # Check system health
                await self._check_system_health()
                
                # Sleep until next iteration
                await asyncio.sleep(self.monitoring_interval)
                
            except Exception as e:
                enhanced_logger.error(f"Error in system monitoring loop: {str(e)}")
                await asyncio.sleep(10)  # Brief pause on error
    
    async def _collect_system_metrics(self):
        """Collect system-level metrics"""
        try:
            # CPU and memory usage
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            # Network I/O
            network = psutil.net_io_counters()
            
            # Process information
            process = psutil.Process()
            process_memory = process.memory_info()
            
            # Get queue statistics
            queue_size = 0
            processing_count = 0
            try:
                queue_size = await redis_queue.get_queue_size()
                processing_count = await redis_queue.get_processing_count()
            except:
                pass  # Redis might not be available
            
            # Count active workers (simplified - in production, use service discovery)
            active_workers = processing_count  # Approximate
            
            # Create system metric
            system_metric = SystemMetric(
                timestamp=datetime.now(),
                cpu_usage=cpu_percent / 100.0,
                memory_usage=memory.percent / 100.0,
                queue_size=queue_size,
                processing_count=processing_count,
                active_workers=active_workers
            )
            
            # Record the metric
            await metrics_collector.record_system_metric(system_metric)
            
            # Log important metrics
            enhanced_logger.log_performance_metric("cpu_usage", cpu_percent)
            enhanced_logger.log_performance_metric("memory_usage", memory.percent)
            enhanced_logger.log_performance_metric("queue_size", queue_size)
            
            # Check for immediate alerts
            await self._check_immediate_alerts(system_metric)
            
        except Exception as e:
            enhanced_logger.error(f"Error collecting system metrics: {str(e)}")
    
    async def _check_immediate_alerts(self, metric: SystemMetric):
        """Check for immediate system alerts"""
        alerts = []
        
        # CPU alerts
        if metric.cpu_usage > self.alert_thresholds['cpu_critical']:
            alerts.append({
                'type': 'cpu_critical',
                'message': f"Critical CPU usage: {metric.cpu_usage:.1%}",
                'severity': 'critical',
                'value': metric.cpu_usage
            })
        elif metric.cpu_usage > self.alert_thresholds['cpu_warning']:
            alerts.append({
                'type': 'cpu_warning',
                'message': f"High CPU usage: {metric.cpu_usage:.1%}",
                'severity': 'warning',
                'value': metric.cpu_usage
            })
        
        # Memory alerts
        if metric.memory_usage > self.alert_thresholds['memory_critical']:
            alerts.append({
                'type': 'memory_critical',
                'message': f"Critical memory usage: {metric.memory_usage:.1%}",
                'severity': 'critical',
                'value': metric.memory_usage
            })
        elif metric.memory_usage > self.alert_thresholds['memory_warning']:
            alerts.append({
                'type': 'memory_warning',
                'message': f"High memory usage: {metric.memory_usage:.1%}",
                'severity': 'warning',
                'value': metric.memory_usage
            })
        
        # Queue size alerts
        if metric.queue_size > self.alert_thresholds['queue_size_critical']:
            alerts.append({
                'type': 'queue_critical',
                'message': f"Critical queue size: {metric.queue_size} tasks",
                'severity': 'critical',
                'value': metric.queue_size
            })
        elif metric.queue_size > self.alert_thresholds['queue_size_warning']:
            alerts.append({
                'type': 'queue_warning',
                'message': f"Large queue size: {metric.queue_size} tasks",
                'severity': 'warning',
                'value': metric.queue_size
            })
        
        # Log alerts
        for alert in alerts:
            if alert['severity'] == 'critical':
                enhanced_logger.critical(f"ALERT: {alert['message']}", **alert)
            else:
                enhanced_logger.warning(f"ALERT: {alert['message']}", **alert)
    
    async def _health_check_loop(self):
        """Health check loop for system components"""
        while self.running:
            try:
                await self._perform_health_checks()
                await asyncio.sleep(30)  # Health checks every 30 seconds
            except Exception as e:
                enhanced_logger.error(f"Error in health check loop: {str(e)}")
                await asyncio.sleep(10)
    
    async def _perform_health_checks(self):
        """Perform health checks on all system components"""
        health_status = {}
        issues = []
        
        # Check Redis connection
        redis_health = await self._check_redis_health()
        health_status['redis'] = redis_health
        if redis_health['status'] != 'healthy':
            issues.append(f"Redis: {redis_health['message']}")
        
        # Check database connection
        db_health = await self._check_database_health()
        health_status['database'] = db_health
        if db_health['status'] != 'healthy':
            issues.append(f"Database: {db_health['message']}")
        
        # Check API responsiveness
        api_health = await self._check_api_health()
        health_status['api'] = api_health
        if api_health['status'] != 'healthy':
            issues.append(f"API: {api_health['message']}")
        
        # Check worker availability
        worker_health = await self._check_worker_health()
        health_status['workers'] = worker_health
        if worker_health['status'] != 'healthy':
            issues.append(f"Workers: {worker_health['message']}")
        
        # Update overall system health
        overall_status = 'healthy'
        if any(status['status'] == 'critical' for status in health_status.values()):
            overall_status = 'critical'
        elif any(status['status'] == 'warning' for status in health_status.values()):
            overall_status = 'warning'
        
        self.system_health = {
            'overall': overall_status,
            'components': health_status,
            'last_check': datetime.now().isoformat(),
            'issues': issues
        }
        
        # Log health status
        if overall_status != 'healthy':
            enhanced_logger.warning(f"System health: {overall_status}", issues=issues)
        else:
            enhanced_logger.info("System health: healthy")
    
    async def _check_redis_health(self) -> Dict[str, Any]:
        """Check Redis health"""
        try:
            start_time = time.time()
            await redis_queue.redis_client.ping()
            response_time = (time.time() - start_time) * 1000  # milliseconds
            
            if response_time > 1000:  # 1 second
                return {
                    'status': 'warning',
                    'message': f'Slow Redis response: {response_time:.1f}ms',
                    'response_time_ms': response_time
                }
            
            return {
                'status': 'healthy',
                'message': 'Redis responding normally',
                'response_time_ms': response_time
            }
        except Exception as e:
            return {
                'status': 'critical',
                'message': f'Redis connection failed: {str(e)}',
                'error': str(e)
            }
    
    async def _check_database_health(self) -> Dict[str, Any]:
        """Check database health"""
        try:
            start_time = time.time()
            # Simple database query
            await task_queue.get_task(999999)  # This will return None but test connection
            response_time = (time.time() - start_time) * 1000
            
            if response_time > 2000:  # 2 seconds
                return {
                    'status': 'warning',
                    'message': f'Slow database response: {response_time:.1f}ms',
                    'response_time_ms': response_time
                }
            
            return {
                'status': 'healthy',
                'message': 'Database responding normally',
                'response_time_ms': response_time
            }
        except Exception as e:
            return {
                'status': 'critical',
                'message': f'Database connection failed: {str(e)}',
                'error': str(e)
            }
    
    async def _check_api_health(self) -> Dict[str, Any]:
        """Check API health (simplified - in production, use actual HTTP check)"""
        try:
            # This would normally make an HTTP request to the API
            # For now, we'll just check if the process is running
            return {
                'status': 'healthy',
                'message': 'API is running'
            }
        except Exception as e:
            return {
                'status': 'critical',
                'message': f'API health check failed: {str(e)}',
                'error': str(e)
            }
    
    async def _check_worker_health(self) -> Dict[str, Any]:
        """Check worker health"""
        try:
            processing_count = await redis_queue.get_processing_count()
            
            if processing_count == 0:
                return {
                    'status': 'warning',
                    'message': 'No active workers detected',
                    'active_workers': 0
                }
            
            return {
                'status': 'healthy',
                'message': f'{processing_count} active workers',
                'active_workers': processing_count
            }
        except Exception as e:
            return {
                'status': 'critical',
                'message': f'Worker health check failed: {str(e)}',
                'error': str(e)
            }
    
    async def _performance_analysis_loop(self):
        """Performance analysis loop"""
        while self.running:
            try:
                await self._analyze_performance_trends()
                await asyncio.sleep(300)  # Every 5 minutes
            except Exception as e:
                enhanced_logger.error(f"Error in performance analysis: {str(e)}")
                await asyncio.sleep(60)
    
    async def _analyze_performance_trends(self):
        """Analyze performance trends and generate insights"""
        try:
            # Get task type statistics
            task_stats = metrics_collector.get_task_type_stats()
            
            for task_type, stats in task_stats.items():
                # Check for performance degradation
                if stats['avg_execution_time'] > 30:  # 30 seconds threshold
                    enhanced_logger.warning(
                        f"Performance degradation detected for {task_type}",
                        task_type=task_type,
                        avg_execution_time=stats['avg_execution_time']
                    )
                
                # Check for high failure rates
                if stats.get('failure_rate', 0) > 0.1:  # 10% failure rate
                    enhanced_logger.warning(
                        f"High failure rate for {task_type}",
                        task_type=task_type,
                        failure_rate=stats.get('failure_rate', 0)
                    )
            
            # Analyze system metrics trends
            system_summary = metrics_collector.get_system_metrics_summary(60)  # Last hour
            
            if system_summary:
                avg_cpu = system_summary.get('avg_cpu_usage', 0)
                avg_memory = system_summary.get('avg_memory_usage', 0)
                
                if avg_cpu > 0.8:  # 80% average CPU
                    enhanced_logger.warning(
                        "High average CPU usage detected",
                        avg_cpu_usage=avg_cpu
                    )
                
                if avg_memory > 0.85:  # 85% average memory
                    enhanced_logger.warning(
                        "High average memory usage detected",
                        avg_memory_usage=avg_memory
                    )
        
        except Exception as e:
            enhanced_logger.error(f"Error in performance analysis: {str(e)}")
    
    async def _alert_management_loop(self):
        """Alert management and cleanup loop"""
        while self.running:
            try:
                await self._cleanup_old_alerts()
                await asyncio.sleep(3600)  # Every hour
            except Exception as e:
                enhanced_logger.error(f"Error in alert management: {str(e)}")
                await asyncio.sleep(300)
    
    async def _cleanup_old_alerts(self):
        """Clean up old alerts and metrics"""
        try:
            # Clean old metrics
            cleared = metrics_collector.clear_old_metrics(days=7)
            enhanced_logger.info("Cleaned up old metrics", **cleared)
            
        except Exception as e:
            enhanced_logger.error(f"Error cleaning up old alerts: {str(e)}")
    
    def get_system_health(self) -> Dict[str, Any]:
        """Get current system health status"""
        return self.system_health.copy()
    
    def get_monitoring_dashboard(self) -> Dict[str, Any]:
        """Get comprehensive monitoring dashboard data"""
        return {
            'system_health': self.get_system_health(),
            'task_statistics': metrics_collector.get_task_type_stats(),
            'system_metrics': metrics_collector.get_system_metrics_summary(60),
            'recent_alerts': metrics_collector.get_recent_alerts(60),
            'error_patterns': metrics_collector.get_error_patterns(),
            'performance_trends': {
                task_type: metrics_collector.get_performance_trends(task_type)
                for task_type in ['text_processing', 'ai_summarization', 'batch_processing', 'image_processing']
            },
            'monitoring_info': {
                'monitoring_interval': self.monitoring_interval,
                'alert_thresholds': self.alert_thresholds,
                'last_update': datetime.now().isoformat()
            }
        }
    
    def get_alert_thresholds(self) -> Dict[str, float]:
        """Get current alert thresholds"""
        return self.alert_thresholds.copy()
    
    def update_alert_thresholds(self, **thresholds):
        """Update alert thresholds"""
        for key, value in thresholds.items():
            if key in self.alert_thresholds:
                old_value = self.alert_thresholds[key]
                self.alert_thresholds[key] = value
                enhanced_logger.info(f"Updated alert threshold {key}: {old_value} -> {value}")
            else:
                enhanced_logger.warning(f"Unknown alert threshold: {key}")


# Global monitoring service instance
monitoring_service = MonitoringService()
