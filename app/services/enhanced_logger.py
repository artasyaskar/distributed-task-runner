import logging
import json
import sys
import time
import traceback
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path
from enum import Enum
from app.core.config import settings


class LogLevel(Enum):
    """Log levels with numeric values"""
    DEBUG = 10
    INFO = 20
    WARNING = 30
    ERROR = 40
    CRITICAL = 50


class LogFormat(Enum):
    """Available log formats"""
    SIMPLE = "simple"
    DETAILED = "detailed"
    JSON = "json"
    STRUCTURED = "structured"


class EnhancedLogger:
    """Enhanced logging system with structured output and correlation"""
    
    def __init__(self, name: str = "distributed-task-system"):
        self.name = name
        self.logger = logging.getLogger(name)
        self.loggers = {}  # Additional loggers for different components
        self.log_files = {}  # File handlers for different log types
        self.correlation_context = {}  # Request/task correlation
        
        # Configuration
        self.log_level = LogLevel.DEBUG if settings.debug else LogLevel.INFO
        self.log_format = LogFormat.DETAILED
        self.log_directory = Path("logs")
        self.max_file_size = 10 * 1024 * 1024  # 10MB
        self.backup_count = 5
        
        # Ensure log directory exists
        self.log_directory.mkdir(exist_ok=True)
        
        # Setup logging
        self._setup_logging()
    
    def _setup_logging(self):
        """Setup enhanced logging configuration"""
        # Clear existing handlers
        self.logger.handlers.clear()
        
        # Set log level
        self.logger.setLevel(self.log_level.value)
        
        # Create formatters
        formatters = {
            LogFormat.SIMPLE: logging.Formatter(
                '%(asctime)s - %(levelname)s - %(message)s'
            ),
            LogFormat.DETAILED: logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(module)s:%(funcName)s:%(lineno)d - %(message)s'
            ),
            LogFormat.JSON: self._create_json_formatter(),
            LogFormat.STRUCTURED: self._create_structured_formatter()
        }
        
        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatters[self.log_format])
        console_handler.setLevel(self.log_level.value)
        self.logger.addHandler(console_handler)
        
        # File handlers for different log types
        self._setup_file_handlers(formatters)
        
        # Setup component-specific loggers
        self._setup_component_loggers(formatters)
    
    def _create_json_formatter(self):
        """Create JSON formatter for structured logging"""
        class JSONFormatter(logging.Formatter):
            def format(self, record):
                log_entry = {
                    'timestamp': datetime.fromtimestamp(record.created).isoformat(),
                    'level': record.levelname,
                    'logger': record.name,
                    'module': record.module,
                    'function': record.funcName,
                    'line': record.lineno,
                    'message': record.getMessage(),
                    'thread': record.thread,
                    'process': record.process
                }
                
                # Add exception info if present
                if record.exc_info:
                    log_entry['exception'] = self.formatException(record.exc_info)
                
                # Add correlation context if available
                if hasattr(record, 'correlation_id'):
                    log_entry['correlation_id'] = record.correlation_id
                if hasattr(record, 'task_id'):
                    log_entry['task_id'] = record.task_id
                if hasattr(record, 'worker_id'):
                    log_entry['worker_id'] = record.worker_id
                
                return json.dumps(log_entry)
        
        return JSONFormatter()
    
    def _create_structured_formatter(self):
        """Create structured formatter with key-value pairs"""
        class StructuredFormatter(logging.Formatter):
            def format(self, record):
                parts = [
                    f"time={datetime.fromtimestamp(record.created).isoformat()}",
                    f"level={record.levelname}",
                    f"logger={record.name}",
                    f"msg=\"{record.getMessage()}\""
                ]
                
                # Add correlation context
                if hasattr(record, 'correlation_id'):
                    parts.append(f"correlation_id={record.correlation_id}")
                if hasattr(record, 'task_id'):
                    parts.append(f"task_id={record.task_id}")
                if hasattr(record, 'worker_id'):
                    parts.append(f"worker_id={record.worker_id}")
                
                return " ".join(parts)
        
        return StructuredFormatter()
    
    def _setup_file_handlers(self, formatters):
        """Setup file handlers for different log types"""
        log_types = {
            'app': 'application.log',
            'tasks': 'tasks.log',
            'errors': 'errors.log',
            'performance': 'performance.log',
            'audit': 'audit.log'
        }
        
        for log_type, filename in log_types.items():
            file_path = self.log_directory / filename
            
            # Create rotating file handler
            from logging.handlers import RotatingFileHandler
            handler = RotatingFileHandler(
                file_path,
                maxBytes=self.max_file_size,
                backupCount=self.backup_count
            )
            
            # Use JSON format for structured analysis
            if log_type == 'performance' or log_type == 'audit':
                handler.setFormatter(formatters[LogFormat.JSON])
            else:
                handler.setFormatter(formatters[LogFormat.DETAILED])
            
            # Set level (errors get higher threshold)
            if log_type == 'errors':
                handler.setLevel(LogLevel.ERROR.value)
            else:
                handler.setLevel(self.log_level.value)
            
            self.logger.addHandler(handler)
            self.log_files[log_type] = handler
    
    def _setup_component_loggers(self, formatters):
        """Setup loggers for different components"""
        components = ['api', 'worker', 'queue', 'executor', 'retry']
        
        for component in components:
            logger_name = f"{self.name}.{component}"
            component_logger = logging.getLogger(logger_name)
            component_logger.setLevel(self.log_level.value)
            
            # Add component-specific file handler
            file_path = self.log_directory / f"{component}.log"
            from logging.handlers import RotatingFileHandler
            handler = RotatingFileHandler(
                file_path,
                maxBytes=self.max_file_size,
                backupCount=self.backup_count
            )
            handler.setFormatter(formatters[LogFormat.JSON])
            handler.setLevel(self.log_level.value)
            
            component_logger.addHandler(handler)
            component_logger.addHandler(logging.StreamHandler(sys.stdout))  # Also to console
            
            self.loggers[component] = component_logger
    
    def set_correlation_context(self, **context):
        """Set correlation context for current operation"""
        self.correlation_context.update(context)
    
    def clear_correlation_context(self):
        """Clear correlation context"""
        self.correlation_context.clear()
    
    def _log_with_context(self, level: LogLevel, message: str, **kwargs):
        """Log message with correlation context"""
        # Create log record with extra context
        extra = {}
        
        # Add correlation context
        if 'correlation_id' in self.correlation_context:
            extra['correlation_id'] = self.correlation_context['correlation_id']
        if 'task_id' in self.correlation_context:
            extra['task_id'] = self.correlation_context['task_id']
        if 'worker_id' in self.correlation_context:
            extra['worker_id'] = self.correlation_context['worker_id']
        
        # Add any additional context
        extra.update(kwargs)
        
        # Log the message
        self.logger.log(level.value, message, extra=extra)
    
    def debug(self, message: str, **kwargs):
        """Log debug message"""
        self._log_with_context(LogLevel.DEBUG, message, **kwargs)
    
    def info(self, message: str, **kwargs):
        """Log info message"""
        self._log_with_context(LogLevel.INFO, message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        """Log warning message"""
        self._log_with_context(LogLevel.WARNING, message, **kwargs)
    
    def error(self, message: str, **kwargs):
        """Log error message"""
        self._log_with_context(LogLevel.ERROR, message, **kwargs)
    
    def critical(self, message: str, **kwargs):
        """Log critical message"""
        self._log_with_context(LogLevel.CRITICAL, message, **kwargs)
    
    def log_task_event(self, task_id: int, event: str, **kwargs):
        """Log task-specific event"""
        self.set_correlation_context(task_id=task_id)
        message = f"Task {task_id}: {event}"
        
        if event in ['created', 'queued', 'started']:
            self.info(message, **kwargs)
        elif event in ['completed', 'success']:
            self.info(message, **kwargs)
        elif event in ['failed', 'error', 'retry']:
            self.error(message, **kwargs)
        else:
            self.info(message, **kwargs)
        
        self.clear_correlation_context()
    
    def log_worker_event(self, worker_id: str, event: str, **kwargs):
        """Log worker-specific event"""
        self.set_correlation_context(worker_id=worker_id)
        message = f"Worker {worker_id}: {event}"
        
        if event in ['started', 'connected', 'ready']:
            self.info(message, **kwargs)
        elif event in ['stopped', 'disconnected', 'error']:
            self.warning(message, **kwargs)
        else:
            self.info(message, **kwargs)
        
        self.clear_correlation_context()
    
    def log_performance_metric(self, metric_name: str, value: float, **kwargs):
        """Log performance metric"""
        message = f"Performance: {metric_name}={value}"
        self.info(message, metric_name=metric_name, value=value, **kwargs)
    
    def log_api_request(self, method: str, endpoint: str, status_code: int, 
                       duration: float, **kwargs):
        """Log API request"""
        message = f"API {method} {endpoint} -> {status_code} ({duration:.3f}s)"
        
        # Determine log level based on status code
        if status_code >= 500:
            self.error(message, method=method, endpoint=endpoint, 
                     status_code=status_code, duration=duration, **kwargs)
        elif status_code >= 400:
            self.warning(message, method=method, endpoint=endpoint,
                       status_code=status_code, duration=duration, **kwargs)
        else:
            self.info(message, method=method, endpoint=endpoint,
                    status_code=status_code, duration=duration, **kwargs)
    
    def log_system_event(self, event: str, **kwargs):
        """Log system-level event"""
        message = f"System: {event}"
        self.info(message, **kwargs)
    
    def get_component_logger(self, component: str):
        """Get logger for specific component"""
        return self.loggers.get(component, self.logger)
    
    def set_log_level(self, level: LogLevel):
        """Set log level for all loggers"""
        self.log_level = level
        self.logger.setLevel(level.value)
        
        for component_logger in self.loggers.values():
            component_logger.setLevel(level.value)
    
    def get_log_stats(self) -> Dict[str, Any]:
        """Get logging statistics"""
        return {
            'log_level': self.log_level.name,
            'log_format': self.log_format.value,
            'log_directory': str(self.log_directory),
            'active_handlers': len(self.logger.handlers),
            'component_loggers': list(self.loggers.keys()),
            'log_files': {name: str(handler.baseFilename) 
                         for name, handler in self.log_files.items()}
        }


# Global enhanced logger instance
enhanced_logger = EnhancedLogger()
