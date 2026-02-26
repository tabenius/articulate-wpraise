"""MCP function profiling and performance monitoring."""

from __future__ import annotations

import functools
import logging
import sys
import time
from typing import Any, Callable, Optional
import asyncio

from articulate_mcp.database import db

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

        try:
            await db.execute(
                """
                INSERT INTO articulate_mcp_profiling (
                    user_id,
                    organization_id,
                    connection_id,
                    function_name,
                    execution_time_ms,
                    cpu_time_ms,
                    io_time_ms,
                    memory_mb,
                    args_size_bytes,
                    result_size_bytes,
                    success,
                    error_message
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                )
                """,
                (
                    user_id,
                    organization_id,
                    connection_id,
                    function_name,
                    execution_time_ms,
                    cpu_time_ms,
                    io_time_ms,
                    memory_mb,
                    args_size_bytes,
                    result_size_bytes,
                    success,
                    error_message,
                ),
            )

            # Update aggregated stats
            await MCPProfiler._update_stats(
                organization_id, function_name, execution_time_ms, success
            )

        except Exception as e:
            logger.error(f"Failed to record profiling data: {e}")
            # Don't fail the actual function call due to profiling errors

    @staticmethod
    async def _update_stats(
        organization_id: Optional[int],
        function_name: str,
        execution_time_ms: float,
        success: bool,
    ) -> None:
        """Update aggregated statistics."""
        try:
            await db.execute(
                """
                INSERT INTO articulate_mcp_profiling_stats (
                    organization_id,
                    function_name,
                    date,
                    call_count,
                    total_time_ms,
                    avg_time_ms,
                    min_time_ms,
                    max_time_ms,
                    success_count,
                    error_count
                ) VALUES (
                    %s, %s, CURDATE(),
                    1,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s
                )
                ON DUPLICATE KEY UPDATE
                    call_count = call_count + 1,
                    total_time_ms = total_time_ms + %s,
                    avg_time_ms = (total_time_ms + %s) / (call_count + 1),
                    min_time_ms = LEAST(min_time_ms, %s),
                    max_time_ms = GREATEST(max_time_ms, %s),
                    success_count = success_count + %s,
                    error_count = error_count + %s
                """,
                (
                    organization_id,
                    function_name,
                    execution_time_ms,
                    execution_time_ms,
                    execution_time_ms,
                    execution_time_ms,
                    1 if success else 0,
                    0 if success else 1,
                    execution_time_ms,
                    execution_time_ms,
                    execution_time_ms,
                    execution_time_ms,
                    1 if success else 0,
                    0 if success else 1,
                ),
            )

        except Exception as e:
            logger.error(f"Failed to update profiling stats: {e}")


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
    conditions = []
    params = []

    if organization_id:
        conditions.append("organization_id = %s")
        params.append(organization_id)

    if function_name:
        conditions.append("function_name = %s")
        params.append(function_name)

    if start_date:
        conditions.append("date >= %s")
        params.append(start_date)

    if end_date:
        conditions.append("date <= %s")
        params.append(end_date)

    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    params.append(limit)

    query = f"""
        SELECT
            function_name,
            date,
            call_count,
            avg_time_ms,
            min_time_ms,
            max_time_ms,
            p95_time_ms,
            p99_time_ms,
            success_count,
            error_count
        FROM articulate_mcp_profiling_stats
        {where_clause}
        ORDER BY date DESC, avg_time_ms DESC
        LIMIT %s
    """

    results = await db.fetchall(query, tuple(params))

    return [
        {
            "function_name": row["function_name"],
            "date": str(row["date"]),
            "call_count": row["call_count"],
            "avg_time_ms": float(row["avg_time_ms"]),
            "min_time_ms": float(row["min_time_ms"]),
            "max_time_ms": float(row["max_time_ms"]),
            "p95_time_ms": float(row["p95_time_ms"]) if row["p95_time_ms"] else None,
            "p99_time_ms": float(row["p99_time_ms"]) if row["p99_time_ms"] else None,
            "success_count": row["success_count"],
            "error_count": row["error_count"],
        }
        for row in results
    ]
