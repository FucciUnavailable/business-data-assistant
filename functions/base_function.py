"""
Base class for all client data functions.
Provides: caching, connection pooling, security, logging, rate limiting.
"""

import os
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple
from functools import wraps
from datetime import datetime
import time

from config.database import db_config
from config.cache import cache
from config.permissions import permissions

# Setup logging
logging.basicConfig(
    level=os.getenv('LOG_LEVEL', 'INFO'),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.getenv('LOG_FILE', 'logs/app.log')),
        logging.StreamHandler()
    ]
)


def cache_result(ttl: int = 300):
    """
    Decorator to cache function results.

    Args:
        ttl: Time to live in seconds (default 5 minutes)
    """
    def decorator(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            # Generate cache key (exclude __user__ from key)
            cache_kwargs = {k: v for k, v in kwargs.items() if k != '__user__'}
            cache_key = f"{func.__name__}:{cache.generate_cache_key(*args, **cache_kwargs)}"

            # Try to get from cache
            cached_result = cache.get(cache_key)
            if cached_result is not None:
                self.logger.info(f"Cache HIT: {cache_key}")
                return cached_result

            # Cache miss - execute function
            self.logger.info(f"Cache MISS: {cache_key}")
            result = func(self, *args, **kwargs)

            # Store in cache
            cache.set(cache_key, result, ttl)

            return result
        return wrapper
    return decorator


def track_performance(func):
    """Decorator to track function execution time"""
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        start_time = time.time()

        try:
            result = func(self, *args, **kwargs)
            duration = time.time() - start_time

            # Log slow queries
            if duration > 1.0:
                self.logger.warning(
                    f"SLOW QUERY: {func.__name__} took {duration:.2f}s"
                )
            else:
                self.logger.info(
                    f"Query completed: {func.__name__} in {duration:.3f}s"
                )

            return result

        except Exception as e:
            duration = time.time() - start_time
            self.logger.error(
                f"Query failed: {func.__name__} after {duration:.3f}s - {str(e)}"
            )
            raise

    return wrapper


class BaseClientFunction(ABC):
    """
    Base class that all client data functions inherit from.
    Provides common functionality: DB access, caching, security, logging.
    """

    # Override these in child classes
    FUNCTION_NAME = "base_function"
    FUNCTION_VERSION = "0.0.0"
    REQUIRED_PERMISSIONS = []  # List of roles that can access this function

    def __init__(self):
        self.logger = logging.getLogger(self.FUNCTION_NAME)
        self.max_rows = int(os.getenv('MAX_QUERY_ROWS', '1000'))

    # ==================== PERMISSION CHECKING ====================

    def _check_permissions(self, user: Dict[str, Any], client_id: Optional[str] = None) -> bool:
        """
        Check if user has permission to execute this function.

        Args:
            user: User dict with 'id', 'name', 'role', etc.
            client_id: Optional client ID for row-level security

        Returns:
            True if authorized, False otherwise
        """
        user_id = user.get('id', 'unknown')
        user_role = user.get('role', '')

        # Check function-level permission
        if not permissions.can_access_function(user_role, self.FUNCTION_NAME):
            self.logger.warning(
                f"Permission denied: user={user_id}, role={user_role}, "
                f"function={self.FUNCTION_NAME}"
            )
            return False

        # Check row-level security if client_id provided
        if client_id and os.getenv('ENABLE_ROW_LEVEL_SECURITY', 'true').lower() == 'true':
            if not self._can_access_client(user, client_id):
                self.logger.warning(
                    f"Client access denied: user={user_id}, client={client_id}"
                )
                return False

        # Check rate limit
        if not self._check_rate_limit(user):
            self.logger.warning(f"Rate limit exceeded: user={user_id}")
            return False

        return True

    def _can_access_client(self, user: Dict[str, Any], client_id: str) -> bool:
        """
        Check if user can access specific client data (row-level security).

        Args:
            user: User dictionary
            client_id: Client identifier

        Returns:
            True if user can access this client's data
        """
        user_role = user.get('role', '')

        # Admin and roles with can_view_all_clients can access any client
        if permissions.can_view_all_clients(user_role):
            return True

        # For restricted roles, check user-client mapping
        # This assumes you have a table mapping users to clients
        user_id = user.get('id')

        query = """
            SELECT 1
            FROM dbo.user_client_access
            WHERE user_id = ? AND client_id = ?
        """

        try:
            results = self._execute_query(query, (user_id, client_id), use_cache=False)
            return len(results) > 0
        except Exception as e:
            self.logger.error(f"Error checking client access: {str(e)}")
            return False

    def _check_rate_limit(self, user: Dict[str, Any]) -> bool:
        """
        Check if user has exceeded their rate limit.

        Args:
            user: User dictionary

        Returns:
            True if within limit, False if exceeded
        """
        user_id = user.get('id', 'unknown')
        user_role = user.get('role', '')

        # Get rate limit for role
        limit = permissions.get_rate_limit(user_role)

        # Use Redis counter
        key = f"rate_limit:{user_id}"
        current = cache.increment(key)

        # Set expiry on first request (1 hour window)
        if current == 1:
            cache.expire(key, 3600)

        # Check if over limit
        if current > limit:
            return False

        return True

    # ==================== DATABASE OPERATIONS ====================

    @track_performance
    def _execute_query(
        self,
        query: str,
        params: Tuple,
        max_rows: Optional[int] = None,
        use_cache: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Execute a parameterized SQL query safely.

        Args:
            query: SQL query with ? placeholders
            params: Tuple of parameters
            max_rows: Maximum rows to return (defaults to self.max_rows)
            use_cache: Whether results can be cached (default True)

        Returns:
            List of result rows as dictionaries
        """
        max_rows = max_rows or self.max_rows

        conn = None
        try:
            # Get connection from pool
            conn = db_config.get_connection()
            cursor = conn.cursor()

            # Set query limits at SQL Server level
            cursor.execute("SET LOCK_TIMEOUT 5000")  # 5 sec max lock wait
            cursor.execute(f"SET ROWCOUNT {max_rows}")

            # Execute query
            cursor.execute(query, params)

            # Fetch results
            columns = [column[0] for column in cursor.description]
            results = []

            for row in cursor.fetchall():
                results.append(dict(zip(columns, row)))

            self.logger.debug(
                f"Query executed: {len(results)} rows returned. "
                f"Query: {query[:100]}..."
            )

            return results

        except Exception as e:
            self.logger.error(f"Query execution failed: {str(e)}")
            raise Exception("Unable to retrieve data. Please try again later.")

        finally:
            if conn:
                conn.close()  # Returns connection to pool

    # ==================== UTILITY METHODS ====================

    def _sanitize_input(self, value: str) -> str:
        """
        Sanitize user input (defense in depth - we use parameterized queries).

        Args:
            value: Input string to sanitize

        Returns:
            Sanitized string
        """
        if not value:
            return ""

        # Remove potentially dangerous characters
        dangerous = [';', '--', '/*', '*/', 'xp_', 'sp_']
        sanitized = str(value)

        for char in dangerous:
            sanitized = sanitized.replace(char, '')

        return sanitized.strip()

    def _format_error_response(self, error: Exception) -> str:
        """
        Format error message for users (don't leak internal details).

        Args:
            error: The exception that occurred

        Returns:
            User-friendly error message
        """
        self.logger.error(f"Error in {self.FUNCTION_NAME}: {str(error)}")

        # Generic error message for users
        return (
            "I encountered an error while retrieving the data. "
            "Please try again or contact support if the issue persists."
        )

    # ==================== ABSTRACT METHOD ====================

    @abstractmethod
    def execute(self, **kwargs) -> str:
        """
        Main execution method - override in child classes.
        This is what OpenWebUI will call.
        """
        pass
