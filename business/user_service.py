"""
User and Permission Management Service.
Handles CRUD for users, password resets, role assignments, and modular permission grids.
"""

import logging
from typing import Optional, List, Dict, Tuple, Set, Any
import bcrypt
import json

from data.db import DatabaseManager, get_db
from business.session import get_session
from business.permissions import (
    MODULES,
    ACTIONS,
    DEFAULT_ROLE_PERMISSIONS,
    has_permission,
)

logger = logging.getLogger(__name__)


def hash_password(password: str) -> str:
    """Generate bcrypt password hash."""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


class UserService:
    """
    Business service for managing user accounts and access permissions.
    """

    def __init__(self, db_manager: Optional[DatabaseManager] = None):
        self.db = db_manager or get_db()
        self.session = get_session()

    def get_all_users(self) -> List[Dict[str, Any]]:
        """Retrieve list of all users with their role details."""
        query = """
            SELECT 
                u.id, u.username, u.full_name, u.email, u.phone, 
                u.is_active, u.role_id, r.name AS role_name,
                u.last_login_at, u.created_at, u.updated_at
            FROM users u
            JOIN roles r ON u.role_id = r.id
            ORDER BY 
                CASE LOWER(r.name) 
                    WHEN 'admin' THEN 1 
                    WHEN 'manager' THEN 2 
                    WHEN 'cashier' THEN 3 
                    ELSE 4 
                END, 
                u.username ASC;
        """
        rows = self.db.execute_query(query)
        return [dict(r) for r in rows]

    def get_user_by_id(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Retrieve single user details with role name."""
        query = """
            SELECT 
                u.id, u.username, u.full_name, u.email, u.phone, 
                u.is_active, u.role_id, r.name AS role_name,
                u.last_login_at, u.created_at
            FROM users u
            JOIN roles r ON u.role_id = r.id
            WHERE u.id = ?;
        """
        row = self.db.execute_one(query, (user_id,))
        return dict(row) if row else None

    def get_all_roles(self) -> List[Dict[str, Any]]:
        """Retrieve list of all system roles."""
        rows = self.db.execute_query("SELECT id, name, description FROM roles ORDER BY id ASC;")
        return [dict(r) for r in rows]

    def get_role_permissions(self, role_id: int) -> Set[str]:
        """Get set of permission codes assigned to a role."""
        query = """
            SELECT p.code 
            FROM permissions p
            JOIN role_permissions rp ON p.id = rp.permission_id
            WHERE rp.role_id = ?;
        """
        rows = self.db.execute_query(query, (role_id,))
        return {r["code"] for r in rows}

    def get_user_direct_permissions(self, user_id: int) -> Set[str]:
        """Get set of permission codes explicitly granted to a user."""
        query = """
            SELECT p.code 
            FROM permissions p
            JOIN user_permissions up ON p.id = up.permission_id
            WHERE up.user_id = ?;
        """
        rows = self.db.execute_query(query, (user_id,))
        return {r["code"] for r in rows}

    def get_user_effective_permissions(self, user_id: int) -> Set[str]:
        """Get total combined permissions for a user (role + direct grants)."""
        user = self.get_user_by_id(user_id)
        if not user:
            return set()

        # If admin role, returns all permissions
        if user["role_name"].lower() == "admin":
            all_perms = self.db.execute_query("SELECT code FROM permissions;")
            return {r["code"] for r in all_perms}

        role_perms = self.get_role_permissions(user["role_id"])
        direct_perms = self.get_user_direct_permissions(user_id)
        combined = role_perms.union(direct_perms)

        # Enforce rule: Non-admins cannot have '.delete' permissions
        return {p for p in combined if not p.endswith(".delete")}

    def create_user(
        self,
        username: str,
        password: str,
        full_name: str,
        role_id: int,
        email: Optional[str] = None,
        phone: Optional[str] = None,
        is_active: bool = True,
        permissions: Optional[Set[str]] = None,
    ) -> Tuple[bool, Optional[int], str]:
        """
        Create a new user account with hashed password and permissions.
        Requires 'users.manage' permission.
        """
        if not has_permission("users.manage"):
            return False, None, "Permission Denied: You do not have permission to create users."

        username = (username or "").strip()
        full_name = (full_name or "").strip()
        email = (email or "").strip() or None
        phone = (phone or "").strip() or None

        if not username or len(username) < 3:
            return False, None, "Username must be at least 3 characters long."
        if not full_name:
            return False, None, "Full Name is required."
        if not password or len(password) < 6:
            return False, None, "Password must be at least 6 characters long."

        # Check for unique username
        existing = self.db.execute_one(
            "SELECT id FROM users WHERE LOWER(username) = LOWER(?);",
            (username,)
        )
        if existing:
            return False, None, f"Username '{username}' already exists. Please choose another."

        # Verify role
        role_row = self.db.execute_one("SELECT name FROM roles WHERE id = ?;", (role_id,))
        if not role_row:
            return False, None, "Invalid role selected."
        role_name = role_row["name"].lower()

        # Enforce: Only Admin can create an Admin user
        current_user = self.session.current_user
        if role_name == "admin" and (not current_user or not current_user.is_admin):
            return False, None, "Only Administrators can create an Admin account."

        hashed_pw = hash_password(password)

        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO users (role_id, username, password_hash, full_name, email, phone, is_active)
                    VALUES (?, ?, ?, ?, ?, ?, ?);
                """, (role_id, username, hashed_pw, full_name, email, phone, 1 if is_active else 0))
                new_user_id = cursor.lastrowid

                # Assign custom permissions if provided
                if permissions:
                    # Filter out delete permissions for non-admins
                    allowed_perms = permissions if role_name == "admin" else {p for p in permissions if not p.endswith(".delete")}
                    for code in allowed_perms:
                        cursor.execute("SELECT id FROM permissions WHERE code = ?;", (code,))
                        prow = cursor.fetchone()
                        if prow:
                            cursor.execute(
                                "INSERT OR IGNORE INTO user_permissions (user_id, permission_id, granted_by) VALUES (?, ?, ?);",
                                (new_user_id, prow["id"], current_user.id if current_user else None),
                            )

                # Record audit log
                cursor.execute("""
                    INSERT INTO audit_logs (user_id, action, entity_type, entity_id, new_value)
                    VALUES (?, 'CREATE', 'User', ?, ?);
                """, (
                    current_user.id if current_user else None,
                    str(new_user_id),
                    json.dumps({"username": username, "role": role_name, "full_name": full_name}),
                ))

            logger.info(f"User '{username}' created successfully with ID {new_user_id}")
            return True, new_user_id, "User created successfully."

        except Exception as e:
            logger.error(f"Error creating user '{username}': {e}", exc_info=True)
            return False, None, f"Database error: {str(e)}"

    def update_user(
        self,
        user_id: int,
        full_name: str,
        role_id: int,
        email: Optional[str] = None,
        phone: Optional[str] = None,
        is_active: bool = True,
        permissions: Optional[Set[str]] = None,
    ) -> Tuple[bool, str]:
        """
        Update user profile, role, and permission grants.
        Requires 'users.manage' permission.
        """
        if not has_permission("users.manage"):
            return False, "Permission Denied: You do not have permission to edit users."

        full_name = (full_name or "").strip()
        email = (email or "").strip() or None
        phone = (phone or "").strip() or None

        if not full_name:
            return False, "Full Name cannot be empty."

        target_user = self.get_user_by_id(user_id)
        if not target_user:
            return False, "User not found."

        # Safety Check: Prevent deactivating the last active Admin
        if not is_active and target_user["role_name"].lower() == "admin":
            admin_count_row = self.db.execute_one(
                "SELECT COUNT(*) AS count FROM users u JOIN roles r ON u.role_id = r.id WHERE LOWER(r.name) = 'admin' AND u.is_active = 1 AND u.id != ?;",
                (user_id,)
            )
            if admin_count_row and admin_count_row["count"] == 0:
                return False, "Cannot deactivate the only active Administrator account."

        # Verify role
        role_row = self.db.execute_one("SELECT name FROM roles WHERE id = ?;", (role_id,))
        if not role_row:
            return False, "Invalid role selected."
        role_name = role_row["name"].lower()

        current_user = self.session.current_user

        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE users 
                    SET full_name = ?, role_id = ?, email = ?, phone = ?, is_active = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?;
                """, (full_name, role_id, email, phone, 1 if is_active else 0, user_id))

                # Update user_permissions (clear and re-insert)
                cursor.execute("DELETE FROM user_permissions WHERE user_id = ?;", (user_id,))
                if permissions:
                    allowed_perms = permissions if role_name == "admin" else {p for p in permissions if not p.endswith(".delete")}
                    for code in allowed_perms:
                        cursor.execute("SELECT id FROM permissions WHERE code = ?;", (code,))
                        prow = cursor.fetchone()
                        if prow:
                            cursor.execute(
                                "INSERT OR IGNORE INTO user_permissions (user_id, permission_id, granted_by) VALUES (?, ?, ?);",
                                (user_id, prow["id"], current_user.id if current_user else None),
                            )

                # Record audit
                cursor.execute("""
                    INSERT INTO audit_logs (user_id, action, entity_type, entity_id, old_value, new_value)
                    VALUES (?, 'UPDATE', 'User', ?, ?, ?);
                """, (
                    current_user.id if current_user else None,
                    str(user_id),
                    json.dumps(target_user),
                    json.dumps({"full_name": full_name, "role": role_name, "is_active": is_active}),
                ))

            logger.info(f"User ID {user_id} updated successfully")
            return True, "User updated successfully."

        except Exception as e:
            logger.error(f"Error updating user ID {user_id}: {e}", exc_info=True)
            return False, f"Database error: {str(e)}"

    def reset_password(self, user_id: int, new_password: str) -> Tuple[bool, str]:
        """
        Reset user's password.
        Requires 'users.manage' permission.
        """
        if not has_permission("users.manage"):
            return False, "Permission Denied: You do not have permission to reset passwords."

        if not new_password or len(new_password) < 6:
            return False, "New Password must be at least 6 characters long."

        target_user = self.get_user_by_id(user_id)
        if not target_user:
            return False, "User not found."

        hashed_pw = hash_password(new_password)
        current_user = self.session.current_user

        try:
            self.db.execute_update(
                "UPDATE users SET password_hash = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?;",
                (hashed_pw, user_id)
            )

            # Record audit
            self.db.execute_update("""
                INSERT INTO audit_logs (user_id, action, entity_type, entity_id, new_value)
                VALUES (?, 'PASSWORD_RESET', 'User', ?, ?);
            """, (
                current_user.id if current_user else None,
                str(user_id),
                json.dumps({"target_username": target_user["username"]}),
            ))

            logger.info(f"Password reset for user '{target_user['username']}' by user ID {current_user.id if current_user else 'system'}")
            return True, f"Password for '{target_user['username']}' has been reset successfully."

        except Exception as e:
            logger.error(f"Error resetting password for user ID {user_id}: {e}", exc_info=True)
            return False, f"Database error: {str(e)}"

    def delete_user(self, user_id: int) -> Tuple[bool, str]:
        """
        Delete a user account.
        Requires 'users.delete' permission (strictly restricted to Admin).
        """
        if not has_permission("users.delete"):
            return False, "Permission Denied: Delete operation is strictly restricted to Administrators."

        target_user = self.get_user_by_id(user_id)
        if not target_user:
            return False, "User not found."

        current_user = self.session.current_user
        if current_user and current_user.id == user_id:
            return False, "You cannot delete your own account while logged in."

        # Safety Check: Prevent deleting the last Admin
        if target_user["role_name"].lower() == "admin":
            admin_count_row = self.db.execute_one(
                "SELECT COUNT(*) AS count FROM users u JOIN roles r ON u.role_id = r.id WHERE LOWER(r.name) = 'admin' AND u.id != ?;",
                (user_id,)
            )
            if admin_count_row and admin_count_row["count"] == 0:
                return False, "Cannot delete the only Administrator account."

        try:
            # Check if user has associated transactions
            has_sales = self.db.execute_one("SELECT id FROM sales WHERE user_id = ? LIMIT 1;", (user_id,))
            has_purchases = self.db.execute_one("SELECT id FROM purchases WHERE user_id = ? LIMIT 1;", (user_id,))

            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                if has_sales or has_purchases:
                    # User has transaction history: deactivate instead to maintain referential integrity
                    cursor.execute("UPDATE users SET is_active = 0, updated_at = CURRENT_TIMESTAMP WHERE id = ?;", (user_id,))
                    action = "DEACTIVATE"
                    msg = f"User '{target_user['username']}' has historical transaction records. Account was deactivated instead of permanently deleted."
                else:
                    cursor.execute("DELETE FROM user_permissions WHERE user_id = ?;", (user_id,))
                    cursor.execute("DELETE FROM users WHERE id = ?;", (user_id,))
                    action = "DELETE"
                    msg = f"User '{target_user['username']}' has been permanently deleted."

                # Audit log
                cursor.execute("""
                    INSERT INTO audit_logs (user_id, action, entity_type, entity_id, old_value)
                    VALUES (?, ?, 'User', ?, ?);
                """, (
                    current_user.id if current_user else None,
                    action,
                    str(user_id),
                    json.dumps(target_user),
                ))

            logger.info(f"User '{target_user['username']}' {action.lower()}d by user ID {current_user.id if current_user else 'system'}")
            return True, msg

        except Exception as e:
            logger.error(f"Error deleting user ID {user_id}: {e}", exc_info=True)
            return False, f"Database error: {str(e)}"
