"""Database connection and query utilities."""

from __future__ import annotations

import logging
import os
from typing import Any, Optional

import aiomysql

from wp_mcp.config import config

logger = logging.getLogger(__name__)


class Database:
    """MySQL/MariaDB database connection manager."""

    def __init__(self) -> None:
        """Initialize database connection pool."""
        self.pool: Optional[aiomysql.Pool] = None

    async def connect(self) -> None:
        """Create database connection pool."""
        if self.pool is not None:
            return

        try:
            self.pool = await aiomysql.create_pool(
                host=os.getenv("MYSQL_HOST", "mariadb"),
                port=int(os.getenv("MYSQL_PORT", "3306")),
                user=os.getenv("MYSQL_USER", "wpuser"),
                password=os.getenv("MYSQL_PASSWORD", "wppassword"),
                db=os.getenv("MYSQL_DATABASE", "wordpress"),
                charset="utf8mb4",
                autocommit=True,
                minsize=config.db_pool_minsize,
                maxsize=config.db_pool_maxsize,
                pool_recycle=3600,  # Recycle connections after 1 hour
                connect_timeout=config.db_pool_timeout,
            )
            logger.info(
                "Database connection pool created (min=%d, max=%d)",
                config.db_pool_minsize,
                config.db_pool_maxsize,
            )
        except Exception as e:
            logger.error("Failed to create database connection pool: %s", e)
            self.pool = None

    async def disconnect(self) -> None:
        """Close database connection pool."""
        if self.pool:
            self.pool.close()
            await self.pool.wait_closed()
            self.pool = None
            logger.info("Database connection pool closed")

    async def _ensure_connection(self) -> None:
        """Ensure database connection is available.

        Raises:
            RuntimeError: If connection cannot be established
        """
        if not self.pool:
            await self.connect()

        if not self.pool:
            raise RuntimeError("Database connection not available")

    async def execute(self, query: str, params: tuple = ()) -> int:
        """Execute a query (INSERT, UPDATE, DELETE).

        Args:
            query: SQL query string
            params: Query parameters

        Returns:
            Number of affected rows
        """
        await self._ensure_connection()
        assert self.pool is not None  # Guaranteed by _ensure_connection

        async with self.pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(query, params)
                return cursor.rowcount

    async def fetchone(self, query: str, params: tuple = ()) -> Optional[dict[str, Any]]:
        """Fetch a single row.

        Args:
            query: SQL query string
            params: Query parameters

        Returns:
            Row as dict or None
        """
        await self._ensure_connection()
        assert self.pool is not None  # Guaranteed by _ensure_connection

        async with self.pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                await cursor.execute(query, params)
                return await cursor.fetchone()

    async def fetchall(self, query: str, params: tuple = ()) -> list[dict[str, Any]]:
        """Fetch all rows.

        Args:
            query: SQL query string
            params: Query parameters

        Returns:
            List of rows as dicts
        """
        await self._ensure_connection()
        assert self.pool is not None  # Guaranteed by _ensure_connection

        async with self.pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                await cursor.execute(query, params)
                return await cursor.fetchall()

    async def insert(self, query: str, params: tuple = ()) -> int:
        """Execute INSERT and return the last inserted ID.

        Args:
            query: SQL INSERT query
            params: Query parameters

        Returns:
            Last inserted ID
        """
        await self._ensure_connection()
        assert self.pool is not None  # Guaranteed by _ensure_connection

        async with self.pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(query, params)
                return cursor.lastrowid


# Global database instance
db = Database()
