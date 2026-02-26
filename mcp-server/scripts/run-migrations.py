#!/usr/bin/env python3
"""
Database Migration Runner for WP-AI

Applies SQL migrations from mcp-server/migrations/ directory.
Tracks applied migrations in the database.
"""

import os
import sys
import logging
from pathlib import Path

# Add parent directory to path to import articulate_mcp
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import pymysql


def get_connection():
    """Get synchronous database connection for migrations"""
    return pymysql.connect(
        host=os.getenv("MYSQL_HOST", "mariadb"),
        port=int(os.getenv("MYSQL_PORT", "3306")),
        user=os.getenv("MYSQL_USER", "wpuser"),
        password=os.getenv("MYSQL_PASSWORD", "wppassword"),
        database=os.getenv("MYSQL_DATABASE", "wordpress"),
        charset="utf8mb4",
        autocommit=False,
    )

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def create_migrations_table():
    """Create table to track applied migrations"""
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                id INT AUTO_INCREMENT PRIMARY KEY,
                migration_name VARCHAR(255) NOT NULL UNIQUE,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_migration_name (migration_name)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """
        )
        conn.commit()
        logger.info("Migrations tracking table ready")
    finally:
        cursor.close()


def get_applied_migrations():
    """Get list of already applied migrations"""
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT migration_name FROM schema_migrations ORDER BY id")
        return {row[0] for row in cursor.fetchall()}
    finally:
        cursor.close()


def apply_migration(migration_file: Path):
    """Apply a single migration file"""
    migration_name = migration_file.name

    logger.info(f"Applying migration: {migration_name}")

    # Read SQL file
    sql = migration_file.read_text()

    conn = get_connection()
    cursor = conn.cursor()

    try:
        # Execute each statement (split by semicolon)
        for statement in sql.split(";"):
            statement = statement.strip()
            if statement:
                cursor.execute(statement)

        # Record migration as applied
        cursor.execute(
            "INSERT INTO schema_migrations (migration_name) VALUES (%s)",
            (migration_name,),
        )

        conn.commit()
        logger.info(f"✓ Applied: {migration_name}")

    except Exception as e:
        conn.rollback()
        logger.error(f"✗ Failed to apply {migration_name}: {e}")
        raise
    finally:
        cursor.close()


def run_migrations():
    """Run all pending migrations"""
    # Find migrations directory
    migrations_dir = Path(__file__).parent.parent / "migrations"

    if not migrations_dir.exists():
        logger.error(f"Migrations directory not found: {migrations_dir}")
        return

    # Ensure tracking table exists
    create_migrations_table()

    # Get applied migrations
    applied = get_applied_migrations()
    logger.info(f"Already applied: {len(applied)} migrations")

    # Get all migration files
    migration_files = sorted(migrations_dir.glob("*.sql"))

    if not migration_files:
        logger.info("No migration files found")
        return

    # Apply pending migrations
    pending = [f for f in migration_files if f.name not in applied]

    if not pending:
        logger.info("No pending migrations")
        return

    logger.info(f"Pending migrations: {len(pending)}")

    for migration_file in pending:
        apply_migration(migration_file)

    logger.info(f"✓ All migrations applied successfully!")


if __name__ == "__main__":
    try:
        run_migrations()
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        sys.exit(1)
