"""Pytest configuration and shared fixtures."""

import asyncio
import os
import socket

import pytest


# Set test environment variables
os.environ["MYSQL_HOST"] = os.getenv("MYSQL_HOST", "localhost")
os.environ["MYSQL_PORT"] = os.getenv("MYSQL_PORT", "3306")
os.environ["MYSQL_USER"] = os.getenv("MYSQL_USER", "wpuser")
os.environ["MYSQL_PASSWORD"] = os.getenv("MYSQL_PASSWORD", "wppassword")
os.environ["MYSQL_DATABASE"] = os.getenv("MYSQL_DATABASE", "wordpress")
os.environ["ENCRYPTION_KEY"] = os.getenv("ENCRYPTION_KEY", "pUhZBBsCbHu_7am0tWVYDXMgbIgpHUa_RQkZMsNG-3o=")


def _db_available() -> bool:
    """Check if MariaDB/MySQL is reachable."""
    host = os.environ.get("MYSQL_HOST", "localhost")
    port = int(os.environ.get("MYSQL_PORT", "3306"))
    try:
        with socket.create_connection((host, port), timeout=1):
            return True
    except OSError:
        return False


requires_db = pytest.mark.skipif(
    not _db_available(),
    reason="MariaDB not available (run inside Docker or port-forward 3306)",
)


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()
