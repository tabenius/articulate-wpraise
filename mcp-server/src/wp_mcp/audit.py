"""Audit logging for security events."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from wp_mcp.database import db

logger = logging.getLogger(__name__)


class EventCategory(str, Enum):
    """Audit event categories."""

    AUTH = "auth"
    ACCESS = "access"
    DATA = "data"
    SECURITY = "security"
    SYSTEM = "system"


class Severity(str, Enum):
    """Event severity levels."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AuditLog:
    """Audit logging service for tracking security events."""

    @staticmethod
    async def log_event(
        event_type: str,
        category: EventCategory = EventCategory.SECURITY,
        severity: Severity = Severity.INFO,
        user_id: int | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        resource_type: str | None = None,
        resource_id: str | None = None,
        action: str | None = None,
        status: str | None = None,
        message: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> int:
        """Log an audit event.

        Args:
            event_type: Type of event (e.g., "login", "logout", "rate_limit")
            category: Event category
            severity: Event severity level
            user_id: User ID associated with event
            ip_address: Client IP address
            user_agent: Client user agent string
            resource_type: Type of resource accessed (e.g., "post", "connection")
            resource_id: ID of resource accessed
            action: Action performed (e.g., "create", "update", "delete")
            status: Event status (e.g., "success", "failure")
            message: Human-readable event description
            metadata: Additional structured data

        Returns:
            Audit log entry ID
        """
        try:
            # Serialize metadata to JSON
            metadata_json = json.dumps(metadata) if metadata else None

            # Insert audit log entry
            result = await db.execute(
                """
                INSERT INTO wp_audit_log (
                    event_type, event_category, severity,
                    user_id, ip_address, user_agent,
                    resource_type, resource_id, action, status,
                    message, metadata
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    event_type,
                    category.value,
                    severity.value,
                    user_id,
                    ip_address,
                    user_agent,
                    resource_type,
                    resource_id,
                    action,
                    status,
                    message,
                    metadata_json,
                ),
            )

            log_id = result

            # Also log to application logger for real-time monitoring
            log_level = {
                Severity.INFO: logging.INFO,
                Severity.WARNING: logging.WARNING,
                Severity.ERROR: logging.ERROR,
                Severity.CRITICAL: logging.CRITICAL,
            }[severity]

            logger.log(
                log_level,
                "Audit: %s [%s] user=%s ip=%s resource=%s/%s status=%s",
                event_type,
                category.value,
                user_id or "anonymous",
                ip_address or "unknown",
                resource_type or "-",
                resource_id or "-",
                status or "-",
                extra={"audit_id": log_id, "metadata": metadata},
            )

            return log_id

        except Exception as e:
            logger.error("Failed to log audit event: %s", e)
            # Don't fail the request if audit logging fails
            return 0

    @staticmethod
    async def log_auth_event(
        event_type: str,
        status: str,
        user_id: int | None = None,
        email: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        message: str | None = None,
    ) -> int:
        """Log authentication event (login, logout, register)."""
        severity = Severity.INFO if status == "success" else Severity.WARNING

        return await AuditLog.log_event(
            event_type=event_type,
            category=EventCategory.AUTH,
            severity=severity,
            user_id=user_id,
            ip_address=ip_address,
            user_agent=user_agent,
            action=event_type,
            status=status,
            message=message,
            metadata={"email": email} if email else None,
        )

    @staticmethod
    async def log_rate_limit_event(
        user_id: int | None,
        endpoint: str,
        ip_address: str | None = None,
        limit: int | None = None,
        retry_after: int | None = None,
    ) -> int:
        """Log rate limit violation."""
        return await AuditLog.log_event(
            event_type="rate_limit_exceeded",
            category=EventCategory.SECURITY,
            severity=Severity.WARNING,
            user_id=user_id,
            ip_address=ip_address,
            resource_type="endpoint",
            resource_id=endpoint,
            action="access",
            status="blocked",
            message=f"Rate limit exceeded for {endpoint}",
            metadata={"limit": limit, "retry_after": retry_after},
        )

    @staticmethod
    async def log_access_denied(
        user_id: int | None,
        resource_type: str,
        resource_id: str | None,
        reason: str,
        ip_address: str | None = None,
    ) -> int:
        """Log access denied event."""
        return await AuditLog.log_event(
            event_type="access_denied",
            category=EventCategory.ACCESS,
            severity=Severity.WARNING,
            user_id=user_id,
            ip_address=ip_address,
            resource_type=resource_type,
            resource_id=resource_id,
            action="access",
            status="denied",
            message=f"Access denied: {reason}",
            metadata={"reason": reason},
        )

    @staticmethod
    async def log_data_change(
        user_id: int,
        resource_type: str,
        resource_id: str,
        action: str,
        ip_address: str | None = None,
        changes: dict[str, Any] | None = None,
    ) -> int:
        """Log data modification event (create, update, delete)."""
        return await AuditLog.log_event(
            event_type=f"{resource_type}_{action}",
            category=EventCategory.DATA,
            severity=Severity.INFO,
            user_id=user_id,
            ip_address=ip_address,
            resource_type=resource_type,
            resource_id=resource_id,
            action=action,
            status="success",
            message=f"{action.capitalize()}d {resource_type} {resource_id}",
            metadata=changes,
        )

    @staticmethod
    async def get_recent_events(
        limit: int = 100,
        user_id: int | None = None,
        event_type: str | None = None,
        severity: Severity | None = None,
        category: EventCategory | None = None,
    ) -> list[dict[str, Any]]:
        """Get recent audit log entries.

        Args:
            limit: Maximum number of entries to return
            user_id: Filter by user ID
            event_type: Filter by event type
            severity: Filter by severity level
            category: Filter by event category

        Returns:
            List of audit log entries
        """
        query = "SELECT * FROM wp_audit_log WHERE 1=1"
        params: list[Any] = []

        if user_id is not None:
            query += " AND user_id = %s"
            params.append(user_id)

        if event_type:
            query += " AND event_type = %s"
            params.append(event_type)

        if severity:
            query += " AND severity = %s"
            params.append(severity.value)

        if category:
            query += " AND event_category = %s"
            params.append(category.value)

        query += " ORDER BY created_at DESC LIMIT %s"
        params.append(limit)

        results = await db.fetchall(query, tuple(params))

        # Parse JSON metadata
        for result in results:
            if result.get("metadata"):
                try:
                    result["metadata"] = json.loads(result["metadata"])
                except Exception:
                    pass

        return results

    @staticmethod
    async def get_security_summary(hours: int = 24) -> dict[str, Any]:
        """Get security event summary for the last N hours.

        Args:
            hours: Number of hours to look back

        Returns:
            Summary statistics
        """
        # Total events by severity
        severity_counts = await db.fetchall(
            """
            SELECT severity, COUNT(*) as count
            FROM wp_audit_log
            WHERE created_at >= DATE_SUB(NOW(), INTERVAL %s HOUR)
            GROUP BY severity
            """,
            (hours,),
        )

        # Failed auth attempts
        failed_auth = await db.fetchone(
            """
            SELECT COUNT(*) as count
            FROM wp_audit_log
            WHERE created_at >= DATE_SUB(NOW(), INTERVAL %s HOUR)
            AND event_category = 'auth'
            AND status = 'failure'
            """,
            (hours,),
        )

        # Rate limit violations
        rate_limits = await db.fetchone(
            """
            SELECT COUNT(*) as count
            FROM wp_audit_log
            WHERE created_at >= DATE_SUB(NOW(), INTERVAL %s HOUR)
            AND event_type = 'rate_limit_exceeded'
            """,
            (hours,),
        )

        # Access denied events
        access_denied = await db.fetchone(
            """
            SELECT COUNT(*) as count
            FROM wp_audit_log
            WHERE created_at >= DATE_SUB(NOW(), INTERVAL %s HOUR)
            AND event_type = 'access_denied'
            """,
            (hours,),
        )

        # Top IP addresses with security events
        top_ips = await db.fetchall(
            """
            SELECT ip_address, COUNT(*) as count
            FROM wp_audit_log
            WHERE created_at >= DATE_SUB(NOW(), INTERVAL %s HOUR)
            AND severity IN ('warning', 'error', 'critical')
            AND ip_address IS NOT NULL
            GROUP BY ip_address
            ORDER BY count DESC
            LIMIT 10
            """,
            (hours,),
        )

        return {
            "period_hours": hours,
            "severity_counts": {row["severity"]: row["count"] for row in severity_counts},
            "failed_auth_attempts": failed_auth["count"] if failed_auth else 0,
            "rate_limit_violations": rate_limits["count"] if rate_limits else 0,
            "access_denied_events": access_denied["count"] if access_denied else 0,
            "top_ips": [
                {"ip": row["ip_address"], "events": row["count"]} for row in top_ips
            ],
        }
