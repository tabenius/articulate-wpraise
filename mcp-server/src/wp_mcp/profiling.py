"""MCP function profiling and performance monitoring."""

from __future__ import annotations

import functools
import logging
import sys
import time
from typing import Any, Callable, Optional
import asyncio

from wp_mcp.database import db

logger = logging.getLogger(__name__)


class MCPProfiler:
    """Profile MCP function performance and store metrics."""

    @staticmethod
    async def record_execution(
        user_id: int,
        organization_id: Optional[int],
        connection_id: Optional[int],
        function_name: str,
        execution_time_ms: float,
        cpu_time_ms: float,
        memory_mb: Optional[float] = None,
        args_size_bytes: Optional[int] = None,
        result_size_bytes: Optional[int] = None,
        success: bool = True,
        error_message: Optional[str] = None,
    ) -> None:
        """Record function execution metrics to database.

        Args:
            user_id: User who triggered the function
            organization_id: Organization context (if any)
            connection_id: WordPress connection used (if any)
            function_name: Name of the MCP function
            execution_time_ms: Total wall clock time in milliseconds
            cpu_time_ms: CPU time in milliseconds
            memory_mb: Memory usage in MB (if available)
            args_size_bytes: Size of arguments in bytes
            result_size_bytes: Size of result in bytes
            success: Whether function succeeded
            error_message: Error message if failed
        """
        io_time_ms = max(0, execution_time_ms - cpu_time_ms)

        # TODO: Implement async database profiling storage
        # For now, just log metrics
        logger.info(
            f"Profiling: {function_name} - "
            f"exec={execution_time_ms:.2f}ms cpu={cpu_time_ms:.2f}ms "
            f"io={io_time_ms:.2f}ms success={success}"
        )

    @staticmethod
    async def _update_stats(
        organization_id: Optional[int],
        function_name: str,
        execution_time_ms: float,
        success: bool,
    ) -> None:
        """Update aggregated statistics."""
        # TODO: Implement async database stats storage
        pass


def profile_mcp_function(
    enabled: bool = True,
    track_memory: bool = False,
    track_size: bool = False,
):
    """Decorator to profile MCP function execution.

    Args:
        enabled: Whether profiling is enabled for this function
        track_memory: Whether to track memory usage (more overhead)
        track_size: Whether to track argument/result sizes

    Usage:
        @profile_mcp_function(enabled=True, track_memory=True)
        async def my_expensive_function(...):
            ...
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            if not enabled:
                return await func(*args, **kwargs)

            # Extract context information
            context = kwargs.get("context", {})
            user_id = context.get("user_id")
            organization_id = context.get("organization_id")
            connection_id = context.get("connection_id")

            if not user_id:
                # No user context, skip profiling
                return await func(*args, **kwargs)

            # Measure execution time
            start_wall = time.perf_counter()
            start_cpu = time.process_time()

            # Track memory if requested
            memory_before = None
            if track_memory:
                try:
                    import psutil
                    import os

                    process = psutil.Process(os.getpid())
                    memory_before = process.memory_info().rss / (1024 * 1024)  # MB
                except ImportError:
                    pass

            # Track argument size if requested
            args_size = None
            if track_size:
                try:
                    import sys

                    args_size = sys.getsizeof(args) + sys.getsizeof(kwargs)
                except (TypeError, AttributeError) as e:
                    logger.debug(f"Failed to measure argument size: {e}")
                    pass

            # Execute function
            success = True
            error_message = None
            result = None

            try:
                result = await func(*args, **kwargs)
                return result
            except Exception as e:
                success = False
                error_message = str(e)
                raise
            finally:
                # Measure times
                end_wall = time.perf_counter()
                end_cpu = time.process_time()

                execution_time_ms = (end_wall - start_wall) * 1000
                cpu_time_ms = (end_cpu - start_cpu) * 1000

                # Track memory if requested
                memory_mb = None
                if track_memory and memory_before is not None:
                    try:
                        import psutil
                        import os

                        process = psutil.Process(os.getpid())
                        memory_after = process.memory_info().rss / (1024 * 1024)
                        memory_mb = memory_after - memory_before
                    except (ImportError, psutil.Error) as e:
                        logger.debug(f"Failed to measure memory: {e}")
                        pass

                # Track result size if requested
                result_size = None
                if track_size and result is not None:
                    try:
                        result_size = sys.getsizeof(result)
                    except (TypeError, AttributeError) as e:
                        logger.debug(f"Failed to measure result size: {e}")
                        pass

                # Record profiling data (async, don't block)
                try:
                    asyncio.create_task(
                        MCPProfiler.record_execution(
                            user_id=user_id,
                            organization_id=organization_id,
                            connection_id=connection_id,
                            function_name=func.__name__,
                            execution_time_ms=execution_time_ms,
                            cpu_time_ms=cpu_time_ms,
                            memory_mb=memory_mb,
                            args_size_bytes=args_size,
                            result_size_bytes=result_size,
                            success=success,
                            error_message=error_message,
                        )
                    )
                except Exception as e:
                    logger.error(f"Failed to create profiling task: {e}")

        return wrapper

    return decorator


async def get_profiling_stats(
    organization_id: Optional[int] = None,
    function_name: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = 100,
) -> list[dict[str, Any]]:
    """Get profiling statistics.

    Args:
        organization_id: Filter by organization
        function_name: Filter by function name
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
        limit: Maximum number of results

    Returns:
        List of profiling statistics
    """
    # TODO: Implement async database query for profiling stats
    return []
