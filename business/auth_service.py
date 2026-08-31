"""
Authentication and Setup Service.
Handles credential verification, password hashing, session bootstrap, and initial setup wizard logic.
"""

import logging
from typing import Optional, Tuple, Set
from datetime import datetime
import bcrypt
import json

from data.db import DatabaseManager, get_db
from models.user import User
from business.session import AppSession, get_session

logger = logging.getLogger(__name__)


def hash_password(password: str) -> str:
    """Generate bcrypt hash for plain password string."""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify plain password against bcrypt hash safely."""
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"),
            hashed_password.encode("utf-8")
        )
    except Exception as e:
        logger.error(f"Password verification error: {e}")
        return False


class AuthService:
    """
    Business service for user authentication, access control, and initial setup.
    """

    def __init__(self, db_manager: Optional[DatabaseManager] = None):
        self.db = db_manager or get_db()
        self.session = get_session()

    def has_users(self) -> bool:
        """
        Check if any user accounts exist in the database.
        Returns False if system is in a first-launch unconfigured state.
        """
        try:
            row = self.db.execute_one("SELECT COUNT(*) AS count FROM users;")
            return row is not None and row["count"] > 0
        except Exception as e:
            logger.error(f"Error checking user count: {e}")
            return False

    def authenticate(self, username: str, password: str) -> Tuple[bool, Optional[User], str]:
        """
        Verify credentials and start user session.
        Returns (success: bool, user: Optional[User], message: str).
        """
        username = (username or "").strip()
        if not username or not password:
            return False, None, "Please enter both username and password."

        try:
            query = """
                SELECT 
                    u.id, u.username, u.password_hash, u.full_name, u.email, u.phone,
                    u.is_active, u.role_id, r.name AS role_name
                FROM users u
                JOIN roles r ON u.role_id = r.id
                WHERE LOWER(u.username) = LOWER(?);
            """
            user_row = self.db.execute_one(query, (username,))

            if not user_row:
                logger.warning(f"Login failed: user '{username}' not found.")
                return False, None, "Invalid username or password."

            if not user_row["is_active"]:
                logger.warning(f"Login rejected: user '{username}' is deactivated.")
                return False, None, "This account is inactive. Please contact your manager."

            # Verify Bcrypt password hash
            if not verify_password(password, user_row["password_hash"]):
                logger.warning(f"Login failed: invalid password for user '{username}'.")
                return False, None, "Invalid username or password."

            # Load permissions
            user_id = user_row["id"]
            role_id = user_row["role_id"]
            permissions = self._load_user_permissions(user_id, role_id)

            # Construct User object
            user = User(
                id=user_id,
                username=user_row["username"],
                full_name=user_row["full_name"],
                role_id=role_id,
                role_name=user_row["role_name"],
                email=user_row["email"],
                phone=user_row["phone"],
                is_active=bool(user_row["is_active"]),
                last_login_at=datetime.now(),
                permissions=permissions,
            )

            # Update DB last_login_at & log audit
            self.db.execute_update(
                "UPDATE users SET last_login_at = CURRENT_TIMESTAMP WHERE id = ?;",
                (user_id,)
            )
            self._log_audit(user_id, "LOGIN", "User", str(user_id), None, {"status": "success"})

            # Store in app-wide session
            self.session.set_user(user)
            logger.info(f"User '{user.username}' successfully authenticated.")
            return True, user, "Login successful."

        except Exception as e:
            logger.error(f"Authentication exception: {e}", exc_info=True)
            return False, None, "An unexpected error occurred during login. Please try again."

    def complete_first_time_setup(
        self,
        store_name: str,
        store_address: str,
        store_phone: str,
        admin_username: str,
        admin_password: str,
        confirm_password: Optional[str] = None,
        full_name: str = "System Administrator",
        email: Optional[str] = None,
    ) -> Tuple[bool, Optional[User], str]:
        """
        Execute First-Time Setup Wizard:
        1. Validates inputs.
        2. Ensures 'admin' role exists with full permissions.
        3. Creates the first Admin user account (hashed with bcrypt).
        4. Updates store_settings with initial store configuration.
        5. Logs the created admin into the application session.
        """
        store_name = (store_name or "").strip()
        store_address = (store_address or "").strip()
        store_phone = (store_phone or "").strip()
        admin_username = (admin_username or "").strip()
        admin_password = admin_password or ""

        # Validations
        if not store_name:
            return False, None, "Store Name is required."
        if not admin_username:
            return False, None, "Admin Username is required."
        if len(admin_username) < 3:
            return False, None, "Admin Username must be at least 3 characters long."
        if not admin_password:
            return False, None, "Admin Password is required."
        if len(admin_password) < 6:
            return False, None, "Admin Password must be at least 6 characters long."
        if confirm_password is not None and admin_password != confirm_password:
            return False, None, "Passwords do not match."

        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()

                # 1. Ensure Admin Role exists
                cursor.execute("SELECT id FROM roles WHERE name = 'admin';")
                role_row = cursor.fetchone()
                if not role_row:
                    cursor.execute(
                        "INSERT INTO roles (name, description) VALUES ('admin', 'Full system access and administrative control');"
                    )
                    admin_role_id = cursor.lastrowid
                else:
                    admin_role_id = role_row["id"]

                # 2. Grant all existing permissions to admin role
                cursor.execute("SELECT id FROM permissions;")
                all_permissions = cursor.fetchall()
                for perm in all_permissions:
                    cursor.execute(
                        "INSERT OR IGNORE INTO role_permissions (role_id, permission_id) VALUES (?, ?);",
                        (admin_role_id, perm["id"]),
                    )

                # 3. Create Admin User
                hashed_pw = hash_password(admin_password)
                cursor.execute("""
                    INSERT INTO users (role_id, username, password_hash, full_name, email, phone, is_active)
                    VALUES (?, ?, ?, ?, ?, ?, 1);
                """, (
                    admin_role_id,
                    admin_username,
                    hashed_pw,
                    full_name or "System Administrator",
                    email or f"{admin_username}@store.local",
                    store_phone or None,
                ))
                new_user_id = cursor.lastrowid

                # 4. Save Store Settings
                settings_to_update = [
                    ("store_name", store_name, "string", "Store Business Name", "general"),
                    ("store_address", store_address, "string", "Store Physical Address", "general"),
                    ("store_phone", store_phone, "string", "Contact Telephone", "general"),
                ]
                for key, val, vtype, desc, cat in settings_to_update:
                    cursor.execute("""
                        INSERT INTO store_settings (setting_key, setting_value, value_type, description, category)
                        VALUES (?, ?, ?, ?, ?)
                        ON CONFLICT(setting_key) DO UPDATE SET 
                            setting_value = excluded.setting_value,
                            updated_at = CURRENT_TIMESTAMP;
                    """, (key, val, vtype, desc, cat))

                # 5. Audit Log
                cursor.execute("""
                    INSERT INTO audit_logs (user_id, action, entity_type, entity_id, new_value)
                    VALUES (?, 'SETUP_COMPLETED', 'System', 'initial_setup', ?);
                """, (new_user_id, json.dumps({
                    "store_name": store_name,
                    "admin_username": admin_username,
                    "created_at": datetime.now().isoformat(),
                })))

            # Construct user object and establish session
            permissions_set = self._load_user_permissions(new_user_id, admin_role_id)
            admin_user = User(
                id=new_user_id,
                username=admin_username,
                full_name=full_name or "System Administrator",
                role_id=admin_role_id,
                role_name="admin",
                email=email or f"{admin_username}@store.local",
                phone=store_phone or None,
                is_active=True,
                last_login_at=datetime.now(),
                permissions=permissions_set,
            )

            self.session.set_user(admin_user)
            logger.info(f"First-time setup completed successfully for '{store_name}' by admin '{admin_username}'")
            return True, admin_user, "Setup completed successfully."

        except Exception as e:
            logger.error(f"Error executing first-time setup: {e}", exc_info=True)
            return False, None, f"Failed to complete setup: {str(e)}"

    def _load_user_permissions(self, user_id: int, role_id: int) -> Set[str]:
        """Load combined set of role permissions and specific user permissions."""
        query = """
            SELECT DISTINCT p.code
            FROM permissions p
            LEFT JOIN role_permissions rp ON p.id = rp.permission_id AND rp.role_id = ?
            LEFT JOIN user_permissions up ON p.id = up.permission_id AND up.user_id = ?
            WHERE rp.id IS NOT NULL OR up.id IS NOT NULL;
        """
        rows = self.db.execute_query(query, (role_id, user_id))
        return {row["code"] for row in rows}

    def _log_audit(
        self,
        user_id: Optional[int],
        action: str,
        entity_type: str,
        entity_id: Optional[str],
        old_value: Optional[dict] = None,
        new_value: Optional[dict] = None,
    ) -> None:
        """Helper to write to audit_logs."""
        try:
            self.db.execute_update("""
                INSERT INTO audit_logs (user_id, action, entity_type, entity_id, old_value, new_value)
                VALUES (?, ?, ?, ?, ?, ?);
            """, (
                user_id,
                action,
                entity_type,
                entity_id,
                json.dumps(old_value) if old_value else None,
                json.dumps(new_value) if new_value else None,
            ))
        except Exception as e:
            logger.warning(f"Failed to record audit log: {e}")
