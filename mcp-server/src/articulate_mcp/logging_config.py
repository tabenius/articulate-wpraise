"""Structured logging configuration for WP-MCP server."""

from __future__ import annotations

import json
import logging
import sys
import time
from datetime import datetime, timezone
from typing import Any


class StructuredFormatter(logging.Formatter):
    """JSON formatter for structured logging."""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON.

        Args:
            record: Log record to format

        Returns:
            JSON string
        """
        log_data: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # Add extra fields from record
        if hasattr(record, "user_id"):
            log_data["user_id"] = record.user_id
        if hasattr(record, "request_id"):
            log_data["request_id"] = record.request_id
        if hasattr(record, "duration_ms"):
            log_data["duration_ms"] = record.duration_ms
        if hasattr(record, "tool_name"):
            log_data["tool_name"] = record.tool_name
        if hasattr(record, "query_type"):
            log_data["query_type"] = record.query_type
        if hasattr(record, "cache_hit"):
            log_data["cache_hit"] = record.cache_hit

        # Add source location
        log_data["source"] = {
            "file": record.pathname,
            "line": record.lineno,
            "function": record.funcName,
        }

        return json.dumps(log_data)


class HumanReadableFormatter(logging.Formatter):
    """Human-readable colored formatter for development."""

    # ANSI color codes
    COLORS = {
        "DEBUG": "\033[36m",  # Cyan
        "INFO": "\033[32m",  # Green
        "WARNING": "\033[33m",  # Yellow
        "ERROR": "\033[31m",  # Red
        "CRITICAL": "\033[35m",  # Magenta
        "RESET": "\033[0m",
    }

    def format(self, record: logging.LogRecord) -> str:
        """Format log record with colors.

        Args:
            record: Log record to format

        Returns:
            Colored string
        """
        color = self.COLORS.get(record.levelname, "")
        reset = self.COLORS["RESET"]

        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        level = f"{color}[{record.levelname}]{reset}"
        logger = record.name
        message = record.getMessage()

        # Build base message
        log_line = f"{timestamp} {level} {logger}: {message}"

        # Add extra context if available
        extras = []
        if hasattr(record, "method") and hasattr(record, "path"):
            extras.append(f"{record.method} {record.path}")
        if hasattr(record, "status_code"):
            extras.append(f"status={record.status_code}")
        if hasattr(record, "duration_ms"):
            extras.append(f"duration={record.duration_ms}ms")
        if hasattr(record, "user_id"):
            extras.append(f"user={record.user_id}")
        if hasattr(record, "client_ip"):
            extras.append(f"ip={record.client_ip}")
        if hasattr(record, "tool_name"):
            extras.append(f"tool={record.tool_name}")
        if hasattr(record, "cache_hit"):
            extras.append(f"cache={'HIT' if record.cache_hit else 'MISS'}")

        if extras:
            log_line += f" ({', '.join(extras)})"

        # Add exception if present
        if record.exc_info:
            log_line += f"\n{self.formatException(record.exc_info)}"

        return log_line


def configure_logging(json_format: bool = False, log_level: str = "INFO"):
    """Configure structured logging for the application.

    Args:
        json_format: If True, use JSON format. If False, use human-readable format
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    # Determine formatter based on environment
    formatter: logging.Formatter
    if json_format:
        formatter = StructuredFormatter()
    else:
        formatter = HumanReadableFormatter()

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))

    # Remove existing handlers
    root_logger.handlers.clear()

    # Add stderr handler
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(formatter)
    root_logger.addHandler(handler)

    # Silence noisy loggers
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)


class PerformanceLogger:
    """Context manager for logging operation performance."""

    def __init__(self, logger: logging.Logger, operation: str, **extra):
        """Initialize performance logger.

        Args:
            logger: Logger instance
            operation: Operation name
            **extra: Extra fields to log
        """
        self.logger = logger
        self.operation = operation
        self.extra = extra
        self.start_time: float | None = None

    def __enter__(self):
        """Start timing."""
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Log completion with duration."""
        if self.start_time is not None:
            duration_ms = int((time.time() - self.start_time) * 1000)

            log_data = {
                "duration_ms": duration_ms,
                "operation": self.operation,
                **self.extra,
            }

            if exc_type is None:
                self.logger.info(
                    f"{self.operation} completed",
                    extra=log_data,
                )
            else:
                log_data["error"] = str(exc_val)
                self.logger.error(
                    f"{self.operation} failed",
                    extra=log_data,
                    exc_info=True,
                )


# Metrics collection (in-memory for now, could be exported to Prometheus)
class Metrics:
    """Simple in-memory metrics collector."""

    def __init__(self):
        self._counters: dict[str, int] = {}
        self._histograms: dict[str, list[float]] = {}

    def increment(self, metric: str, value: int = 1):
        """Increment a counter metric."""
        self._counters[metric] = self._counters.get(metric, 0) + value

    def record(self, metric: str, value: float):
        """Record a histogram value."""
        if metric not in self._histograms:
            self._histograms[metric] = []
        self._histograms[metric].append(value)

    def get_stats(self) -> dict[str, Any]:
        """Get current metrics statistics."""
        stats: dict[str, Any] = {"counters": self._counters}

        # Calculate histogram statistics
        histograms = {}
        for metric, values in self._histograms.items():
            if values:
                sorted_values = sorted(values)
                count = len(values)
                histograms[metric] = {
                    "count": count,
                    "min": min(values),
                    "max": max(values),
                    "avg": sum(values) / count,
                    "p50": sorted_values[count // 2],
                    "p95": sorted_values[int(count * 0.95)],
                    "p99": sorted_values[int(count * 0.99)],
                }

        stats["histograms"] = histograms
        return stats

    def reset(self):
        """Reset all metrics."""
        self._counters.clear()
        self._histograms.clear()


# Global metrics instance
metrics = Metrics()
