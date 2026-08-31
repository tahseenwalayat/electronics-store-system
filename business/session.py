"""
Application Session Manager.
Maintains state for the currently authenticated user application-wide.
"""

from typing import Optional, Set
from datetime import datetime
import logging
from models.user import User

logger = logging.getLogger(__name__)


class AppSession:
    """
    Singleton Application Session holder.
    Stores the currently logged-in user and session metadata.
    """

    _instance: Optional["AppSession"] = None

    def __init__(self):
        self._user: Optional[User] = None
        self._login_time: Optional[datetime] = None

    @classmethod
    def get_instance(cls) -> "AppSession":
        """Get or initialize singleton instance."""
        if cls._instance is None:
            cls._instance = AppSession()
        return cls._instance

    def set_user(self, user: User) -> None:
        """Store authenticated user and record login timestamp."""
        self._user = user
        self._login_time = datetime.now()
        logger.info(f"Session started for user '{user.username}' (Role: {user.role_name})")

    def clear(self) -> None:
        """Clear current session on logout."""
        if self._user:
            logger.info(f"Session cleared for user '{self._user.username}'")
        self._user = None
        self._login_time = None

    logout = clear  # Alias

    @property
    def is_authenticated(self) -> bool:
        """Check if a valid active user is currently logged in."""
        return self._user is not None and self._user.is_active

    @property
    def current_user(self) -> Optional[User]:
        """Return the current logged-in user instance, or None."""
        return self._user

    @property
    def username(self) -> str:
        """Return current username or empty string."""
        return self._user.username if self._user else ""

    @property
    def user_id(self) -> Optional[int]:
        """Return current user id or None."""
        return self._user.id if self._user else None

    @property
    def role_name(self) -> str:
        """Return current role name or empty string."""
        return self._user.role_name if self._user else ""

    @property
    def login_time(self) -> Optional[datetime]:
        """Return login timestamp."""
        return self._login_time

    def has_permission(self, permission_code: str) -> bool:
        """Check if currently logged-in user holds the given permission."""
        if not self.is_authenticated or self._user is None:
            return False
        return self._user.has_permission(permission_code)


def get_session() -> AppSession:
    """Convenience helper to get the AppSession singleton."""
    return AppSession.get_instance()
