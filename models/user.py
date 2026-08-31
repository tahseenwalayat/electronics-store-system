"""
User and Role Domain Models.
"""

from dataclasses import dataclass, field
from typing import Optional, Set
from datetime import datetime


@dataclass
class User:
    """
    User entity representation with role and permission checking.
    """
    id: int
    username: str
    full_name: str
    role_id: int
    role_name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    is_active: bool = True
    last_login_at: Optional[datetime] = None
    permissions: Set[str] = field(default_factory=set)

    @property
    def is_admin(self) -> bool:
        """Check if user has administrative privileges."""
        return self.role_name.lower() == "admin"

    def has_permission(self, permission_code: str) -> bool:
        """
        Check if user has a specific permission code.
        Admins inherently possess all permissions.
        """
        if not self.is_active:
            return False
        if self.is_admin:
            return True
        return permission_code in self.permissions
