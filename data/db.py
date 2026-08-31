import os
import sqlite3
import logging
from contextlib import contextmanager
from typing import Optional, List, Tuple, Any, Generator
from .migrations import MigrationRunner, run_migrations

logger = logging.getLogger(__name__)


class DatabaseManager:
    """
    SQLite Database Manager handling connections, transactions, queries, and migrations.
    """

    _instance: Optional["DatabaseManager"] = None

    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize database manager.
        Default path resolves to ./data/store.db.
        """
        if db_path is None:
            # Default to store.db in the data folder
            base_dir = os.path.dirname(os.path.abspath(__file__))
            self.db_path = os.path.join(base_dir, "store.db")
        else:
            self.db_path = os.path.abspath(db_path)

        self._ensure_db_directory()
        logger.info(f"DatabaseManager initialized for: {self.db_path}")

    @classmethod
    def get_instance(cls, db_path: Optional[str] = None) -> "DatabaseManager":
        """Singleton instance accessor."""
        if cls._instance is None:
            cls._instance = DatabaseManager(db_path)
        return cls._instance

    def _ensure_db_directory(self) -> None:
        """Ensure the directory containing the database file exists."""
        db_dir = os.path.dirname(self.db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)
            logger.info(f"Created directory: {db_dir}")

    @contextmanager
    def get_connection(self) -> Generator[sqlite3.Connection, None, None]:
        """
        Context manager for acquiring a database connection.
        Ensures foreign keys are enabled and rows are accessible by column name.
        Commits on success and rolls back on exception.
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Database transaction error: {e}")
            raise
        finally:
            conn.close()

    def test_connection(self) -> bool:
        """Test if database is reachable and can execute simple query."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT 1;")
                row = cursor.fetchone()
                return row is not None and row[0] == 1
        except Exception as e:
            logger.error(f"Database connection test failed: {e}")
            return False

    def init_database(self) -> None:
        """Initialize database by applying schema and pending migrations."""
        self._ensure_db_directory()
        runner = MigrationRunner(self.db_path)
        runner.run()

    def execute_query(self, query: str, params: Tuple[Any, ...] = ()) -> List[sqlite3.Row]:
        """Execute a read query and return all results."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            return cursor.fetchall()

    def execute_one(self, query: str, params: Tuple[Any, ...] = ()) -> Optional[sqlite3.Row]:
        """Execute a read query and return single result or None."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            return cursor.fetchone()

    def execute_update(self, query: str, params: Tuple[Any, ...] = ()) -> int:
        """Execute INSERT/UPDATE/DELETE query and return rowcount or lastrowid."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            return cursor.lastrowid or cursor.rowcount

    def get_table_names(self) -> List[str]:
        """Return list of all non-system tables in the database."""
        query = "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name ASC;"
        rows = self.execute_query(query)
        return [row["name"] for row in rows]


def get_db(db_path: Optional[str] = None) -> DatabaseManager:
    """Convenience helper to retrieve DatabaseManager singleton."""
    return DatabaseManager.get_instance(db_path)
