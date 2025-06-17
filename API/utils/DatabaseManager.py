import sqlite3
import threading
import time
from contextlib import contextmanager
from typing import Any, Dict, List, Optional, Tuple
import logging
import config

logger = logging.getLogger(__name__)


class DatabaseManager:
    """
    Thread-safe database manager with connection pooling and transaction support.
    
    This class provides:
    - Thread-local connections (one connection per thread)
    - Automatic retry logic for database locks
    - Transaction support with context managers
    - Common query methods for simplified database operations
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        """Singleton pattern to ensure only one DatabaseManager instance exists."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(DatabaseManager, cls).__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """Initialize the DatabaseManager with thread-local storage."""
        if self._initialized:
            return
            
        self.db_path = config.DATABASE_PATH
        self._local = threading.local()
        self._retry_attempts = 3
        self._retry_delay = 0.1  # seconds
        self._initialized = True
    
    def _get_connection(self) -> sqlite3.Connection:
        """
        Get or create a connection for the current thread.
        
        Returns:
            sqlite3.Connection: Thread-local database connection
        """
        if not hasattr(self._local, 'connection') or self._local.connection is None:
            self._local.connection = sqlite3.connect(self.db_path)
            self._local.connection.row_factory = sqlite3.Row  # Enable column access by name
            # Enable foreign keys
            self._local.connection.execute("PRAGMA foreign_keys = ON")
        return self._local.connection
    
    def _execute_with_retry(self, func, *args, **kwargs):
        """
        Execute a database operation with retry logic for handling locks.
        
        Args:
            func: Function to execute
            *args: Positional arguments for func
            **kwargs: Keyword arguments for func
            
        Returns:
            Result of func execution
            
        Raises:
            sqlite3.Error: If all retry attempts fail
        """
        last_error = sqlite3.Error("Database operation failed after retries")
        for attempt in range(self._retry_attempts):
            try:
                return func(*args, **kwargs)
            except sqlite3.OperationalError as e:
                last_error = e
                if "database is locked" in str(e) and attempt < self._retry_attempts - 1:
                    time.sleep(self._retry_delay * (attempt + 1))  # Exponential backoff
                    continue
                raise
            except Exception as e:
                last_error = e
                raise
        
        raise last_error
    
    @contextmanager
    def transaction(self):
        """
        Context manager for database transactions.
        
        Usage:
            with db_manager.transaction():
                db_manager.execute("INSERT INTO ...")
                db_manager.execute("UPDATE ...")
        """
        conn = self._get_connection()
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
    
    def execute(self, query: str, params: Optional[Tuple] = None) -> sqlite3.Cursor:
        """
        Execute a query without returning results.
        
        Args:
            query: SQL query to execute
            params: Optional parameters for the query
            
        Returns:
            sqlite3.Cursor: Cursor after execution
        """
        def _execute():
            conn = self._get_connection()
            cursor = conn.cursor()
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            conn.commit()
            return cursor
        
        return self._execute_with_retry(_execute)
    
    def executemany(self, query: str, params_list: List[Tuple]) -> sqlite3.Cursor:
        """
        Execute a query multiple times with different parameters.
        
        Args:
            query: SQL query to execute
            params_list: List of parameter tuples
            
        Returns:
            sqlite3.Cursor: Cursor after execution
        """
        def _executemany():
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.executemany(query, params_list)
            conn.commit()
            return cursor
        
        return self._execute_with_retry(_executemany)
    
    def fetchone(self, query: str, params: Optional[Tuple] = None) -> Optional[sqlite3.Row]:
        """
        Execute a query and fetch one result.
        
        Args:
            query: SQL query to execute
            params: Optional parameters for the query
            
        Returns:
            sqlite3.Row or None: Single result row
        """
        def _fetchone():
            conn = self._get_connection()
            cursor = conn.cursor()
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            return cursor.fetchone()
        
        return self._execute_with_retry(_fetchone)
    
    def fetchall(self, query: str, params: Optional[Tuple] = None) -> List[sqlite3.Row]:
        """
        Execute a query and fetch all results.
        
        Args:
            query: SQL query to execute
            params: Optional parameters for the query
            
        Returns:
            List[sqlite3.Row]: All result rows
        """
        def _fetchall():
            conn = self._get_connection()
            cursor = conn.cursor()
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            return cursor.fetchall()
        
        return self._execute_with_retry(_fetchall)
    
    def table_exists(self, table_name: str) -> bool:
        """
        Check if a table exists in the database.
        
        Args:
            table_name: Name of the table to check
            
        Returns:
            bool: True if table exists, False otherwise
        """
        query = "SELECT name FROM sqlite_master WHERE type='table' AND name=?"
        result = self.fetchone(query, (table_name,))
        return result is not None
    
    def create_table(self, table_name: str, schema: str):
        """
        Create a table if it doesn't exist.
        
        Args:
            table_name: Name of the table to create
            schema: SQL schema definition (columns, types, constraints)
        """
        query = f"CREATE TABLE IF NOT EXISTS {table_name} ({schema})"
        self.execute(query)
    
    def insert(self, table_name: str, data: Dict[str, Any]) -> Optional[int]:
        """
        Insert a row into a table.
        
        Args:
            table_name: Name of the table
            data: Dictionary of column names to values
            
        Returns:
            Optional[int]: Last inserted row ID or None
        """
        columns = ', '.join(data.keys())
        placeholders = ', '.join('?' * len(data))
        query = f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders})"
        cursor = self.execute(query, tuple(data.values()))
        return cursor.lastrowid
    
    def insert_or_replace(self, table_name: str, data: Dict[str, Any]) -> Optional[int]:
        """
        Insert or replace a row in a table.
        
        Args:
            table_name: Name of the table
            data: Dictionary of column names to values
            
        Returns:
            Optional[int]: Last inserted row ID or None
        """
        columns = ', '.join(data.keys())
        placeholders = ', '.join('?' * len(data))
        query = f"INSERT OR REPLACE INTO {table_name} ({columns}) VALUES ({placeholders})"
        cursor = self.execute(query, tuple(data.values()))
        return cursor.lastrowid
    
    def update(self, table_name: str, data: Dict[str, Any], where: str, where_params: Tuple) -> int:
        """
        Update rows in a table.
        
        Args:
            table_name: Name of the table
            data: Dictionary of column names to new values
            where: WHERE clause (without 'WHERE' keyword)
            where_params: Parameters for the WHERE clause
            
        Returns:
            int: Number of affected rows
        """
        set_clause = ', '.join(f"{k} = ?" for k in data.keys())
        query = f"UPDATE {table_name} SET {set_clause} WHERE {where}"
        params = tuple(data.values()) + where_params
        cursor = self.execute(query, params)
        return cursor.rowcount
    
    def delete(self, table_name: str, where: str, where_params: Tuple) -> int:
        """
        Delete rows from a table.
        
        Args:
            table_name: Name of the table
            where: WHERE clause (without 'WHERE' keyword)
            where_params: Parameters for the WHERE clause
            
        Returns:
            int: Number of deleted rows
        """
        query = f"DELETE FROM {table_name} WHERE {where}"
        cursor = self.execute(query, where_params)
        return cursor.rowcount
    
    def close_thread_connection(self):
        """Close the connection for the current thread."""
        if hasattr(self._local, 'connection') and self._local.connection:
            self._local.connection.close()
            self._local.connection = None
    
    def close_all_connections(self):
        """Close all connections (call only when shutting down)."""
        # Note: This only closes the current thread's connection
        # In a multi-threaded environment, each thread should call close_thread_connection
        self.close_thread_connection()


# Global instance getter
def get_db_manager() -> DatabaseManager:
    """Get the singleton DatabaseManager instance."""
    return DatabaseManager()
