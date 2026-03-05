import asyncio
import time
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass
from enum import Enum
from app.core.logging import logger
from app.services.worker_pool import worker_pool
from app.services.redis_queue import redis_queue
from app.services.metrics_collector import metrics_collector


class ScalingPolicy(Enum):
    """Auto-scaling policies"""
    QUEUE_BASED = "queue_based"
    CPU_BASED = "cpu_based"
    MEMORY_BASED = "memory_based"
    CUSTOM = "custom"
    PREDICTIVE = "predictive"


class ScalingDirection(Enum):
    """Scaling direction"""
    UP = "up"
    DOWN = "down"
    NONE = "none"


@dataclass
class ScalingEvent:
    """Individual scaling event"""
    timestamp: float
    direction: ScalingDirection
    from_workers: int
    to_workers: int
    reason: str
    metrics: Dict[str, float]
    policy: ScalingPolicy


@dataclass
class ScalingRule:
    """Auto-scaling rule definition"""
    name: str
    policy: ScalingPolicy
    scale_up_condition: str
    scale_down_condition: str
    cooldown_period: int
    max_scale_up_step: int
    max_scale_down_step: int
    enabled: bool = True


class AutoScaler:
    """Advanced auto-scaling system with multiple policies and predictive capabilities"""
    
    def __init__(self):
        self.enabled = True
        self.current_policy = ScalingPolicy.QUEUE_BASED
        self.scaling_history: List[ScalingEvent] = []
        self.rules: Dict[str, ScalingRule] = {}
        
        # Predictive scaling
        self.prediction_window = 300  # 5 minutes
        self.historical_data: List[Dict[str, Any]] = []
        self.max_historical_size = 1000
        
        # Scaling limits and safety
        self.max_scale_up_per_minute = 5
        self.max_scale_down_per_minute = 3
        self.scale_events_per_minute = 0
        self.last_scale_event_time = 0
        
        # Custom scaling functions
        self.custom_scale_functions: Dict[str, Callable] = {}
        
        # Initialize default rules
        self._initialize_default_rules()
    
    def _initialize_default_rules(self):
        """Initialize default scaling rules"""
        self.rules["queue_based"] = ScalingRule(
            name="queue_based",
            policy=ScalingPolicy.QUEUE_BASED,
            scale_up_condition="queue_size > 5 and avg_task_time < 10",
            scale_down_condition="queue_size < 2 and idle_workers > 2",
            cooldown_period=60,
            max_scale_up_step=3,
            max_scale_down_step=2
        )
        
        self.rules["cpu_based"] = ScalingRule(
            name="cpu_based",
            policy=ScalingPolicy.CPU_BASED,
            scale_up_condition="avg_cpu > 0.7 and queue_size > 3",
            scale_down_condition="avg_cpu < 0.3 and queue_size < 1",
            cooldown_period=120,
            max_scale_up_step=2,
            max_scale_down_step=1
        )
        
        self.rules["memory_based"] = ScalingRule(
            name="memory_based",
            policy=ScalingPolicy.MEMORY_BASED,
            scale_up_condition="avg_memory > 0.8",
            scale_down_condition="avg_memory < 0.5",
            cooldown_period=180,
            max_scale_up_step=2,
            max_scale_down_step=1
        )
    
    async def start(self):
        """Start the auto-scaler"""
        logger.info("Starting auto-scaler")
        
        # Start background tasks
        asyncio.create_task(self._scaling_loop())
        asyncio.create_task(self._predictive_analysis_loop())
        asyncio.create_task(self._metrics_collection_loop())
        
        logger.info("Auto-scaler started")
    
    async def stop(self):
        """Stop the auto-scaler"""
        logger.info("Stopping auto-scaler")
        self.enabled = False
        logger.info("Auto-scaler stopped")
    
    async def _scaling_loop(self):
        """Main scaling decision loop"""
        while self.enabled:
            try:
                # Get current metrics
                metrics = await self._collect_current_metrics()
                
                # Make scaling decision
                decision = await self._make_scaling_decision(metrics)
                
                if decision["should_scale"]:
                    await self._execute_scaling(decision, metrics)
                
                # Sleep before next iteration
                await asyncio.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                logger.error(f"Error in scaling loop: {str(e)}")
                await asyncio.sleep(10)
    
    async def _collect_current_metrics(self) -> Dict[str, Any]:
        """Collect current system metrics"""
        metrics = {}
        
        # Queue metrics
        try:
            metrics["queue_size"] = await redis_queue.get_queue_size()
            metrics["processing_count"] = await redis_queue.get_processing_count()
        except:
            metrics["queue_size"] = 0
            metrics["processing_count"] = 0
        
        # System metrics
        try:
            system_metrics = metrics_collector.get_system_metrics_summary(5)  # Last 5 minutes
            if system_metrics:
                metrics["avg_cpu"] = system_metrics.get("avg_cpu_usage", 0)
                metrics["avg_memory"] = system_metrics.get("avg_memory_usage", 0)
                metrics["max_cpu"] = system_metrics.get("max_cpu_usage", 0)
                metrics["max_memory"] = system_metrics.get("max_memory_usage", 0)
        except:
            metrics["avg_cpu"] = 0
            metrics["avg_memory"] = 0
            metrics["max_cpu"] = 0
            metrics["max_memory"] = 0
        
        # Worker metrics
        pool_status = worker_pool.get_pool_status()
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
    
    async def _make_scaling_decision(self, metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Make scaling decision based on current policy"""
        if not self.enabled:
            return {"should_scale": False, "reason": "Auto-scaler disabled"}
        
        # Get current rule
        rule = self.rules.get(self.current_policy.value)
        if not rule or not rule.enabled:
            return {"should_scale": False, "reason": f"Rule {self.current_policy.value} not enabled"}
        
        # Check cooldown
        current_time = time.time()
        if current_time - self.last_scale_event_time < rule.cooldown_period:
            return {"should_scale": False, "reason": "In cooldown period"}
        
        # Check rate limits
        if current_time - self.last_scale_event_time < 60:
            if self.scale_events_per_minute >= self.max_scale_up_per_minute:
                return {"should_scale": False, "reason": "Max scale events per minute exceeded"}
        
        # Evaluate conditions
        scale_up = await self._evaluate_condition(rule.scale_up_condition, metrics)
        scale_down = await self._evaluate_condition(rule.scale_down_condition, metrics)
        
        if scale_up and scale_down:
            return {"should_scale": False, "reason": "Conflicting scaling conditions"}
        elif scale_up:
            return {
                "should_scale": True,
                "direction": ScalingDirection.UP,
                "reason": rule.scale_up_condition,
                "max_step": rule.max_scale_up_step
            }
        elif scale_down:
            return {
                "should_scale": True,
                "direction": ScalingDirection.DOWN,
                "reason": rule.scale_down_condition,
                "max_step": rule.max_scale_down_step
            }
        else:
            return {"should_scale": False, "reason": "No scaling conditions met"}
    
    async def _evaluate_condition(self, condition: str, metrics: Dict[str, Any]) -> bool:
        """Evaluate a scaling condition"""
        try:
            # Simple condition evaluation (in production, use a proper expression parser)
            if "queue_size" in condition:
                queue_size = metrics.get("queue_size", 0)
                if "> 5" in condition and queue_size > 5:
                    return True
                if "< 2" in condition and queue_size < 2:
                    return True
            
            if "avg_cpu" in condition:
                avg_cpu = metrics.get("avg_cpu", 0)
                if "> 0.7" in condition and avg_cpu > 0.7:
                    return True
                if "< 0.3" in condition and avg_cpu < 0.3:
                    return True
            
            if "avg_memory" in condition:
                avg_memory = metrics.get("avg_memory", 0)
                if "> 0.8" in condition and avg_memory > 0.8:
                    return True
                if "< 0.5" in condition and avg_memory < 0.5:
                    return True
            
            if "avg_task_time" in condition:
                avg_task_time = metrics.get("avg_task_time", 0)
                if "< 10" in condition and avg_task_time < 10:
                    return True
            
            if "idle_workers" in condition:
                idle_workers = metrics.get("idle_workers", 0)
                if "> 2" in condition and idle_workers > 2:
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error evaluating condition '{condition}': {str(e)}")
            return False
    
    async def _execute_scaling(self, decision: Dict[str, Any], metrics: Dict[str, Any]):
        """Execute scaling decision"""
        current_workers = metrics["current_workers"]
        direction = decision["direction"]
        max_step = decision["max_step"]
        
        if direction == ScalingDirection.UP:
            # Scale up
            new_workers = min(current_workers + max_step, worker_pool.max_workers)
            await worker_pool._scale_to_workers(new_workers)
            
            # Record scaling event
            event = ScalingEvent(
                timestamp=time.time(),
                direction=direction,
                from_workers=current_workers,
                to_workers=new_workers,
                reason=decision["reason"],
                metrics=metrics,
                policy=self.current_policy
            )
            self.scaling_history.append(event)
            
            # Update rate limiting
            self.last_scale_event_time = time.time()
            self.scale_events_per_minute += 1
            
            logger.info(f"Scaled UP from {current_workers} to {new_workers} workers: {decision['reason']}")
            
        elif direction == ScalingDirection.DOWN:
            # Scale down
            new_workers = max(current_workers - max_step, worker_pool.min_workers)
            await worker_pool._scale_to_workers(new_workers)
            
            # Record scaling event
            event = ScalingEvent(
                timestamp=time.time(),
                direction=direction,
                from_workers=current_workers,
                to_workers=new_workers,
                reason=decision["reason"],
                metrics=metrics,
                policy=self.current_policy
            )
            self.scaling_history.append(event)
            
            # Update rate limiting
            self.last_scale_event_time = time.time()
            self.scale_events_per_minute += 1
            
            logger.info(f"Scaled DOWN from {current_workers} to {new_workers} workers: {decision['reason']}")
    
    async def _predictive_analysis_loop(self):
        """Predictive scaling analysis"""
        while self.enabled:
            try:
                if self.current_policy == ScalingPolicy.PREDICTIVE:
                    await self._predictive_scaling()
                
                await asyncio.sleep(300)  # Analyze every 5 minutes
                
            except Exception as e:
                logger.error(f"Error in predictive analysis: {str(e)}")
                await asyncio.sleep(60)
    
    async def _predictive_scaling(self):
        """Predictive scaling based on historical patterns"""
        if len(self.historical_data) < 10:
            return  # Not enough data for prediction
        
        # Simple prediction: if queue size is trending up, pre-scale
        recent_data = self.historical_data[-5:]  # Last 5 data points
        queue_trend = self._calculate_trend([d["queue_size"] for d in recent_data])
        
        if queue_trend > 0.5:  # Strong upward trend
            current_workers = worker_pool.get_pool_status()["total_workers"]
            if current_workers < worker_pool.max_workers:
                new_workers = min(current_workers + 1, worker_pool.max_workers)
                await worker_pool._scale_to_workers(new_workers)
                logger.info(f"Predictive scaling UP to {new_workers} workers (queue trend: {queue_trend:.2f})")
    
    def _calculate_trend(self, values: List[float]) -> float:
        """Calculate trend (simple linear regression slope)"""
        if len(values) < 2:
            return 0.0
        
        n = len(values)
        x = list(range(n))
        sum_x = sum(x)
        sum_y = sum(values)
        sum_xy = sum(x[i] * values[i] for i in range(n))
        sum_x2 = sum(x[i] ** 2 for i in range(n))
        
        # Calculate slope
        slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x ** 2)
        return slope
    
    async def _metrics_collection_loop(self):
        """Collect metrics for predictive analysis"""
        while self.enabled:
            try:
                metrics = await self._collect_current_metrics()
                metrics["timestamp"] = time.time()
                
                # Add to historical data
                self.historical_data.append(metrics)
                
                # Limit historical data size
                if len(self.historical_data) > self.max_historical_size:
                    self.historical_data.pop(0)
                
                # Reset rate limiting counter every minute
                current_time = time.time()
                if current_time - self.last_scale_event_time > 60:
                    self.scale_events_per_minute = 0
                
                await asyncio.sleep(60)  # Collect every minute
                
            except Exception as e:
                logger.error(f"Error in metrics collection: {str(e)}")
                await asyncio.sleep(30)
    
    def get_scaling_status(self) -> Dict[str, Any]:
        """Get current scaling status"""
        return {
            "enabled": self.enabled,
            "current_policy": self.current_policy.value,
            "total_scaling_events": len(self.scaling_history),
            "recent_events": [
                {
                    "timestamp": event.timestamp,
                    "direction": event.direction.value,
                    "from_workers": event.from_workers,
                    "to_workers": event.to_workers,
                    "reason": event.reason,
                    "policy": event.policy.value
                }
                for event in self.scaling_history[-10:]  # Last 10 events
            ],
            "rules": {
                name: {
                    "enabled": rule.enabled,
                    "policy": rule.policy.value,
                    "cooldown": rule.cooldown_period
                }
                for name, rule in self.rules.items()
            },
            "metrics_collected": len(self.historical_data),
            "scale_events_per_minute": self.scale_events_per_minute
        }
    
    async def set_policy(self, policy: ScalingPolicy):
        """Set scaling policy"""
        self.current_policy = policy
        logger.info(f"Scaling policy set to {policy.value}")
    
    async def add_custom_rule(self, rule: ScalingRule):
        """Add custom scaling rule"""
        self.rules[rule.name] = rule
        logger.info(f"Added custom scaling rule: {rule.name}")
    
    async def enable_rule(self, rule_name: str):
        """Enable a scaling rule"""
        if rule_name in self.rules:
            self.rules[rule_name].enabled = True
            logger.info(f"Enabled scaling rule: {rule_name}")
    
    async def disable_rule(self, rule_name: str):
        """Disable a scaling rule"""
        if rule_name in self.rules:
            self.rules[rule_name].enabled = False
            logger.info(f"Disabled scaling rule: {rule_name}")


# Global auto-scaler instance
auto_scaler = AutoScaler()
