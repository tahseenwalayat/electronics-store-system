"""
Partner and Transaction Service for Customers, Suppliers, Sales, and Purchases.
"""

import logging
import datetime
import random
from typing import List, Dict, Optional, Tuple, Any
from data.db import DatabaseManager, get_db

logger = logging.getLogger(__name__)


class PartnerService:
    """
    Handles Customer and Supplier directory operations and quick transactions.
    """

    def __init__(self, db: Optional[DatabaseManager] = None):
        self.db = db or get_db()

    # -------------------------------------------------------------------------
    # CUSTOMERS
    # -------------------------------------------------------------------------

    def get_all_customers(self, query: str = "") -> List[Dict[str, Any]]:
        """Retrieve customers with optional search filtering."""
        sql = "SELECT * FROM customers WHERE is_active = 1"
        params = []
        if query.strip():
            sql += " AND (name LIKE ? OR COALESCE(phone, '') LIKE ? OR COALESCE(email, '') LIKE ?)"
            pat = f"%{query.strip()}%"
            params.extend([pat, pat, pat])
        sql += " ORDER BY name ASC;"
        try:
            return [dict(r) for r in self.db.execute_query(sql, tuple(params))]
        except Exception as e:
            logger.error(f"Error fetching customers: {e}")
            return []

    def create_customer(
        self,
        name: str,
        phone: Optional[str] = None,
        email: Optional[str] = None,
        address: Optional[str] = None,
        credit_limit: float = 0.0,
        notes: Optional[str] = None,
    ) -> Tuple[bool, Optional[int], str]:
        """Create a new customer profile."""
        name = name.strip()
        if not name:
            return False, None, "Customer Name is required."
        if credit_limit < 0:
            return False, None, "Credit limit cannot be negative."

        sql = """
            INSERT INTO customers (name, phone, email, address, credit_limit, notes, is_active)
            VALUES (?, ?, ?, ?, ?, ?, 1);
        """
        try:
            cid = self.db.execute_update(sql, (name, phone, email, address, credit_limit, notes))
            return True, cid, "Customer added successfully."
        except Exception as e:
            logger.error(f"Failed to create customer: {e}")
            return False, None, f"Database error: {e}"

    # -------------------------------------------------------------------------
    # SUPPLIERS
    # -------------------------------------------------------------------------

    def get_all_suppliers(self, query: str = "") -> List[Dict[str, Any]]:
        """Retrieve suppliers with optional search filtering."""
        sql = "SELECT * FROM suppliers WHERE is_active = 1"
        params = []
        if query.strip():
            sql += " AND (name LIKE ? OR COALESCE(contact_person, '') LIKE ? OR COALESCE(phone, '') LIKE ?)"
            pat = f"%{query.strip()}%"
            params.extend([pat, pat, pat])
        sql += " ORDER BY name ASC;"
        try:
            return [dict(r) for r in self.db.execute_query(sql, tuple(params))]
        except Exception as e:
            logger.error(f"Error fetching suppliers: {e}")
            return []

    def create_supplier(
        self,
        name: str,
        contact_person: Optional[str] = None,
        phone: Optional[str] = None,
        email: Optional[str] = None,
        address: Optional[str] = None,
        tax_number: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> Tuple[bool, Optional[int], str]:
        """Create a new supplier profile."""
        name = name.strip()
        if not name:
            return False, None, "Supplier Name is required."

        existing = self.db.execute_one("SELECT id FROM suppliers WHERE name = ?;", (name,))
        if existing:
            return False, None, f"Supplier '{name}' already exists."

        sql = """
            INSERT INTO suppliers (name, contact_person, phone, email, address, tax_number, notes, is_active)
            VALUES (?, ?, ?, ?, ?, ?, ?, 1);
        """
        try:
            sid = self.db.execute_update(sql, (name, contact_person, phone, email, address, tax_number, notes))
            return True, sid, "Supplier added successfully."
        except Exception as e:
            logger.error(f"Failed to create supplier: {e}")
            return False, None, f"Database error: {e}"

    # -------------------------------------------------------------------------
    # QUICK SALES & TRANSACTIONS
    # -------------------------------------------------------------------------

    def process_quick_sale(
        self,
        user_id: int,
        customer_id: Optional[int],
        guest_name: Optional[str],
        items: List[Dict[str, Any]],  # [{product_id, quantity, unit_price, discount, product_name, sku}]
        payment_method: str = "cash",
        notes: Optional[str] = None,
    ) -> Tuple[bool, Optional[str], str]:
        """
        Process a point-of-sale checkout:
        1. Validate stock availability.
        2. Create sale record with invoice number.
        3. Insert sale items and deduct inventory stock.
        4. Insert payment record.
        """
        if not items:
            return False, None, "Sale must contain at least one product."

        # Calculate totals
        subtotal = 0.0
        discount_total = 0.0
        for item in items:
            p_id = item["product_id"]
            qty = item["quantity"]
            price = item["unit_price"]
            disc = item.get("discount", 0.0)

            # Check stock
            p_row = self.db.execute_one("SELECT current_stock, name FROM products WHERE id = ?;", (p_id,))
            if not p_row:
                return False, None, f"Product ID {p_id} not found."
            if p_row["current_stock"] < qty:
                return False, None, f"Insufficient stock for '{p_row['name']}'. Available: {p_row['current_stock']}, Requested: {qty}"

            line_total = (price * qty) - disc
            subtotal += (price * qty)
            discount_total += disc

        # Tax calculation
        tax_row = self.db.execute_one("SELECT setting_value FROM store_settings WHERE setting_key = 'tax_rate';")
        tax_rate = float(tax_row["setting_value"]) if tax_row else 8.5
        tax_amount = round(((subtotal - discount_total) * (tax_rate / 100.0)), 2)
        total_amount = round(subtotal - discount_total + tax_amount, 2)

        # Generate unique Invoice Number
        now_str = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        rand_suffix = random.randint(100, 999)
        invoice_number = f"INV-{now_str}-{rand_suffix}"

        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()

                # Insert Sale
                cursor.execute("""
                    INSERT INTO sales (
                        invoice_number, customer_id, guest_name, user_id,
                        subtotal, tax_amount, discount_amount, total_amount,
                        paid_amount, change_amount, payment_status, status, notes
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0.0, 'paid', 'completed', ?);
                """, (
                    invoice_number,
                    customer_id if customer_id and customer_id > 0 else None,
                    guest_name if not customer_id else None,
                    user_id,
                    subtotal,
                    tax_amount,
                    discount_total,
                    total_amount,
                    total_amount,
                    notes,
                ))
                sale_id = cursor.lastrowid

                # Insert Sale Items & Deduct Stock
                for item in items:
                    p_id = item["product_id"]
                    qty = item["quantity"]
                    unit_p = item["unit_price"]
                    disc = item.get("discount", 0.0)
                    total_p = (unit_p * qty) - disc

                    cursor.execute("""
                        INSERT INTO sale_items (
                            sale_id, product_id, product_name, product_sku,
                            unit_price, quantity, discount_amount, total_price
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?);
                    """, (
                        sale_id,
                        p_id,
                        item.get("product_name", ""),
                        item.get("sku", ""),
                        unit_p,
                        qty,
                        disc,
                        total_p,
                    ))

                    # Deduct stock
                    cursor.execute("""
                        UPDATE products
                        SET current_stock = current_stock - ?, updated_at = CURRENT_TIMESTAMP
                        WHERE id = ?;
                    """, (qty, p_id))

                # Insert Payment
                cursor.execute("""
                    INSERT INTO sale_payments (sale_id, user_id, payment_method, amount, notes)
                    VALUES (?, ?, ?, ?, ?);
                """, (sale_id, user_id, payment_method, total_amount, "POS Checkout Payment"))

            logger.info(f"Successfully processed sale #{invoice_number} for total ${total_amount:.2f}")
            return True, invoice_number, f"Sale {invoice_number} processed successfully!"
        except Exception as e:
            logger.error(f"Failed to process sale: {e}", exc_info=True)
            return False, None, f"Transaction error: {e}"

    # -------------------------------------------------------------------------
    # QUICK PURCHASES
    # -------------------------------------------------------------------------

    def process_quick_purchase(
        self,
        user_id: int,
        supplier_id: int,
        items: List[Dict[str, Any]],  # [{product_id, quantity, unit_cost}]
        payment_method: str = "bank_transfer",
        notes: Optional[str] = None,
    ) -> Tuple[bool, Optional[str], str]:
        """
        Record an inbound purchase from a supplier and increment product inventory stock.
        """
        if not items:
            return False, None, "Purchase order must contain at least one item."
        if not supplier_id or supplier_id <= 0:
            return False, None, "Supplier selection is required."

        total_amount = sum(item["unit_cost"] * item["quantity"] for item in items)
        now_str = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        rand_suffix = random.randint(100, 999)
        po_number = f"PO-{now_str}-{rand_suffix}"

        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()

                # Insert Purchase
                cursor.execute("""
                    INSERT INTO purchases (
                        purchase_number, supplier_id, user_id,
                        subtotal, total_amount, paid_amount, payment_status,
                        status, payment_method, notes
                    ) VALUES (?, ?, ?, ?, ?, ?, 'paid', 'received', ?, ?);
                """, (po_number, supplier_id, user_id, total_amount, total_amount, total_amount, payment_method, notes))
                purchase_id = cursor.lastrowid

                # Insert Items and Increment Stock
                for item in items:
                    p_id = item["product_id"]
                    qty = item["quantity"]
                    cost = item["unit_cost"]
                    subtotal = cost * qty

                    cursor.execute("""
                        INSERT INTO purchase_items (
                            purchase_id, product_id, unit_cost, quantity, subtotal, received_quantity
                        ) VALUES (?, ?, ?, ?, ?, ?);
                    """, (purchase_id, p_id, cost, qty, subtotal, qty))

                    # Increment Stock and update cost_price
                    cursor.execute("""
                        UPDATE products
                        SET current_stock = current_stock + ?, cost_price = ?, updated_at = CURRENT_TIMESTAMP
                        WHERE id = ?;
                    """, (qty, cost, p_id))

            logger.info(f"Recorded purchase {po_number} from supplier #{supplier_id}")
            return True, po_number, f"Purchase {po_number} recorded successfully."
        except Exception as e:
            logger.error(f"Failed to record purchase: {e}", exc_info=True)
            return False, None, f"Database error: {e}"

    def get_all_purchases(self, query: str = "") -> List[Dict[str, Any]]:
        """Retrieve purchase order history."""
        sql = """
            SELECT 
                p.id,
                p.purchase_number,
                COALESCE(s.name, 'Unknown Supplier') AS supplier_name,
                p.purchase_date,
                p.total_amount,
                p.status,
                p.payment_status,
                p.payment_method
            FROM purchases p
            LEFT JOIN suppliers s ON p.supplier_id = s.id
        """
        params = []
        if query.strip():
            sql += " WHERE p.purchase_number LIKE ? OR s.name LIKE ?"
            pat = f"%{query.strip()}%"
            params.extend([pat, pat])
        sql += " ORDER BY p.purchase_date DESC, p.id DESC LIMIT 300;"
        try:
            return [dict(r) for r in self.db.execute_query(sql, tuple(params))]
        except Exception as e:
            logger.error(f"Error fetching purchases: {e}")
            return []

    def get_all_warranty_claims(self, query: str = "") -> List[Dict[str, Any]]:
        """Retrieve warranty claims history."""
        sql = """
            SELECT 
                w.id,
                w.claim_number,
                p.name AS product_name,
                COALESCE(c.name, 'Guest Customer') AS customer_name,
                w.serial_number,
                w.issue_description,
                w.status,
                w.claim_date
            FROM warranty_claims w
            LEFT JOIN products p ON w.product_id = p.id
            LEFT JOIN customers c ON w.customer_id = c.id
        """
        params = []
        if query.strip():
            sql += " WHERE w.claim_number LIKE ? OR p.name LIKE ? OR c.name LIKE ?"
            pat = f"%{query.strip()}%"
            params.extend([pat, pat, pat])
        sql += " ORDER BY w.claim_date DESC, w.id DESC LIMIT 300;"
        try:
            return [dict(r) for r in self.db.execute_query(sql, tuple(params))]
        except Exception as e:
            logger.error(f"Error fetching warranty claims: {e}")
            return []

    def get_all_returns(self, query: str = "") -> List[Dict[str, Any]]:
        """Retrieve sales returns history."""
        sql = """
            SELECT 
                r.id,
                r.return_number,
                s.invoice_number,
                COALESCE(c.name, 'Guest Customer') AS customer_name,
                r.total_refund_amount,
                r.refund_method,
                r.status,
                r.return_date
            FROM sales_returns r
            LEFT JOIN sales s ON r.sale_id = s.id
            LEFT JOIN customers c ON r.customer_id = c.id
        """
        params = []
        if query.strip():
            sql += " WHERE r.return_number LIKE ? OR s.invoice_number LIKE ? OR c.name LIKE ?"
            pat = f"%{query.strip()}%"
            params.extend([pat, pat, pat])
        sql += " ORDER BY r.return_date DESC, r.id DESC LIMIT 300;"
        try:
            return [dict(r) for r in self.db.execute_query(sql, tuple(params))]
        except Exception as e:
            logger.error(f"Error fetching returns: {e}")
            return []

