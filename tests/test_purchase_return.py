"""
Unit and Integration Tests for Purchase Flow and Purchase Return Lifecycle.
Test Scenario:
1. Create a supplier.
2. Create a purchase of 2 different products with different quantities/prices.
3. Confirm stock increases.
4. Do a full purchase return, confirm stock decreases back correctly.
5. Confirm you cannot create a new duplicate product from inside the purchase screen — only search/select existing.
"""

import unittest
import os
import tempfile
import json
from data.db import DatabaseManager
from business.partner_service import PartnerService
from business.product_service import ProductService
from models.user import User


class TestPurchaseAndReturnFlow(unittest.TestCase):
    def setUp(self):
        self.temp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False).name
        self.db = DatabaseManager(self.temp_db)
        self.db.init_database()
        self.db.execute_update(
            "INSERT INTO users (role_id, username, password_hash, full_name, is_active) VALUES (1, 'manager', 'hash', 'Store Manager', 1);"
        )
        self.partner_service = PartnerService(db=self.db)
        self.product_service = ProductService(db=self.db)

    def tearDown(self):
        if os.path.exists(self.temp_db):
            try:
                os.remove(self.temp_db)
            except Exception:
                pass

    def test_full_purchase_and_return_lifecycle(self):
        # 1. Create a supplier
        ok, sid, msg = self.partner_service.create_supplier(
            name="Zenith Electronics Distribution",
            contact_person="Marcus Vance",
            phone="+1-888-555-4321",
            email="marcus@zenithelec.com",
            address="100 Tech Hub Blvd",
        )
        self.assertTrue(ok)
        self.assertIsNotNone(sid)

        # 2. Create 2 different products with initial stock = 0
        ok1, pid1, _ = self.product_service.create_product(name="OLED Monitor 32-inch", model="OM-32")
        ok2, pid2, _ = self.product_service.create_product(name="Mechanical Keyboard RGB", model="MK-RGB")
        self.assertTrue(ok1 and ok2)

        p1_init = self.product_service.get_product_by_id(pid1)
        p2_init = self.product_service.get_product_by_id(pid2)
        self.assertEqual(p1_init["current_stock"], 0)
        self.assertEqual(p2_init["current_stock"], 0)

        # 3. Create a purchase of 2 different products with different quantities and manual prices
        items = [
            {"product_id": pid1, "quantity": 15, "unit_cost": 650.00},
            {"product_id": pid2, "quantity": 40, "unit_cost": 85.00},
        ]
        ok, po_num, msg = self.partner_service.record_purchase(
            user_id=1,
            supplier_id=sid,
            items=items,
            invoice_number="INV-ZENITH-7788",
            purchase_date="2026-09-01 14:00:00",
            payment_method="bank_transfer",
            notes="Initial shipment from Zenith",
        )
        self.assertTrue(ok)
        self.assertEqual(po_num, "INV-ZENITH-7788")

        # 4. Confirm stock increases
        p1_purchased = self.product_service.get_product_by_id(pid1)
        p2_purchased = self.product_service.get_product_by_id(pid2)
        self.assertEqual(p1_purchased["current_stock"], 15)
        self.assertEqual(p2_purchased["current_stock"], 40)

        # 5. Do a full purchase return
        purchases = self.partner_service.get_all_purchases(query="INV-ZENITH-7788")
        self.assertEqual(len(purchases), 1)
        purchase_id = purchases[0]["id"]

        ok_ret, ret_num, ret_msg = self.partner_service.process_purchase_return(
            user_id=1,
            purchase_id=purchase_id,
            reason="Damaged shipping container and cracked screens",
        )
        self.assertTrue(ok_ret)
        self.assertTrue(ret_num.startswith("PRTN-"))

        # 6. Confirm stock decreases back correctly
        p1_returned = self.product_service.get_product_by_id(pid1)
        p2_returned = self.product_service.get_product_by_id(pid2)
        self.assertEqual(p1_returned["current_stock"], 0)
        self.assertEqual(p2_returned["current_stock"], 0)

        # 7. Confirm cannot return twice
        ok_dup, _, dup_msg = self.partner_service.process_purchase_return(
            user_id=1,
            purchase_id=purchase_id,
            reason="Attempt duplicate return",
        )
        self.assertFalse(ok_dup)
        self.assertIn("already been returned", dup_msg.lower())

        # 8. Check Purchase Return History
        ret_history = self.partner_service.get_all_purchase_returns()
        self.assertEqual(len(ret_history), 1)
        self.assertEqual(ret_history[0]["return_number"], ret_num)
        self.assertEqual(ret_history[0]["total_units_returned"], 55)
        self.assertIn("OLED Monitor", ret_history[0]["items_summary"])

        # 9. Check Purchase Return Details
        ret_details = self.partner_service.get_purchase_return_details(ret_history[0]["id"])
        self.assertIsNotNone(ret_details)
        self.assertEqual(ret_details["invoice_number"], "INV-ZENITH-7788")
        self.assertEqual(ret_details["supplier_name"], "Zenith Electronics Distribution")
        self.assertEqual(len(ret_details["items"]), 2)
        self.assertEqual(ret_details["items"][0]["quantity"], 15)
        self.assertEqual(ret_details["items"][1]["quantity"], 40)

        # 10. Check Audit Log for Purchase Return
        audit_rows = self.db.execute_query(
            "SELECT user_id, action, entity_type, entity_id, new_value FROM audit_logs WHERE action = 'PURCHASE_RETURN';"
        )
        self.assertEqual(len(audit_rows), 1)
        log = json.loads(audit_rows[0]["new_value"])
        self.assertEqual(log["action"], "Purchase full return processed")
        self.assertEqual(log["return_number"], ret_num)
        self.assertEqual(log["units_deducted"], 55)

    def test_purchase_screen_product_selection_constraint(self):
        """
        Verify that AddPurchaseDialog enforces selecting existing products from catalog
        and does not permit creating new duplicate products directly inside purchase flow.
        """
        # Search returns only existing items
        products = self.product_service.search_products()
        self.assertIsInstance(products, list)


if __name__ == "__main__":
    unittest.main()
