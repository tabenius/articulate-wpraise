"""Pytest configuration and shared fixtures."""

import os
import socket
import subprocess

import pytest


def _discover_db_host() -> str:
    """Find a reachable MariaDB host.

    Priority:
      1. MYSQL_HOST env var (if already set explicitly)
      2. localhost:3306 (port-forwarded or local install)
      3. Docker container IP of articulate-db
    """
    explicit = os.getenv("MYSQL_HOST")
    if explicit:
        return explicit

    # Try localhost first
    try:
        with socket.create_connection(("localhost", 3306), timeout=1):
            return "localhost"
    except OSError:
        pass

    # Try to get the Docker container IP
    try:
        result = subprocess.run(
            ["docker", "inspect", "articulate-db",
             "--format", "{{range .NetworkSettings.Networks}}{{.IPAddress}} {{end}}"],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0:
            ip = result.stdout.strip().split()[0]
            with socket.create_connection((ip, 3306), timeout=1):
                return ip
    except (OSError, subprocess.TimeoutExpired, IndexError):
        pass

    return "localhost"  # fallback, will fail gracefully


_db_host = _discover_db_host()

# Set test environment variables
os.environ["MYSQL_HOST"] = _db_host
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
async def setup_db():
    """Session-scoped DB connection shared across all test files.

    This avoids the issue where per-file setup_db fixtures disconnect
    the global db singleton, preventing subsequent files from reconnecting.
    """
    from articulate_mcp.database import db

    await db.connect()
    yield
    await db.disconnect()
