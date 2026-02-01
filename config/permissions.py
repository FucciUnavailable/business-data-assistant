"""
Role-Based Access Control (RBAC) configuration.
Define who can access what functions and data.
"""

from typing import List, Dict, Any
from enum import Enum


class Role(str, Enum):
    """Available user roles"""
    ADMIN = "admin"
    SALES = "sales"
    SUPPORT = "support"
    FINANCE = "finance"
    READONLY = "readonly"


class PermissionConfig:
    """Centralized permission management"""

    # Function-level permissions: which roles can call which functions
    FUNCTION_PERMISSIONS: Dict[str, List[str]] = {
        "get_client_notes": [Role.ADMIN, Role.SALES, Role.SUPPORT],
        "get_all_notes": [Role.ADMIN, Role.SALES, Role.SUPPORT],
        "get_transaction_count": [Role.ADMIN, Role.FINANCE, Role.SALES],
        "get_total_amount_paid": [Role.ADMIN, Role.FINANCE],
        "get_payment_history": [Role.ADMIN, Role.FINANCE],
        "get_contract_status": [Role.ADMIN, Role.SALES],
        "get_client_summary": [Role.ADMIN, Role.SALES, Role.FINANCE],
    }

    # Rate limits per role (queries per hour)
    RATE_LIMITS: Dict[str, int] = {
        Role.ADMIN: 1000,
        Role.SALES: 500,
        Role.SUPPORT: 500,
        Role.FINANCE: 300,
        Role.READONLY: 100,
    }

    # Data access rules
    DATA_ACCESS: Dict[str, Dict[str, Any]] = {
        Role.ADMIN: {
            "can_view_all_clients": True,
            "can_view_financials": True,
            "tables": "*",  # All tables
        },
        Role.SALES: {
            "can_view_all_clients": True,
            "can_view_financials": False,
            "tables": ["dbo.notes", "dbo.contracts", "dbo.clients"],
        },
        Role.SUPPORT: {
            "can_view_all_clients": False,  # Only assigned clients
            "can_view_financials": False,
            "tables": ["dbo.notes", "dbo.tickets"],
        },
        Role.FINANCE: {
            "can_view_all_clients": True,
            "can_view_financials": True,
            "tables": ["dbo.payments", "dbo.invoices", "dbo.contracts"],
        },
        Role.READONLY: {
            "can_view_all_clients": False,
            "can_view_financials": False,
            "tables": [],
        },
    }

    @classmethod
    def can_access_function(cls, role: str, function_name: str) -> bool:
        """Check if role can access specific function"""
        allowed_roles = cls.FUNCTION_PERMISSIONS.get(function_name, [])
        return role in allowed_roles or role == Role.ADMIN

    @classmethod
    def get_rate_limit(cls, role: str) -> int:
        """Get rate limit for role"""
        return cls.RATE_LIMITS.get(role, 100)

    @classmethod
    def can_view_all_clients(cls, role: str) -> bool:
        """Check if role can view all client data"""
        access = cls.DATA_ACCESS.get(role, {})
        return access.get("can_view_all_clients", False)

    @classmethod
    def can_view_financials(cls, role: str) -> bool:
        """Check if role can view financial data"""
        access = cls.DATA_ACCESS.get(role, {})
        return access.get("can_view_financials", False)


# Singleton instance
permissions = PermissionConfig()
