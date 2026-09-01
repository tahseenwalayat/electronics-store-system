"""
Database Migration & Initialization Runner.
Applies schema.sql and incremental migrations idempotently.
Seeds initial baseline configuration (roles, permissions, admin user, settings).
"""

import os
import sys
import logging
import sqlite3
from typing import Optional, List, Tuple
import bcrypt

logger = logging.getLogger(__name__)

# Default base directory is the folder where this script resides (./data)
DATA_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_DB_PATH = os.path.join(DATA_DIR, "store.db")
SCHEMA_FILE = os.path.join(DATA_DIR, "schema.sql")
MIGRATIONS_DIR = os.path.join(DATA_DIR, "migrations")


def hash_password(password: str) -> str:
    """Hash password using bcrypt."""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


class MigrationRunner:
    """
    Idempotent migration runner and schema manager for SQLite database.
    """

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = os.path.abspath(db_path) if db_path else DEFAULT_DB_PATH
        self._ensure_directory()

    def _ensure_directory(self) -> None:
        """Ensure database directory exists."""
        db_dir = os.path.dirname(self.db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)

    def get_connection(self) -> sqlite3.Connection:
        """Create and configure a SQLite connection."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn

    def setup_migration_tracking(self, conn: sqlite3.Connection) -> None:
        """Ensure the migration tracking table exists."""
        conn.execute("""
            CREATE TABLE IF NOT EXISTS schema_migrations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                version TEXT NOT NULL UNIQUE,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        conn.commit()

    def get_applied_migrations(self, conn: sqlite3.Connection) -> List[str]:
        """Fetch list of already applied migration identifiers."""
        cursor = conn.cursor()
        cursor.execute("SELECT version FROM schema_migrations ORDER BY id ASC;")
        return [row["version"] for row in cursor.fetchall()]

    def record_migration(self, conn: sqlite3.Connection, version: str) -> None:
        """Record applied migration version."""
        conn.execute(
            "INSERT OR IGNORE INTO schema_migrations (version) VALUES (?);",
            (version,)
        )
        conn.commit()

    def apply_schema_file(self, conn: sqlite3.Connection) -> bool:
        """
        Apply the main schema.sql file idempotently.
        """
        if not os.path.exists(SCHEMA_FILE):
            logger.warning(f"Schema file not found at: {SCHEMA_FILE}")
            return False

        logger.info(f"Applying base schema from: {SCHEMA_FILE}")
        with open(SCHEMA_FILE, "r", encoding="utf-8") as f:
            schema_sql = f.read()

        cursor = conn.cursor()
        cursor.executescript(schema_sql)
        conn.commit()
        self.record_migration(conn, "000_base_schema.sql")
        logger.info("Base schema applied successfully.")
        return True

    def apply_incremental_migrations(self, conn: sqlite3.Connection) -> List[str]:
        """
        Apply pending SQL migration scripts found in data/migrations directory.
        """
        if not os.path.exists(MIGRATIONS_DIR):
            return []

        applied = set(self.get_applied_migrations(conn))
        migration_files = sorted([
            f for f in os.listdir(MIGRATIONS_DIR)
            if f.endswith(".sql") and os.path.isfile(os.path.join(MIGRATIONS_DIR, f))
        ])

        newly_applied = []
        for filename in migration_files:
            if filename not in applied:
                file_path = os.path.join(MIGRATIONS_DIR, filename)
                logger.info(f"Applying migration: {filename}")
                with open(file_path, "r", encoding="utf-8") as f:
                    migration_sql = f.read()

                cursor = conn.cursor()
                try:
                    cursor.executescript(migration_sql)
                except sqlite3.OperationalError as e:
                    if "duplicate column name" in str(e).lower():
                        logger.warning(f"Migration {filename} column already exists, skipping duplicate column error.")
                    else:
                        raise
                self.record_migration(conn, filename)
                newly_applied.append(filename)
                logger.info(f"Applied migration: {filename}")

        return newly_applied

    def seed_initial_data(self, conn: sqlite3.Connection) -> None:
        """
        Seed baseline initial data (roles, permissions, admin user, settings) idempotently.
        """
        cursor = conn.cursor()

        # 1. Seed Roles
        roles_data = [
            ("admin", "Full system access and administrative control"),
            ("manager", "Store operations, inventory management, reports and sales oversight"),
            ("cashier", "Point of sale cashier operations, customer lookup and invoicing"),
            ("technician", "Warranty claims processing, repairs, and technical inspections"),
        ]
        for role_name, desc in roles_data:
            cursor.execute(
                "INSERT OR IGNORE INTO roles (name, description) VALUES (?, ?);",
                (role_name, desc),
            )

        # 2. Seed Permissions (10 Modules x 3 Actions = 30 Permissions)
        modules_list = [
            ("sales", "Sales & POS"),
            ("purchases", "Purchases"),
            ("products", "Products"),
            ("stock_adjustment", "Stock Adjustment"),
            ("reports", "Reports & Analytics"),
            ("customers", "Customers"),
            ("suppliers", "Suppliers"),
            ("warranty", "Warranty Claims"),
            ("users", "Users & Permissions"),
            ("backup_restore", "Backup / Restore"),
        ]
        actions_list = [
            ("view", "View"),
            ("manage", "Create / Edit"),
            ("delete", "Delete (Admin Only)"),
        ]

        for mod_key, mod_name in modules_list:
            for act_key, act_name in actions_list:
                code = f"{mod_key}.{act_key}"
                perm_name = f"{mod_name} - {act_name}"
                desc = f"Permission to {act_name.lower()} in {mod_name} module"
                cursor.execute(
                    "INSERT OR IGNORE INTO permissions (code, name, description, module) VALUES (?, ?, ?, ?);",
                    (code, perm_name, desc, mod_key),
                )

        # 3. Seed Role Permissions
        # Admin gets all permissions
        cursor.execute("SELECT id FROM roles WHERE name = 'admin';")
        admin_role_row = cursor.fetchone()
        if admin_role_row:
            admin_role_id = admin_role_row["id"]
            cursor.execute("SELECT id FROM permissions;")
            all_perm_ids = [r["id"] for r in cursor.fetchall()]
            for pid in all_perm_ids:
                cursor.execute(
                    "INSERT OR IGNORE INTO role_permissions (role_id, permission_id) VALUES (?, ?);",
                    (admin_role_id, pid),
                )

        # Manager role permissions (all view/manage except users, backup_restore, and NO delete)
        cursor.execute("SELECT id FROM roles WHERE name = 'manager';")
        manager_role_row = cursor.fetchone()
        if manager_role_row:
            mgr_role_id = manager_role_row["id"]
            mgr_allowed = [
                "sales.view", "sales.manage",
                "purchases.view", "purchases.manage",
                "products.view", "products.manage",
                "stock_adjustment.view", "stock_adjustment.manage",
                "reports.view", "reports.manage",
                "customers.view", "customers.manage",
                "suppliers.view", "suppliers.manage",
                "warranty.view", "warranty.manage",
            ]
            for code in mgr_allowed:
                cursor.execute("SELECT id FROM permissions WHERE code = ?;", (code,))
                prow = cursor.fetchone()
                if prow:
                    cursor.execute(
                        "INSERT OR IGNORE INTO role_permissions (role_id, permission_id) VALUES (?, ?);",
                        (mgr_role_id, prow["id"]),
                    )

        # Cashier role permissions: Sales (view, manage), Customers (view, manage), Products (view only)
        cursor.execute("SELECT id FROM roles WHERE name = 'cashier';")
        cashier_role_row = cursor.fetchone()
        if cashier_role_row:
            csh_role_id = cashier_role_row["id"]
            csh_allowed = [
                "sales.view", "sales.manage",
                "customers.view", "customers.manage",
                "products.view",
            ]
            for code in csh_allowed:
                cursor.execute("SELECT id FROM permissions WHERE code = ?;", (code,))
                prow = cursor.fetchone()
                if prow:
                    cursor.execute(
                        "INSERT OR IGNORE INTO role_permissions (role_id, permission_id) VALUES (?, ?);",
                        (csh_role_id, prow["id"]),
                    )

        # 4. Default Store Settings
        default_settings = [
            ("store_name", "Electronics Store Pro", "string", "Store Business Name", "general"),
            ("store_phone", "+1 (555) 019-2834", "string", "Contact Telephone", "general"),
            ("store_email", "contact@electronicsstore.local", "string", "Contact Email Address", "general"),
            ("store_address", "100 Innovation Way, Tech City", "string", "Store Physical Address", "general"),
            ("currency_symbol", "$", "string", "Currency Display Symbol", "general"),
            ("currency_code", "USD", "string", "ISO Currency Code", "general"),
            ("tax_rate_percent", "8.5", "float", "Default Sales Tax Rate (%)", "tax"),
            ("tax_included_in_price", "false", "boolean", "Whether selling prices include tax", "tax"),
            ("invoice_prefix", "INV-", "string", "Prefix for Sales Invoices", "sales"),
            ("purchase_prefix", "PO-", "string", "Prefix for Purchase Orders", "purchases"),
            ("warranty_prefix", "WAR-", "string", "Prefix for Warranty Claims", "warranty"),
            ("low_stock_threshold_default", "5", "integer", "Default low stock alert threshold", "inventory"),
            ("receipt_footer_message", "Thank you for shopping with us! Please keep this receipt for warranty.", "string", "Receipt Footer Note", "sales"),
            ("auto_backup_enabled", "true", "boolean", "Enable automatic daily backups", "backup"),
        ]
        for key, value, vtype, desc, cat in default_settings:
            cursor.execute("""
                INSERT OR IGNORE INTO store_settings (setting_key, setting_value, value_type, description, category)
                VALUES (?, ?, ?, ?, ?);
            """, (key, value, vtype, desc, cat))

        conn.commit()
        logger.info("Baseline seed data verified/initialized.")

    def run(self) -> bool:
        """
        Run complete idempotent migration and initialization process.
        """
        self._ensure_directory()
        conn = self.get_connection()
        try:
            self.setup_migration_tracking(conn)
            self.apply_schema_file(conn)
            self.apply_incremental_migrations(conn)
            self.seed_initial_data(conn)
            logger.info(f"Database migrations completed successfully on: {self.db_path}")
            return True
        except Exception as e:
            logger.error(f"Database migration failed: {e}", exc_info=True)
            raise
        finally:
            conn.close()


def run_migrations(db_path: Optional[str] = None) -> bool:
    """Convenience function to run migrations."""
    runner = MigrationRunner(db_path)
    return runner.run()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    )
    custom_db = sys.argv[1] if len(sys.argv) > 1 else None
    run_migrations(custom_db)
