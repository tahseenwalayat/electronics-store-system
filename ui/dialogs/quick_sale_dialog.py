"""
Quick Sale / POS Checkout Dialog.
"""

from typing import Optional, Dict, Any, List
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QLabel,
    QLineEdit,
    QDoubleSpinBox,
    QSpinBox,
    QComboBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QMessageBox,
    QGroupBox,
    QFrame,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QColor
from business.product_service import ProductService
from business.partner_service import PartnerService
from business.session import get_session
from business.permissions import check_permission


class QuickSaleDialog(QDialog):
    """
    New Sale Checkout Dialog. Allows rapid order entry, customer selection, and payment processing.
    """

    def __init__(self, product_service: ProductService, partner_service: PartnerService, preselected_product_id: Optional[int] = None, parent=None):
        super().__init__(parent)
        self.product_service = product_service
        self.partner_service = partner_service
        self.session = get_session()
        self.cart_items: List[Dict[str, Any]] = []

        self.setWindowTitle("New Sale (Point of Sale) — Electronics Store System")
        self.resize(780, 620)
        self.setMinimumSize(680, 520)

        self._setup_ui()
        self._load_customers()
        self._load_products(preselected_product_id)

    def _setup_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(18, 16, 18, 16)
        main_layout.setSpacing(12)

        # Top Bar: Customer & Header
        cust_group = QGroupBox("Customer & Billing")
        cust_layout = QHBoxLayout(cust_group)
        cust_layout.setSpacing(12)

        cust_layout.addWidget(QLabel("Customer:"))
        self.cmb_customer = QComboBox()
        self.cmb_customer.setMinimumWidth(280)
        self.cmb_customer.addItem("👤 Walk-in / Guest Customer", 0)
        cust_layout.addWidget(self.cmb_customer)

        self.txt_guest_name = QLineEdit()
        self.txt_guest_name.setPlaceholderText("Guest Customer Name (Optional)")
        cust_layout.addWidget(self.txt_guest_name)

        main_layout.addWidget(cust_group)

        # Add Item Section
        item_group = QGroupBox("Select Product to Add")
        item_layout = QHBoxLayout(item_group)
        item_layout.setSpacing(10)

        self.cmb_product = QComboBox()
        self.cmb_product.setMinimumWidth(320)
        self.cmb_product.currentIndexChanged.connect(self._on_product_selection_changed)
        item_layout.addWidget(self.cmb_product, stretch=3)

        self.lbl_stock_hint = QLabel("Stock: -")
        self.lbl_stock_hint.setStyleSheet("font-weight: bold; color: #0284c7;")
        item_layout.addWidget(self.lbl_stock_hint)

        item_layout.addWidget(QLabel("Qty:"))
        self.spn_qty = QSpinBox()
        self.spn_qty.setRange(1, 999)
        self.spn_qty.setValue(1)
        self.spn_qty.setFixedWidth(70)
        item_layout.addWidget(self.spn_qty)

        self.btn_add_to_cart = QPushButton("➕ Add to Sale")
        self.btn_add_to_cart.setStyleSheet("""
            background-color: #2563eb; color: white; padding: 6px 14px; border-radius: 4px; font-weight: bold;
        """)
        self.btn_add_to_cart.clicked.connect(self._add_selected_product_to_cart)
        item_layout.addWidget(self.btn_add_to_cart)

        main_layout.addWidget(item_group)

        # Cart Table
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["SKU", "Product Name", "Unit Price", "Qty", "Subtotal", "Action"])
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        main_layout.addWidget(self.table, stretch=1)

        # Bottom Summary & Checkout
        bottom_frame = QFrame()
        bottom_frame.setStyleSheet("background-color: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 10px;")
        bottom_layout = QHBoxLayout(bottom_frame)

        # Left: Payment Method
        pay_layout = QVBoxLayout()
        pay_layout.addWidget(QLabel("Payment Method:"))
        self.cmb_payment = QComboBox()
        self.cmb_payment.addItems(["Cash", "Credit Card", "Debit Card", "Bank Transfer", "Store Credit"])
        pay_layout.addWidget(self.cmb_payment)
        bottom_layout.addLayout(pay_layout)

        bottom_layout.addStretch()

        # Right: Total breakdown
        totals_grid = QGridLayout()
        totals_grid.setHorizontalSpacing(16)
        totals_grid.setVerticalSpacing(4)

        totals_grid.addWidget(QLabel("Subtotal:"), 0, 0)
        self.lbl_subtotal = QLabel("$0.00")
        self.lbl_subtotal.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        totals_grid.addWidget(self.lbl_subtotal, 0, 1, Qt.AlignmentFlag.AlignRight)

        totals_grid.addWidget(QLabel("Tax (8.5%):"), 1, 0)
        self.lbl_tax = QLabel("$0.00")
        totals_grid.addWidget(self.lbl_tax, 1, 1, Qt.AlignmentFlag.AlignRight)

        totals_grid.addWidget(QLabel("<b>Total Amount:</b>"), 2, 0)
        self.lbl_total = QLabel("<b>$0.00</b>")
        self.lbl_total.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        self.lbl_total.setStyleSheet("color: #16a34a;")
        totals_grid.addWidget(self.lbl_total, 2, 1, Qt.AlignmentFlag.AlignRight)

        bottom_layout.addLayout(totals_grid)
        main_layout.addWidget(bottom_frame)

        # Action Buttons
        btn_layout = QHBoxLayout()
        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(self.btn_cancel)

        btn_layout.addStretch()

        self.btn_checkout = QPushButton("💳 Complete Sale & Checkout")
        self.btn_checkout.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        self.btn_checkout.setStyleSheet("""
            QPushButton {
                background-color: #16a34a;
                color: #ffffff;
                padding: 10px 24px;
                border-radius: 6px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #15803d;
            }
        """)
        self.btn_checkout.clicked.connect(self._on_checkout_clicked)
        btn_layout.addWidget(self.btn_checkout)

        main_layout.addLayout(btn_layout)

    def _load_customers(self) -> None:
        customers = self.partner_service.get_all_customers()
        for c in customers:
            phone_str = f" ({c['phone']})" if c.get("phone") else ""
            self.cmb_customer.addItem(f"👤 {c['name']}{phone_str}", c["id"])

    def _load_products(self, preselected_id: Optional[int] = None) -> None:
        self.raw_products = self.product_service.search_products(limit=500)
        self.cmb_product.clear()
        self.cmb_product.addItem("— Select a product to add —", None)
        select_idx = 0
        for idx, p in enumerate(self.raw_products):
            stock_info = f"[{p['current_stock']} in stock]"
            price_info = f"${p['selling_price']:.2f}"
            self.cmb_product.addItem(f"{p['name']} — {price_info} {stock_info}", p)
            if preselected_id and p["id"] == preselected_id:
                select_idx = idx + 1

        if select_idx > 0:
            self.cmb_product.setCurrentIndex(select_idx)

    def _on_product_selection_changed(self) -> None:
        p = self.cmb_product.currentData()
        if p and isinstance(p, dict):
            stock = p["current_stock"]
            self.lbl_stock_hint.setText(f"Stock: {stock} {p.get('unit', 'pcs')}")
            if stock <= 0:
                self.lbl_stock_hint.setStyleSheet("font-weight: bold; color: #dc2626;")
            elif stock <= p.get("min_stock_alert", 5):
                self.lbl_stock_hint.setStyleSheet("font-weight: bold; color: #d97706;")
            else:
                self.lbl_stock_hint.setStyleSheet("font-weight: bold; color: #16a34a;")
            self.spn_qty.setMaximum(max(1, stock))
        else:
            self.lbl_stock_hint.setText("Stock: -")
            self.lbl_stock_hint.setStyleSheet("color: #64748b;")

    def _add_selected_product_to_cart(self) -> None:
        p = self.cmb_product.currentData()
        if not p or not isinstance(p, dict):
            QMessageBox.warning(self, "Select Product", "Please select a product from the list.")
            return

        qty = self.spn_qty.value()
        stock = p["current_stock"]

        # Check existing in cart
        existing_item = next((item for item in self.cart_items if item["product_id"] == p["id"]), None)
        current_cart_qty = existing_item["quantity"] if existing_item else 0

        if current_cart_qty + qty > stock:
            QMessageBox.warning(
                self,
                "Insufficient Stock",
                f"Cannot add {qty} units. Only {stock - current_cart_qty} units remaining in stock.",
            )
            return

        if existing_item:
            existing_item["quantity"] += qty
        else:
            self.cart_items.append({
                "product_id": p["id"],
                "sku": p["sku"],
                "product_name": p["name"],
                "unit_price": p["selling_price"],
                "quantity": qty,
                "discount": 0.0,
            })

        self._refresh_cart_table()

    def _refresh_cart_table(self) -> None:
        self.table.setRowCount(len(self.cart_items))
        subtotal = 0.0

        for row_idx, item in enumerate(self.cart_items):
            line_sub = item["unit_price"] * item["quantity"]
            subtotal += line_sub

            self.table.setItem(row_idx, 0, QTableWidgetItem(item["sku"]))
            self.table.setItem(row_idx, 1, QTableWidgetItem(item["product_name"]))
            
            p_item = QTableWidgetItem(f"${item['unit_price']:.2f}")
            p_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.table.setItem(row_idx, 2, p_item)

            q_item = QTableWidgetItem(str(item["quantity"]))
            q_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row_idx, 3, q_item)

            sub_item = QTableWidgetItem(f"${line_sub:.2f}")
            sub_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.table.setItem(row_idx, 4, sub_item)

            # Remove button
            btn_remove = QPushButton("✕ Remove")
            btn_remove.setStyleSheet("background-color: #fee2e2; color: #dc2626; border: none; border-radius: 3px; padding: 3px 6px; font-size: 11px;")
            btn_remove.clicked.connect(lambda _, idx=row_idx: self._remove_cart_item(idx))
            self.table.setCellWidget(row_idx, 5, btn_remove)
            self.table.setRowHeight(row_idx, 36)

        tax_amount = round(subtotal * 0.085, 2)
        total_amount = subtotal + tax_amount

        self.lbl_subtotal.setText(f"${subtotal:.2f}")
        self.lbl_tax.setText(f"${tax_amount:.2f}")
        self.lbl_total.setText(f"<b>${total_amount:.2f}</b>")

    def _remove_cart_item(self, idx: int) -> None:
        if 0 <= idx < len(self.cart_items):
            self.cart_items.pop(idx)
            self._refresh_cart_table()

    def _on_checkout_clicked(self) -> None:
        if not check_permission("sales.manage", parent=self, action_name="process sales"):
            return

        if not self.cart_items:
            QMessageBox.warning(self, "Empty Sale", "Please add at least one product to the sale.")
            return

        customer_id = self.cmb_customer.currentData()
        guest_name = self.txt_guest_name.text().strip() or "Guest Customer"
        pay_method_map = {
            "Cash": "cash",
            "Credit Card": "credit_card",
            "Debit Card": "debit_card",
            "Bank Transfer": "bank_transfer",
            "Store Credit": "store_credit",
        }
        payment_method = pay_method_map.get(self.cmb_payment.currentText(), "cash")

        user_id = self.session.current_user.id if self.session.current_user else 1

        success, invoice_num, msg = self.partner_service.process_quick_sale(
            user_id=user_id,
            customer_id=customer_id if customer_id > 0 else None,
            guest_name=guest_name if customer_id == 0 else None,
            items=self.cart_items,
            payment_method=payment_method,
        )

        if not success:
            QMessageBox.critical(self, "Sale Failed", msg)
            return

        QMessageBox.information(
            self,
            "Sale Completed",
            f"🎉 Sale finalized successfully!\n\nInvoice Number: <b>{invoice_num}</b>\nPayment Method: <b>{self.cmb_payment.currentText()}</b>\nStatus: <b>Paid & Stock Updated</b>",
        )
        self.accept()
