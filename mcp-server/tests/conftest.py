"""Pytest configuration and shared fixtures."""

import asyncio
import os
import pytest


# Set test environment variables
os.environ["MYSQL_HOST"] = os.getenv("MYSQL_HOST", "localhost")
os.environ["MYSQL_PORT"] = os.getenv("MYSQL_PORT", "3306")
os.environ["MYSQL_USER"] = os.getenv("MYSQL_USER", "wpuser")
os.environ["MYSQL_PASSWORD"] = os.getenv("MYSQL_PASSWORD", "wppassword")
os.environ["MYSQL_DATABASE"] = os.getenv("MYSQL_DATABASE", "wordpress")
os.environ["ENCRYPTION_KEY"] = os.getenv("ENCRYPTION_KEY", "test_key_for_testing_only_32bytes!")


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()
