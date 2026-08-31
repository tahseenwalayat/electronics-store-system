"""
App-wide Permissions System & Enforcement Helpers.
Defines modules, actions, role defaults, and security decorators.
"""

from typing import List, Dict, Set, Optional, Callable, Any
from functools import wraps
import logging
from PySide6.QtWidgets import QMessageBox, QWidget
from business.session import get_session
from models.user import User

logger = logging.getLogger(__name__)

# 10 Core System Modules
MODULES = [
    {"key": "sales", "name": "Sales & POS", "description": "Process sales, receipts, and returns"},
    {"key": "purchases", "name": "Purchases", "description": "Supplier purchases and return orders"},
    {"key": "products", "name": "Products", "description": "Product catalog, pricing, and stock search"},
    {"key": "stock_adjustment", "name": "Stock Adjustment", "description": "Manual inventory stock adjustments"},
    {"key": "reports", "name": "Reports & Analytics", "description": "Sales, financial, and inventory analytics"},
    {"key": "customers", "name": "Customers", "description": "Customer directory and credit management"},
    {"key": "suppliers", "name": "Suppliers", "description": "Supplier profiles and purchase history"},
    {"key": "warranty", "name": "Warranty Claims", "description": "Warranty claims and repair tracking"},
    {"key": "users", "name": "Users & Permissions", "description": "User accounts, roles, and access management"},
    {"key": "backup_restore", "name": "Backup / Restore", "description": "Database backup and restoration tools"},
]

ACTIONS = [
    {"key": "view", "name": "View", "desc": "Read-only access to module data"},
    {"key": "manage", "name": "Create / Edit", "desc": "Add or modify records within module"},
    {"key": "delete", "name": "Delete", "desc": "Delete records (Admin-only capability)"},
]

# Default permissions mapping per role
DEFAULT_ROLE_PERMISSIONS: Dict[str, Set[str]] = {
    "admin": {
        f"{m['key']}.{a['key']}" for m in MODULES for a in ACTIONS
    },
    "manager": {
        "sales.view", "sales.manage",
        "purchases.view", "purchases.manage",
        "products.view", "products.manage",
        "stock_adjustment.view", "stock_adjustment.manage",
        "reports.view", "reports.manage",
        "customers.view", "customers.manage",
        "suppliers.view", "suppliers.manage",
        "warranty.view", "warranty.manage",
    },
    "cashier": {
        "sales.view", "sales.manage",
        "customers.view", "customers.manage",
        "products.view",  # Product search
    },
}


def get_all_permission_codes() -> List[str]:
    """Generate all permission code combinations (module.action)."""
    codes = []
    for m in MODULES:
        for a in ACTIONS:
            codes.append(f"{m['key']}.{a['key']}")
    return codes


def has_permission(permission_code: str, user: Optional[User] = None) -> bool:
    """
    App-wide helper to check if the user holds a specific permission.
    If user is omitted, checks the current session user.
    Enforces business rule: '.delete' permissions are strictly for Admins.
    """
    if user is None:
        session = get_session()
        if not session.is_authenticated:
            return False
        user = session.current_user

    if user is None or not user.is_active:
        return False

    # Admins always possess all permissions
    if user.is_admin:
        return True

    # Non-admins can NEVER perform delete actions
    if permission_code.endswith(".delete"):
        return False

    return permission_code in user.permissions


def can_view(module_key: str, user: Optional[User] = None) -> bool:
    """Check view permission for a module."""
    return has_permission(f"{module_key}.view", user)


def can_manage(module_key: str, user: Optional[User] = None) -> bool:
    """Check create/edit permission for a module."""
    return has_permission(f"{module_key}.manage", user)


def can_delete(module_key: str, user: Optional[User] = None) -> bool:
    """Check delete permission for a module (Admin only)."""
    return has_permission(f"{module_key}.delete", user)


def check_permission(
    permission_code: str,
    parent: Optional[QWidget] = None,
    action_name: str = "perform this action",
    show_dialog: bool = True,
) -> bool:
    """
    Check permission with optional user feedback warning dialog.
    """
    allowed = has_permission(permission_code)
    if not allowed and show_dialog:
        msg = f"Access Denied: You do not have permission to {action_name}.\nRequired: '{permission_code}'"
        if permission_code.endswith(".delete"):
            msg += "\n(Note: Delete operations are strictly restricted to Administrators.)"
        logger.warning(f"Permission denied for '{permission_code}' on action '{action_name}'")
        QMessageBox.warning(parent, "Permission Denied", msg)
    return allowed


def require_permission(permission_code: str, action_name: str = "perform this action"):
    """
    Decorator for UI methods to enforce permissions before execution.
    Usage:
        @require_permission("users.manage", "modify users")
        def on_save_clicked(self):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(self, *args, **kwargs) -> Any:
            parent = self if isinstance(self, QWidget) else None
            if not check_permission(permission_code, parent=parent, action_name=action_name):
                return None
            return func(self, *args, **kwargs)
        return wrapper
    return decorator
