"""
Demo Data Seeder for Electronics Store System.
Populates standard store settings, staff accounts, categories, brands, and products.
"""

import sys
import os
import sqlite3
import bcrypt

DATA_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(DATA_DIR, "store.db")


def hash_pw(password: str) -> str:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def seed_demo_data():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    cursor = conn.cursor()

    print("Seeding demo data into:", DB_PATH)

    # 1. Ensure Roles Exist
    roles = {
        "admin": "Full system access and administrative control",
        "manager": "Store operations, inventory management, reports and sales oversight",
        "cashier": "Point of sale cashier operations, customer lookup and invoicing",
        "technician": "Warranty claims processing, repairs, and technical inspections",
    }
    role_ids = {}
    for role_name, desc in roles.items():
        cursor.execute("INSERT OR IGNORE INTO roles (name, description) VALUES (?, ?);", (role_name, desc))
        cursor.execute("SELECT id FROM roles WHERE name = ?;", (role_name,))
        role_ids[role_name] = cursor.fetchone()[0]

    # 2. Seed Permissions
    modules_list = [
        ("sales", "Sales & POS"),
        ("purchases", "Purchases"),
        ("products", "Products"),
        ("stock_adjustment", "Stock Adjustment"),
        ("reports", "Reports & Analytics"),
        ("customers", "Customers"),
        ("suppliers", "Suppliers"),
        ("returns", "Returns & RMA"),
        ("warranty", "Warranty Claims"),
        ("users", "Users & Permissions"),
        ("backup_restore", "Backup / Restore"),
        ("settings", "Store Settings"),
    ]
    actions_list = [("view", "View"), ("manage", "Create / Edit"), ("delete", "Delete (Admin Only)")]

    for mod_key, mod_name in modules_list:
        for act_key, act_name in actions_list:
            code = f"{mod_key}.{act_key}"
            perm_name = f"{mod_name} - {act_name}"
            desc = f"Permission to {act_name.lower()} in {mod_name} module"
            cursor.execute(
                "INSERT OR IGNORE INTO permissions (code, name, description, module) VALUES (?, ?, ?, ?);",
                (code, perm_name, desc, mod_key),
            )

    # Grant all permissions to Admin
    cursor.execute("SELECT id FROM permissions;")
    all_perm_ids = [r["id"] for r in cursor.fetchall()]
    for pid in all_perm_ids:
        cursor.execute(
            "INSERT OR IGNORE INTO role_permissions (role_id, permission_id) VALUES (?, ?);",
            (role_ids["admin"], pid),
        )

    # Manager permissions
    mgr_perms = [
        "sales.view", "sales.manage",
        "purchases.view", "purchases.manage",
        "products.view", "products.manage",
        "stock_adjustment.view", "stock_adjustment.manage",
        "reports.view", "reports.manage",
        "customers.view", "customers.manage",
        "suppliers.view", "suppliers.manage",
        "returns.view", "returns.manage",
        "warranty.view", "warranty.manage",
        "settings.view", "settings.manage",
    ]
    for code in mgr_perms:
        cursor.execute("SELECT id FROM permissions WHERE code = ?;", (code,))
        row = cursor.fetchone()
        if row:
            cursor.execute(
                "INSERT OR IGNORE INTO role_permissions (role_id, permission_id) VALUES (?, ?);",
                (role_ids["manager"], row["id"]),
            )

    # Cashier permissions
    cashier_perms = [
        "sales.view", "sales.manage",
        "customers.view", "customers.manage",
        "products.view",
        "returns.view", "returns.manage",
        "warranty.view",
    ]
    for code in cashier_perms:
        cursor.execute("SELECT id FROM permissions WHERE code = ?;", (code,))
        row = cursor.fetchone()
        if row:
            cursor.execute(
                "INSERT OR IGNORE INTO role_permissions (role_id, permission_id) VALUES (?, ?);",
                (role_ids["cashier"], row["id"]),
            )

    # 3. Seed Users
    users_data = [
        ("admin", "admin123", "System Administrator", "admin@electra.com", "admin", "+1-555-0101"),
        ("manager", "manager123", "Sarah Jenkins", "sarah@electra.com", "manager", "+1-555-0102"),
        ("cashier", "cashier123", "Alex Rivera", "alex@electra.com", "cashier", "+1-555-0103"),
    ]

    for username, pwd, full_name, email, role, phone in users_data:
        pw_hash = hash_pw(pwd)
        cursor.execute("""
            INSERT OR IGNORE INTO users (role_id, username, password_hash, full_name, email, phone, is_active)
            VALUES (?, ?, ?, ?, ?, ?, 1);
        """, (role_ids[role], username, pw_hash, full_name, email, phone))

    # 4. Store Settings
    settings = [
        ("store_name", "ElectraStore Pro", "string", "Store Business Name", "general"),
        ("store_address", "100 Innovation Parkway, Suite 400, Tech City", "string", "Physical Address", "general"),
        ("store_phone", "+1 (800) 555-TECH", "string", "Contact Phone", "general"),
        ("store_email", "support@electrastore.com", "string", "Contact Email", "general"),
        ("currency_symbol", "$", "string", "Currency Symbol", "finance"),
        ("tax_rate", "8.5", "float", "Default Sales Tax %", "finance"),
    ]
    for key, val, vtype, desc, cat in settings:
        cursor.execute("""
            INSERT INTO store_settings (setting_key, setting_value, value_type, description, category)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(setting_key) DO UPDATE SET setting_value = excluded.setting_value;
        """, (key, val, vtype, desc, cat))

    # 5. Brands
    brands = [
        ("Apple", "Premium consumer electronics and computers", "https://apple.com"),
        ("Samsung", "Electronics, smartphones, displays and appliances", "https://samsung.com"),
        ("Sony", "Audio, television, gaming and imaging equipment", "https://sony.com"),
        ("Dell", "Personal computers, monitors and enterprise hardware", "https://dell.com"),
        ("Logitech", "High performance computer peripherals and accessories", "https://logitech.com"),
        ("ASUS", "Laptops, motherboards, graphics and gaming monitors", "https://asus.com"),
    ]
    for name, desc, website in brands:
        cursor.execute("INSERT OR IGNORE INTO brands (name, description, website) VALUES (?, ?, ?);", (name, desc, website))

    # 6. Categories
    categories = [
        ("Smartphones & Tablets", "Mobile devices and cellular tablets"),
        ("Laptops & Desktops", "High performance laptops, ultrabooks and PCs"),
        ("Audio & Headphones", "Noise cancelling headphones, earbuds and speakers"),
        ("Computer Accessories", "Keyboards, mice, docks and cables"),
        ("Monitors & Displays", "4K, UltraWide and Gaming OLED displays"),
    ]
    for name, desc in categories:
        cursor.execute("INSERT OR IGNORE INTO categories (name, description) VALUES (?, ?);", (name, desc))

    # 7. Products
    cursor.execute("SELECT id, name FROM brands;")
    brand_map = {r["name"]: r["id"] for r in cursor.fetchall()}

    cursor.execute("SELECT id, name FROM categories;")
    cat_map = {r["name"]: r["id"] for r in cursor.fetchall()}

    products = [
        ("SKU-APP-IP15P", "195949001011", "Apple iPhone 15 Pro", "A3106 128GB Titanium", "Latest Apple flagship with A17 Pro chip and Titanium finish", cat_map["Smartphones & Tablets"], brand_map["Apple"], 799.00, 999.00, 24, 5, 12),
        ("SKU-SAM-S24U", "887276802012", "Samsung Galaxy S24 Ultra", "SM-S928B 256GB", "Galaxy AI smartphone with S-Pen and 200MP camera", cat_map["Smartphones & Tablets"], brand_map["Samsung"], 880.00, 1199.00, 18, 4, 12),
        ("SKU-APP-MBA15", "195949002022", "MacBook Air 15-inch M3", "A3114 Midnight 16GB", "Lightweight laptop with Apple Silicon M3 processor", cat_map["Laptops & Desktops"], brand_map["Apple"], 1150.00, 1499.00, 12, 3, 12),
        ("SKU-DEL-XPS15", "884116403033", "Dell XPS 15 Laptop", "XPS 9530 Core i9 32GB", "Premium creator laptop with 3.5K OLED touch display", cat_map["Laptops & Desktops"], brand_map["Dell"], 1650.00, 2199.00, 8, 2, 24),
        ("SKU-SNY-WH1000", "027242924044", "Sony Wireless Headphones", "WH-1000XM5 Black", "Industry leading active noise cancellation wireless headset", cat_map["Audio & Headphones"], brand_map["Sony"], 260.00, 399.99, 4, 5, 12),
        ("SKU-LOG-MXM3S", "097855175055", "Logitech Performance Mouse", "MX Master 3S Graphite", "Quiet clicks and 8K DPI any-surface tracking sensor", cat_map["Computer Accessories"], brand_map["Logitech"], 65.00, 99.99, 45, 10, 24),
        ("SKU-ASU-PG32", "192876506066", "ASUS Gaming Monitor", "ROG Swift PG32UCDM 4K", "32-inch 4K QD-OLED 240Hz 0.03ms gaming monitor", cat_map["Monitors & Displays"], brand_map["ASUS"], 920.00, 1299.00, 0, 3, 36),
    ]

    for sku, barcode, name, model, desc, cat_id, brand_id, cost, sell, stock, alert, warranty in products:
        cursor.execute("""
            INSERT INTO products (sku, barcode, name, model, description, category_id, brand_id, cost_price, selling_price, current_stock, min_stock_alert, warranty_period_months)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(sku) DO UPDATE SET 
                name = excluded.name,
                model = excluded.model,
                description = excluded.description,
                category_id = excluded.category_id,
                brand_id = excluded.brand_id,
                current_stock = excluded.current_stock,
                min_stock_alert = excluded.min_stock_alert,
                warranty_period_months = excluded.warranty_period_months;
        """, (sku, barcode, name, model, desc, cat_id, brand_id, cost, sell, stock, alert, warranty))

    # 8. Customers
    customers = [
        ("Michael Chang", "+1-555-0211", "michael.c@example.com", "742 Evergreen Terrace, Tech City", 120, 2000.0, 0.0),
        ("Elena Rostova", "+1-555-0212", "elena.r@example.com", "456 Oak Avenue, Tech City", 45, 1000.0, 0.0),
        ("David Miller", "+1-555-0213", "david.m@example.com", "89 Pine Road, Metro Area", 310, 5000.0, 0.0),
    ]
    for name, phone, email, address, pts, limit, balance in customers:
        cursor.execute("""
            INSERT OR IGNORE INTO customers (name, phone, email, address, loyalty_points, credit_limit, current_balance)
            VALUES (?, ?, ?, ?, ?, ?, ?);
        """, (name, phone, email, address, pts, limit, balance))

    # 9. Suppliers
    suppliers = [
        ("Global Tech Distribution Inc.", "Robert Vance", "+1-800-555-0301", "sales@globaltechdist.com", "100 Industrial Pkwy, Chicago, IL", "US-TAX-998877"),
        ("Silicon Logistics Direct", "Anita Patel", "+1-800-555-0302", "orders@siliconlogistics.com", "55 Supply Chain Blvd, Dallas, TX", "US-TAX-665544"),
    ]
    for name, contact, phone, email, address, tax in suppliers:
        cursor.execute("""
            INSERT OR IGNORE INTO suppliers (name, contact_person, phone, email, address, tax_number)
            VALUES (?, ?, ?, ?, ?, ?);
        """, (name, contact, phone, email, address, tax))

    conn.commit()
    conn.close()
    print("Demo data seeded successfully!")


if __name__ == "__main__":
    seed_demo_data()
