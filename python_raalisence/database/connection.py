"""Database connection and management."""

import sqlite3
import asyncio
from typing import Optional, Union
import asyncpg
import psycopg2
from contextlib import asynccontextmanager
from python_raalisence.config.config import Config


class DatabaseConnection:
    """Database connection manager."""
    
    def __init__(self, config: Config):
        self.config = config
        self._connection: Optional[Union[sqlite3.Connection, asyncpg.Connection]] = None
    
    def connect(self):
        """Establish database connection."""
        if self.config.db_driver == "sqlite3":
            self._connection = sqlite3.connect(self.config.db_path)
            self._connection.row_factory = sqlite3.Row
            # Enable foreign keys
            self._connection.execute("PRAGMA foreign_keys = ON")
        elif self.config.db_driver == "postgresql":
            # For synchronous operations, we'll use psycopg2
            self._connection = psycopg2.connect(self.config.db_dsn)
        else:
            raise ValueError(f"unsupported database driver: {self.config.db_driver}")
    
    async def connect_async(self):
        """Establish async database connection."""
        if self.config.db_driver == "postgresql":
            self._connection = await asyncpg.connect(self.config.db_dsn)
        else:
            raise ValueError("async connections only supported for PostgreSQL")
    
    def close(self):
        """Close database connection."""
        if self._connection:
            if self.config.db_driver == "sqlite3":
                self._connection.close()
            elif self.config.db_driver == "postgresql":
                self._connection.close()
            self._connection = None
    
    async def close_async(self):
        """Close async database connection."""
        if self._connection:
            await self._connection.close()
            self._connection = None
    
    @property
    def connection(self):
        """Get the database connection."""
        return self._connection
    
    def execute(self, query: str, params: tuple = ()):
        """Execute a query synchronously."""
        if not self._connection:
            raise RuntimeError("database not connected")
        
        if self.config.db_driver == "sqlite3":
            cursor = self._connection.cursor()
            cursor.execute(query, params)
            return cursor
        elif self.config.db_driver == "postgresql":
            cursor = self._connection.cursor()
            cursor.execute(query, params)
            return cursor
    
    def execute_fetchone(self, query: str, params: tuple = ()):
        """Execute query and fetch one row."""
        cursor = self.execute(query, params)
        return cursor.fetchone()
    
    def execute_fetchall(self, query: str, params: tuple = ()):
        """Execute query and fetch all rows."""
        cursor = self.execute(query, params)
        return cursor.fetchall()
    
    def commit(self):
        """Commit transaction."""
        if self._connection:
            self._connection.commit()
    
    def rollback(self):
        """Rollback transaction."""
        if self._connection:
            self._connection.rollback()


@asynccontextmanager
async def get_db_connection(config: Config):
    """Context manager for database connections."""
    db = DatabaseConnection(config)
    try:
        if config.db_driver == "postgresql":
            await db.connect_async()
        else:
            db.connect()
        yield db
    finally:
        if config.db_driver == "postgresql":
            await db.close_async()
        else:
            db.close()

