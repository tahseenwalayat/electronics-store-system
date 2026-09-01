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
        """Retrieve suppliers with purchase counts and optional search filtering."""
        sql = """
            SELECT 
                s.id,
                s.name,
                COALESCE(s.contact_person, '') AS contact_person,
                COALESCE(s.phone, '') AS phone,
                COALESCE(s.email, '') AS email,
                COALESCE(s.address, '') AS address,
                COALESCE(s.tax_number, '') AS tax_number,
                COALESCE(s.notes, '') AS notes,
                s.is_active,
                s.created_at,
                COUNT(p.id) AS total_purchases,
                COALESCE(SUM(p.total_amount), 0.0) AS total_purchase_amount
            FROM suppliers s
            LEFT JOIN purchases p ON p.supplier_id = s.id
            WHERE s.is_active = 1
        """
        params: List[Any] = []
        if query.strip():
            tokens = [t.strip() for t in query.strip().split() if t.strip()]
            for token in tokens:
                pat = f"%{token}%"
                sql += """
                    AND (
                        s.name LIKE ? OR 
                        COALESCE(s.contact_person, '') LIKE ? OR 
                        COALESCE(s.phone, '') LIKE ? OR 
                        COALESCE(s.email, '') LIKE ? OR
                        COALESCE(s.address, '') LIKE ?
                    )
                """
                params.extend([pat, pat, pat, pat, pat])
        sql += " GROUP BY s.id ORDER BY s.name ASC;"
        try:
            return [dict(r) for r in self.db.execute_query(sql, tuple(params))]
        except Exception as e:
            logger.error(f"Error fetching suppliers: {e}", exc_info=True)
            return []

    def get_supplier_by_id(self, supplier_id: int) -> Optional[Dict[str, Any]]:
        """Retrieve a single supplier by ID with aggregate purchase statistics."""
        sql = """
            SELECT 
                s.id,
                s.name,
                COALESCE(s.contact_person, '') AS contact_person,
                COALESCE(s.phone, '') AS phone,
                COALESCE(s.email, '') AS email,
                COALESCE(s.address, '') AS address,
                COALESCE(s.tax_number, '') AS tax_number,
                COALESCE(s.notes, '') AS notes,
                s.is_active,
                s.created_at,
                COUNT(p.id) AS total_purchases,
                COALESCE(SUM(p.total_amount), 0.0) AS total_purchase_amount
            FROM suppliers s
            LEFT JOIN purchases p ON p.supplier_id = s.id
            WHERE s.id = ? AND s.is_active = 1
            GROUP BY s.id;
        """
        try:
            row = self.db.execute_one(sql, (supplier_id,))
            return dict(row) if row else None
        except Exception as e:
            logger.error(f"Error fetching supplier #{supplier_id}: {e}", exc_info=True)
            return None

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
        contact_person = contact_person.strip() if contact_person else None
        phone = phone.strip() if phone else None
        email = email.strip() if email else None
        address = address.strip() if address else None
        tax_number = tax_number.strip() if tax_number else None
        notes = notes.strip() if notes else None

        if not name:
            return False, None, "Company / Shop Name is required."

        existing = self.db.execute_one(
            "SELECT id FROM suppliers WHERE name = ? COLLATE NOCASE AND is_active = 1;", (name,)
        )
        if existing:
            return False, None, f"A supplier or company named '{name}' already exists."

        sql = """
            INSERT INTO suppliers (name, contact_person, phone, email, address, tax_number, notes, is_active)
            VALUES (?, ?, ?, ?, ?, ?, ?, 1);
        """
        try:
            sid = self.db.execute_update(sql, (name, contact_person, phone, email, address, tax_number, notes))
            logger.info(f"Created supplier '{name}' (Contact: {contact_person}) with ID {sid}")
            return True, sid, f"Supplier '{name}' added successfully."
        except Exception as e:
            logger.error(f"Failed to create supplier: {e}", exc_info=True)
            return False, None, f"Database error: {e}"

    def update_supplier(
        self,
        supplier_id: int,
        name: str,
        contact_person: Optional[str] = None,
        phone: Optional[str] = None,
        email: Optional[str] = None,
        address: Optional[str] = None,
        tax_number: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> Tuple[bool, str]:
        """Update an existing supplier profile."""
        name = name.strip()
        contact_person = contact_person.strip() if contact_person else None
        phone = phone.strip() if phone else None
        email = email.strip() if email else None
        address = address.strip() if address else None
        tax_number = tax_number.strip() if tax_number else None
        notes = notes.strip() if notes else None

        if not name:
            return False, "Company / Shop Name is required."

        existing = self.db.execute_one(
            "SELECT id FROM suppliers WHERE name = ? COLLATE NOCASE AND id != ? AND is_active = 1;",
            (name, supplier_id),
        )
        if existing:
            return False, f"Another supplier or company named '{name}' already exists."

        sql = """
            UPDATE suppliers
            SET name = ?, contact_person = ?, phone = ?, email = ?, address = ?,
                tax_number = ?, notes = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?;
        """
        try:
            self.db.execute_update(sql, (name, contact_person, phone, email, address, tax_number, notes, supplier_id))
            logger.info(f"Updated supplier #{supplier_id} ('{name}')")
            return True, f"Supplier '{name}' updated successfully."
        except Exception as e:
            logger.error(f"Failed to update supplier #{supplier_id}: {e}", exc_info=True)
            return False, f"Database error: {e}"

    def delete_supplier(self, supplier_id: int) -> Tuple[bool, str]:
        """
        Delete or soft-delete a supplier.
        If the supplier has historical purchase orders, soft-delete by setting is_active = 0
        so that historical purchase orders remain completely intact.
        """
        supplier = self.get_supplier_by_id(supplier_id)
        if not supplier:
            return False, f"Supplier #{supplier_id} not found."

        s_name = supplier["name"]

        # Check if supplier has purchase records
        p_row = self.db.execute_one(
            "SELECT COUNT(*) AS count FROM purchases WHERE supplier_id = ?;", (supplier_id,)
        )
        purchase_count = p_row["count"] if p_row else 0

        try:
            if purchase_count > 0:
                # Soft delete
                self.db.execute_update(
                    "UPDATE suppliers SET is_active = 0, updated_at = CURRENT_TIMESTAMP WHERE id = ?;",
                    (supplier_id,),
                )
                logger.info(f"Archived supplier #{supplier_id} ('{s_name}') preserving {purchase_count} purchase orders.")
                return True, f"Supplier '{s_name}' archived. {purchase_count} historical purchase order(s) remain intact."
            else:
                # Hard delete if no purchases exist
                self.db.execute_update("DELETE FROM suppliers WHERE id = ?;", (supplier_id,))
                logger.info(f"Deleted supplier #{supplier_id} ('{s_name}')")
                return True, f"Supplier '{s_name}' deleted successfully."
        except Exception as e:
            logger.error(f"Failed to delete supplier #{supplier_id}: {e}", exc_info=True)
            return False, f"Database error: {e}"

    def get_supplier_purchase_history(self, supplier_id: int) -> List[Dict[str, Any]]:
        """
        Retrieve full purchase order history for a specific supplier.
        Returns purchase date, invoice/PO number, total amount, status, and summary of items.
        """
        sql = """
            SELECT 
                p.id,
                p.purchase_number,
                p.purchase_date,
                p.status,
                p.payment_status,
                p.payment_method,
                p.subtotal,
                p.tax_amount,
                p.discount_amount,
                p.total_amount,
                p.notes,
                COUNT(pi.id) AS total_line_items,
                COALESCE(SUM(pi.quantity), 0) AS total_units_received,
                GROUP_CONCAT(pi.quantity || 'x ' || prd.name, ', ') AS items_summary
            FROM purchases p
            LEFT JOIN purchase_items pi ON pi.purchase_id = p.id
            LEFT JOIN products prd ON pi.product_id = prd.id
            WHERE p.supplier_id = ?
            GROUP BY p.id
            ORDER BY p.purchase_date DESC, p.id DESC;
        """
        try:
            rows = self.db.execute_query(sql, (supplier_id,))
            results = []
            for r in rows:
                p_dict = dict(r)
                p_dict["items_summary"] = p_dict["items_summary"] or "No items listed"
                results.append(p_dict)
            return results
        except Exception as e:
            logger.error(f"Error fetching purchase history for supplier #{supplier_id}: {e}", exc_info=True)
            return []

    def get_purchase_details(self, purchase_id: int) -> Optional[Dict[str, Any]]:
        """Retrieve full details of a purchase order including itemized product list."""
        p_sql = """
            SELECT 
                p.id,
                p.purchase_number,
                p.purchase_date,
                p.supplier_id,
                s.name AS supplier_name,
                s.contact_person AS supplier_contact,
                p.status,
                p.payment_status,
                p.payment_method,
                p.subtotal,
                p.tax_amount,
                p.discount_amount,
                p.total_amount,
                p.paid_amount,
                p.notes
            FROM purchases p
            LEFT JOIN suppliers s ON p.supplier_id = s.id
            WHERE p.id = ?;
        """
        items_sql = """
            SELECT 
                pi.id,
                pi.product_id,
                prd.name AS product_name,
                COALESCE(prd.model, '') AS product_model,
                pi.unit_cost,
                pi.quantity,
                pi.subtotal,
                pi.received_quantity,
                pi.batch_number
            FROM purchase_items pi
            LEFT JOIN products prd ON pi.product_id = prd.id
            WHERE pi.purchase_id = ?
            ORDER BY pi.id ASC;
        """
        try:
            p_row = self.db.execute_one(p_sql, (purchase_id,))
            if not p_row:
                return None
            p_dict = dict(p_row)
            items_rows = self.db.execute_query(items_sql, (purchase_id,))
            p_dict["items"] = [dict(ir) for ir in items_rows]
            return p_dict
        except Exception as e:
            logger.error(f"Error fetching purchase #{purchase_id} details: {e}", exc_info=True)
            return None

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

    def record_purchase(
        self,
        user_id: int,
        supplier_id: int,
        items: List[Dict[str, Any]],  # [{product_id, quantity, unit_cost}]
        invoice_number: Optional[str] = None,
        purchase_date: Optional[str] = None,
        payment_method: str = "bank_transfer",
        notes: Optional[str] = None,
    ) -> Tuple[bool, Optional[str], str]:
        """
        Record a multi-line inbound purchase from a supplier:
        1. Validates supplier and items.
        2. Inserts purchase record with supplier invoice number and purchase date.
        3. Inserts each purchase_item with actual unit cost paid (never overwrites product default price).
        4. Increments products.current_stock for each item by quantity purchased.
        5. Writes audit_log entry: 'Purchase created' with user, invoice/purchase id, timestamp.
        """
        import json
        if not items:
            return False, None, "Purchase order must contain at least one product line item."
        if not supplier_id or supplier_id <= 0:
            return False, None, "Supplier selection is required."

        # Validate line items
        for idx, item in enumerate(items, 1):
            p_id = item.get("product_id")
            qty = item.get("quantity", 0)
            cost = item.get("unit_cost", 0.0)
            if not p_id or p_id <= 0:
                return False, None, f"Line #{idx}: Invalid product selection."
            if qty <= 0:
                return False, None, f"Line #{idx}: Quantity must be greater than 0."
            if cost < 0:
                return False, None, f"Line #{idx}: Purchase price cannot be negative."

        # Fetch supplier info
        supplier_row = self.db.execute_one("SELECT name FROM suppliers WHERE id = ?;", (supplier_id,))
        supplier_name = supplier_row["name"] if supplier_row else f"Supplier #{supplier_id}"

        # Resolve invoice / PO number
        now = datetime.datetime.now()
        clean_inv = invoice_number.strip() if invoice_number and invoice_number.strip() else None
        if not clean_inv:
            rand_suffix = random.randint(100, 999)
            final_invoice_num = f"PO-{now.strftime('%Y%m%d%H%M%S')}-{rand_suffix}"
        else:
            final_invoice_num = clean_inv

        # Check unique invoice number
        existing_po = self.db.execute_one(
            "SELECT id FROM purchases WHERE purchase_number = ? COLLATE NOCASE;", (final_invoice_num,)
        )
        if existing_po:
            return False, None, f"A purchase order or invoice with number '{final_invoice_num}' already exists."

        # Resolve purchase date
        final_date = purchase_date.strip() if purchase_date and purchase_date.strip() else now.strftime("%Y-%m-%d %H:%M:%S")

        total_amount = round(sum(item["unit_cost"] * item["quantity"] for item in items), 2)

        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()

                # 1. Insert Purchase
                cursor.execute("""
                    INSERT INTO purchases (
                        purchase_number, supplier_id, user_id, purchase_date,
                        subtotal, total_amount, paid_amount, payment_status,
                        status, payment_method, notes
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, 'paid', 'received', ?, ?);
                """, (
                    final_invoice_num,
                    supplier_id,
                    user_id,
                    final_date,
                    total_amount,
                    total_amount,
                    total_amount,
                    payment_method,
                    notes,
                ))
                purchase_id = cursor.lastrowid

                # 2. Insert Purchase Items & Increment Stock
                # Business Rule: Store actual price paid per item; NEVER overwrite default product prices.
                for item in items:
                    p_id = item["product_id"]
                    qty = int(item["quantity"])
                    cost = float(item["unit_cost"])
                    subtotal = round(cost * qty, 2)

                    cursor.execute("""
                        INSERT INTO purchase_items (
                            purchase_id, product_id, unit_cost, quantity, subtotal, received_quantity
                        ) VALUES (?, ?, ?, ?, ?, ?);
                    """, (purchase_id, p_id, cost, qty, subtotal, qty))

                    # Increment product stock ONLY (do NOT overwrite cost_price)
                    cursor.execute("""
                        UPDATE products
                        SET current_stock = current_stock + ?, updated_at = CURRENT_TIMESTAMP
                        WHERE id = ?;
                    """, (qty, p_id))

                # 3. Write Audit Log Entry
                audit_data = {
                    "action": "Purchase created",
                    "purchase_id": purchase_id,
                    "invoice_number": final_invoice_num,
                    "supplier_id": supplier_id,
                    "supplier_name": supplier_name,
                    "total_amount": total_amount,
                    "item_count": len(items),
                    "total_units": sum(int(i["quantity"]) for i in items),
                    "timestamp": now.isoformat(),
                }
                cursor.execute("""
                    INSERT INTO audit_logs (
                        user_id, action, entity_type, entity_id, new_value
                    ) VALUES (?, 'CREATE', 'Purchase', ?, ?);
                """, (
                    user_id,
                    str(purchase_id),
                    json.dumps(audit_data),
                ))

            logger.info(
                f"Purchase '{final_invoice_num}' created by user #{user_id} for supplier '{supplier_name}'. "
                f"Total ${total_amount:.2f} across {len(items)} items."
            )
            return True, final_invoice_num, f"Purchase '{final_invoice_num}' recorded successfully!"

        except Exception as e:
            logger.error(f"Failed to record purchase: {e}", exc_info=True)
            return False, None, f"Database transaction error: {e}"

    # Alias for backward compatibility
    process_quick_purchase = record_purchase

    def get_all_purchases(
        self,
        query: str = "",
        supplier_id: Optional[int] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 300,
    ) -> List[Dict[str, Any]]:
        """
        Retrieve purchase order history with multi-criteria filtering:
        - Text search on Invoice/PO Number or Supplier Name
        - Filter by specific supplier
        - Filter by date range (start_date, end_date)
        """
        sql = """
            SELECT 
                p.id,
                p.purchase_number,
                p.supplier_id,
                COALESCE(s.name, 'Unknown Supplier') AS supplier_name,
                p.purchase_date,
                p.subtotal,
                p.total_amount,
                p.status,
                p.payment_status,
                p.payment_method,
                p.notes,
                COALESCE(u.full_name, u.username, 'System') AS recorded_by,
                COUNT(pi.id) AS total_line_items,
                COALESCE(SUM(pi.quantity), 0) AS total_units_received,
                GROUP_CONCAT(pi.quantity || 'x ' || prd.name, ', ') AS items_summary
            FROM purchases p
            LEFT JOIN suppliers s ON p.supplier_id = s.id
            LEFT JOIN users u ON p.user_id = u.id
            LEFT JOIN purchase_items pi ON pi.purchase_id = p.id
            LEFT JOIN products prd ON pi.product_id = prd.id
            WHERE 1=1
        """
        params: List[Any] = []

        if query.strip():
            tokens = [t.strip() for t in query.strip().split() if t.strip()]
            for token in tokens:
                pat = f"%{token}%"
                sql += " AND (p.purchase_number LIKE ? OR s.name LIKE ?)"
                params.extend([pat, pat])

        if supplier_id and supplier_id > 0:
            sql += " AND p.supplier_id = ?"
            params.append(supplier_id)

        if start_date and start_date.strip():
            sql += " AND DATE(p.purchase_date) >= DATE(?)"
            params.append(start_date.strip())

        if end_date and end_date.strip():
            sql += " AND DATE(p.purchase_date) <= DATE(?)"
            params.append(end_date.strip())

        sql += " GROUP BY p.id ORDER BY p.purchase_date DESC, p.id DESC LIMIT ?"
        params.append(limit)

        try:
            rows = self.db.execute_query(sql, tuple(params))
            results = []
            for r in rows:
                p_dict = dict(r)
                p_dict["items_summary"] = p_dict["items_summary"] or "No items listed"
                results.append(p_dict)
            return results
        except Exception as e:
            logger.error(f"Error fetching purchases: {e}", exc_info=True)
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

    # -------------------------------------------------------------------------
    # PURCHASE RETURNS (FULL RETURNS ONLY)
    # -------------------------------------------------------------------------

    def process_purchase_return(
        self,
        user_id: int,
        purchase_id: int,
        reason: str = "Full purchase return to supplier",
    ) -> Tuple[bool, Optional[str], str]:
        """
        Execute a FULL return of a completed purchase transaction:
        - Only FULL return allowed (all items in the purchase are returned together).
        - Decreases products.current_stock for each item by the quantity purchased.
        - No financial refund/payable tracking (strictly inventory stock reduction).
        - Writes an audit_log entry.
        """
        import json
        if not purchase_id or purchase_id <= 0:
            return False, None, "Invalid purchase order identifier."

        # Fetch purchase record
        purchase = self.db.execute_one("""
            SELECT p.id, p.purchase_number, p.supplier_id, p.status, p.total_amount, s.name AS supplier_name
            FROM purchases p
            LEFT JOIN suppliers s ON p.supplier_id = s.id
            WHERE p.id = ?;
        """, (purchase_id,))

        if not purchase:
            return False, None, f"Purchase order #{purchase_id} was not found."

        if purchase["status"] == "cancelled":
            return False, None, f"Purchase '{purchase['purchase_number']}' has already been returned or cancelled."

        # Check existing return
        existing_return = self.db.execute_one(
            "SELECT return_number FROM purchase_returns WHERE purchase_id = ?;", (purchase_id,)
        )
        if existing_return:
            return False, None, f"Purchase '{purchase['purchase_number']}' has already been returned via return '{existing_return['return_number']}'."

        # Fetch all purchase items
        items = self.db.execute_query("""
            SELECT pi.id AS purchase_item_id, pi.product_id, pi.quantity, pi.unit_cost, pi.subtotal, prd.name AS product_name
            FROM purchase_items pi
            JOIN products prd ON pi.product_id = prd.id
            WHERE pi.purchase_id = ?;
        """, (purchase_id,))

        if not items:
            return False, None, f"No line items found for Purchase '{purchase['purchase_number']}'."

        now = datetime.datetime.now()
        rand_suffix = random.randint(100, 999)
        return_number = f"PRTN-{now.strftime('%Y%m%d%H%M%S')}-{rand_suffix}"
        clean_reason = reason.strip() if reason and reason.strip() else "Full purchase return to supplier"
        total_units = sum(int(i["quantity"]) for i in items)

        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()

                # 1. Insert into purchase_returns
                cursor.execute("""
                    INSERT INTO purchase_returns (
                        return_number, purchase_id, supplier_id, user_id,
                        return_date, total_refund_amount, reason, status
                    ) VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP, 0.0, ?, 'completed');
                """, (
                    return_number,
                    purchase_id,
                    purchase["supplier_id"],
                    user_id,
                    clean_reason,
                ))
                return_id = cursor.lastrowid

                # 2. Insert items and decrease stock
                for item in items:
                    p_id = item["product_id"]
                    qty = int(item["quantity"])
                    unit_cost = float(item["unit_cost"])
                    line_cost = float(item["subtotal"])

                    cursor.execute("""
                        INSERT INTO purchase_return_items (
                            purchase_return_id, purchase_item_id, product_id,
                            quantity, unit_cost, total_cost, reason
                        ) VALUES (?, ?, ?, ?, ?, ?, ?);
                    """, (
                        return_id,
                        item["purchase_item_id"],
                        p_id,
                        qty,
                        unit_cost,
                        line_cost,
                        clean_reason,
                    ))

                    # Decrease inventory stock back to previous level
                    cursor.execute("""
                        UPDATE products
                        SET current_stock = current_stock - ?, updated_at = CURRENT_TIMESTAMP
                        WHERE id = ?;
                    """, (qty, p_id))

                # 3. Update purchase status
                note_append = f" [FULLY RETURNED: {return_number}]"
                cursor.execute("""
                    UPDATE purchases
                    SET status = 'cancelled',
                        notes = COALESCE(notes, '') || ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?;
                """, (note_append, purchase_id))

                # 4. Write audit log entry
                audit_payload = {
                    "action": "Purchase full return processed",
                    "return_number": return_number,
                    "purchase_id": purchase_id,
                    "invoice_number": purchase["purchase_number"],
                    "supplier_id": purchase["supplier_id"],
                    "supplier_name": purchase["supplier_name"],
                    "reason": clean_reason,
                    "items_count": len(items),
                    "units_deducted": total_units,
                    "user_id": user_id,
                    "timestamp": now.isoformat(),
                }
                cursor.execute("""
                    INSERT INTO audit_logs (
                        user_id, action, entity_type, entity_id, new_value
                    ) VALUES (?, 'PURCHASE_RETURN', 'PurchaseReturn', ?, ?);
                """, (
                    user_id,
                    str(return_id),
                    json.dumps(audit_payload),
                ))

            logger.info(
                f"Full Purchase Return '{return_number}' processed for Purchase #{purchase_id} "
                f"({purchase['purchase_number']}). Deducted {total_units} units across {len(items)} products."
            )
            return True, return_number, f"Full purchase return '{return_number}' processed successfully! Inventory stock has been decreased."

        except Exception as e:
            logger.error(f"Error processing purchase return: {e}", exc_info=True)
            return False, None, f"Database transaction error: {e}"

    def get_all_purchase_returns(
        self,
        query: str = "",
        supplier_id: Optional[int] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 300,
    ) -> List[Dict[str, Any]]:
        """
        Retrieve complete history of purchase returns with multi-criteria filtering.
        """
        sql = """
            SELECT 
                pr.id,
                pr.return_number,
                pr.purchase_id,
                p.purchase_number AS invoice_number,
                pr.supplier_id,
                COALESCE(s.name, 'Unknown Supplier') AS supplier_name,
                pr.return_date,
                pr.reason,
                pr.status,
                COALESCE(u.full_name, u.username, 'System') AS processed_by,
                COUNT(pri.id) AS total_line_items,
                COALESCE(SUM(pri.quantity), 0) AS total_units_returned,
                GROUP_CONCAT(pri.quantity || 'x ' || prd.name, ', ') AS items_summary
            FROM purchase_returns pr
            LEFT JOIN purchases p ON pr.purchase_id = p.id
            LEFT JOIN suppliers s ON pr.supplier_id = s.id
            LEFT JOIN users u ON pr.user_id = u.id
            LEFT JOIN purchase_return_items pri ON pri.purchase_return_id = pr.id
            LEFT JOIN products prd ON pri.product_id = prd.id
            WHERE 1=1
        """
        params: List[Any] = []

        if query.strip():
            tokens = [t.strip() for t in query.strip().split() if t.strip()]
            for token in tokens:
                pat = f"%{token}%"
                sql += " AND (pr.return_number LIKE ? OR p.purchase_number LIKE ? OR s.name LIKE ?)"
                params.extend([pat, pat, pat])

        if supplier_id and supplier_id > 0:
            sql += " AND pr.supplier_id = ?"
            params.append(supplier_id)

        if start_date and start_date.strip():
            sql += " AND DATE(pr.return_date) >= DATE(?)"
            params.append(start_date.strip())

        if end_date and end_date.strip():
            sql += " AND DATE(pr.return_date) <= DATE(?)"
            params.append(end_date.strip())

        sql += " GROUP BY pr.id ORDER BY pr.return_date DESC, pr.id DESC LIMIT ?"
        params.append(limit)

        try:
            rows = self.db.execute_query(sql, tuple(params))
            results = []
            for r in rows:
                r_dict = dict(r)
                r_dict["items_summary"] = r_dict["items_summary"] or "No items listed"
                results.append(r_dict)
            return results
        except Exception as e:
            logger.error(f"Error fetching purchase returns: {e}", exc_info=True)
            return []

    def get_purchase_return_details(self, return_id: int) -> Optional[Dict[str, Any]]:
        """Fetch full header and line item details for a single purchase return."""
        sql_head = """
            SELECT 
                pr.id,
                pr.return_number,
                pr.purchase_id,
                p.purchase_number AS invoice_number,
                pr.supplier_id,
                COALESCE(s.name, 'Unknown Supplier') AS supplier_name,
                pr.return_date,
                pr.reason,
                pr.status,
                COALESCE(u.full_name, u.username, 'System') AS processed_by
            FROM purchase_returns pr
            LEFT JOIN purchases p ON pr.purchase_id = p.id
            LEFT JOIN suppliers s ON pr.supplier_id = s.id
            LEFT JOIN users u ON pr.user_id = u.id
            WHERE pr.id = ?;
        """
        row = self.db.execute_one(sql_head, (return_id,))
        if not row:
            return None

        ret_dict = dict(row)

        sql_items = """
            SELECT 
                pri.id,
                pri.product_id,
                prd.name AS product_name,
                prd.model AS product_model,
                pri.quantity,
                pri.unit_cost,
                pri.total_cost,
                pri.reason
            FROM purchase_return_items pri
            LEFT JOIN products prd ON pri.product_id = prd.id
            WHERE pri.purchase_return_id = ?;
        """
        item_rows = self.db.execute_query(sql_items, (return_id,))
        ret_dict["items"] = [dict(i) for i in item_rows]
        return ret_dict


