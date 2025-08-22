import logging
import sys
import json
import time
from datetime import datetime
from contextlib import contextmanager
from core.config import settings


class JSONFormatter(logging.Formatter):
    """Custom JSON formatter for structured logging."""
    
    def format(self, record):
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
        
        # Add extra fields if present
        if hasattr(record, 'extra_fields'):
            log_entry.update(record.extra_fields)
        
        return json.dumps(log_entry)


class SafeLogger:
    """Logger wrapper that sanitizes sensitive data."""
    
    def __init__(self, logger: logging.Logger):
        self.logger = logger
    
    def _sanitize_message(self, message: str) -> str:
        """Sanitize message if needed."""
        if not settings.log_sensitive_data and settings.sanitize_logs:
            from core.security import InputValidator
            return InputValidator.sanitize_for_logging(message)
        return message
    
    def info(self, message: str, **kwargs):
        sanitized = self._sanitize_message(message)
        self.logger.info(sanitized, extra={'extra_fields': kwargs} if kwargs else None)
    
    def error(self, message: str, **kwargs):
        sanitized = self._sanitize_message(message)
        self.logger.error(sanitized, extra={'extra_fields': kwargs} if kwargs else None)
    
    def warning(self, message: str, **kwargs):
        sanitized = self._sanitize_message(message)
        self.logger.warning(sanitized, extra={'extra_fields': kwargs} if kwargs else None)
    
    def debug(self, message: str, **kwargs):
        sanitized = self._sanitize_message(message)
        self.logger.debug(sanitized, extra={'extra_fields': kwargs} if kwargs else None)


def setup_logging():
    """Setup application logging configuration."""
    # Determine log level
    log_level = logging.INFO
    if hasattr(settings, 'log_level'):
        log_level = getattr(logging, settings.log_level.upper(), logging.INFO)
    
    # Create formatters
    json_formatter = JSONFormatter()
    console_formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    # Setup root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # Clear existing handlers
    root_logger.handlers.clear()
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    
    # Use JSON formatter in production-like environments
    if hasattr(settings, 'environment') and settings.environment == 'production':
        console_handler.setFormatter(json_formatter)
    else:
        console_handler.setFormatter(console_formatter)
    
    root_logger.addHandler(console_handler)
    
    # Reduce noise from third-party libraries
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sentence_transformers").setLevel(logging.WARNING)
    logging.getLogger("transformers").setLevel(logging.WARNING)
    logging.getLogger("torch").setLevel(logging.WARNING)


def get_logger(name: str) -> SafeLogger:
    """Get a safe logger instance."""
    if not logging.getLogger().handlers:
        setup_logging()
    
    return SafeLogger(logging.getLogger(name))


# Performance monitoring
class PerformanceMonitor:
    """Simple performance monitoring."""
    
    def __init__(self):
        self.metrics = {}
        self.counters = {}
    
    def record_duration(self, operation: str, duration: float):
        """Record operation duration."""
        if operation not in self.metrics:
            self.metrics[operation] = []
        self.metrics[operation].append(duration)
        
        # Keep only last 1000 measurements
        if len(self.metrics[operation]) > 1000:
            self.metrics[operation] = self.metrics[operation][-1000:]
    
    def increment_counter(self, counter: str):
        """Increment a counter."""
        self.counters[counter] = self.counters.get(counter, 0) + 1
    
    def get_stats(self) -> dict:
        """Get performance statistics."""
        stats = {}
        
        for operation, durations in self.metrics.items():
            if durations:
                stats[operation] = {
                    "count": len(durations),
                    "avg_duration": sum(durations) / len(durations),
                    "min_duration": min(durations),
                    "max_duration": max(durations),
                }
        
        stats["counters"] = self.counters.copy()
        return stats


# Global performance monitor
perf_monitor = PerformanceMonitor()


# Context manager for timing operations
@contextmanager
def time_operation(operation_name: str):
    """Context manager to time operations."""
    start_time = time.time()
    try:
        yield
    finally:
        duration = time.time() - start_time
        perf_monitor.record_duration(operation_name, duration)


# Initialize logging
setup_logging()
