"""JSON serialization utilities for datetime and other non-JSON types."""

from __future__ import annotations

import json
from datetime import date, datetime
from decimal import Decimal
from typing import Any


def json_serializer(obj: Any) -> str:
    """Serialize objects to JSON-compatible format.

    Args:
        obj: Object to serialize

    Returns:
        JSON-serializable representation

    Raises:
        TypeError: If object type is not supported
    """
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, date):
        return obj.isoformat()
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, bytes):
        return obj.decode("utf-8", errors="replace")

    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")


def serialize_to_json(data: Any) -> str:
    """Serialize data to JSON string with datetime support.

    Args:
        data: Data to serialize (dict, list, or primitive)

    Returns:
        JSON string
    """
    return json.dumps(data, default=json_serializer, ensure_ascii=False)


def sanitize_for_json(data: Any) -> Any:
    """Recursively convert datetime objects to ISO strings for JSON serialization.

    Args:
        data: Data structure (dict, list, or primitive)

    Returns:
        Sanitized data with datetime objects converted to strings
    """
    if isinstance(data, dict):
        return {key: sanitize_for_json(value) for key, value in data.items()}
    elif isinstance(data, list):
        return [sanitize_for_json(item) for item in data]
    elif isinstance(data, (datetime, date)):
        return data.isoformat()
    elif isinstance(data, Decimal):
        return float(data)
    elif isinstance(data, bytes):
        return data.decode("utf-8", errors="replace")
    else:
        return data
