"""
Database connection management with pooling and performance optimizations.
"""

import os
import pyodbc
from typing import Optional
from dotenv import load_dotenv
import logging

load_dotenv()

logger = logging.getLogger(__name__)


class DatabaseConfig:
    """Centralized database configuration with connection pooling"""

    def __init__(self):
        self.server = os.getenv('DB_SERVER')
        self.database = os.getenv('DB_NAME')
        self.username = os.getenv('DB_USER')
        self.password = os.getenv('DB_PASSWORD')
        self.driver = os.getenv('DB_DRIVER', 'ODBC Driver 17 for SQL Server')

        # Performance settings
        self.timeout = int(os.getenv('QUERY_TIMEOUT_SECONDS', '30'))
        self.pool_size = int(os.getenv('CONNECTION_POOL_SIZE', '5'))

        # Enable connection pooling globally
        pyodbc.pooling = True

        self._connection_string = self._build_connection_string()

    def _build_connection_string(self) -> str:
        """Build optimized connection string"""
        return (
            f"DRIVER={{{self.driver}}};"
            f"SERVER={self.server};"
            f"DATABASE={self.database};"
            f"UID={self.username};"
            f"PWD={self.password};"
            f"APP=ClientAssistant;"  # For monitoring in SQL Server
            f"MARS_Connection=yes;"  # Multiple Active Result Sets
            f"Encrypt=yes;"
            f"TrustServerCertificate=no;"
            f"Connection Timeout=10;"
        )

    def get_connection(self):
        """
        Get a database connection from the pool.
        Connection is automatically returned to pool when closed.
        """
        try:
            conn = pyodbc.connect(
                self._connection_string,
                timeout=self.timeout,
                autocommit=True
            )
            logger.debug("Database connection acquired from pool")
            return conn
        except pyodbc.Error as e:
            logger.error(f"Database connection failed: {str(e)}")
            raise

    def test_connection(self) -> bool:
        """Test database connectivity"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            conn.close()

            logger.info("Database connection test successful")
            return result[0] == 1
        except Exception as e:
            logger.error(f"Database connection test failed: {str(e)}")
            return False


# Singleton instance
db_config = DatabaseConfig()
