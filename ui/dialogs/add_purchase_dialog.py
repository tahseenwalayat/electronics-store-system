"""
Add Inbound Purchase Dialog.
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
from PySide6.QtGui import QFont
from business.product_service import ProductService
from business.partner_service import PartnerService
from business.session import get_session
from business.permissions import check_permission


class AddPurchaseDialog(QDialog):
    """
    Dialog to record supplier purchase orders and automatically update inventory stock.
    """

    def __init__(self, product_service: ProductService, partner_service: PartnerService, parent=None):
        super().__init__(parent)
        self.product_service = product_service
        self.partner_service = partner_service
        self.session = get_session()
        self.items: List[Dict[str, Any]] = []

        self.setWindowTitle("Add Inbound Purchase — Electronics Store System")
        self.resize(740, 580)
        self.setMinimumSize(640, 480)

        self._setup_ui()
        self._load_suppliers()
        self._load_products()

    def _setup_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(18, 16, 18, 16)
        main_layout.setSpacing(12)

        # Supplier Section
        sup_group = QGroupBox("Supplier & Inbound Order")
        sup_layout = QHBoxLayout(sup_group)
        sup_layout.setSpacing(12)

        sup_layout.addWidget(QLabel("Supplier *:"))
        self.cmb_supplier = QComboBox()
        self.cmb_supplier.setMinimumWidth(320)
        sup_layout.addWidget(self.cmb_supplier, stretch=2)

        sup_layout.addWidget(QLabel("Payment Method:"))
        self.cmb_payment = QComboBox()
        self.cmb_payment.addItems(["Bank Transfer", "Cash", "Credit Card", "Cheque"])
        sup_layout.addWidget(self.cmb_payment, stretch=1)

        main_layout.addWidget(sup_group)

        # Add Item Section
        item_group = QGroupBox("Add Restock Items")
        item_layout = QHBoxLayout(item_group)
        item_layout.setSpacing(10)

        self.cmb_product = QComboBox()
        self.cmb_product.setMinimumWidth(280)
        self.cmb_product.currentIndexChanged.connect(self._on_product_changed)
        item_layout.addWidget(self.cmb_product, stretch=3)

        item_layout.addWidget(QLabel("Cost ($):"))
        self.spn_cost = QDoubleSpinBox()
        self.spn_cost.setRange(0.0, 999999.99)
        self.spn_cost.setDecimals(2)
        self.spn_cost.setPrefix("$ ")
        self.spn_cost.setFixedWidth(100)
        item_layout.addWidget(self.spn_cost)

        item_layout.addWidget(QLabel("Qty:"))
        self.spn_qty = QSpinBox()
        self.spn_qty.setRange(1, 9999)
        self.spn_qty.setValue(10)
        self.spn_qty.setFixedWidth(70)
        item_layout.addWidget(self.spn_qty)

        self.btn_add_item = QPushButton("➕ Add Item")
        self.btn_add_item.setStyleSheet("background-color: #2563eb; color: white; padding: 6px 12px; font-weight: bold; border-radius: 4px;")
        self.btn_add_item.clicked.connect(self._add_item_to_table)
        item_layout.addWidget(self.btn_add_item)

        main_layout.addWidget(item_group)

        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["SKU", "Product Name", "Unit Cost", "Qty", "Total Cost"])
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.verticalHeader().setVisible(False)
        main_layout.addWidget(self.table, stretch=1)

        # Total Bar
        bot_frame = QFrame()
        bot_frame.setStyleSheet("background-color: #f8fafc; border: 1px solid #e2e8f0; border-radius: 6px; padding: 8px;")
        bot_layout = QHBoxLayout(bot_frame)
        bot_layout.addStretch()
        bot_layout.addWidget(QLabel("<b>Total Purchase Cost:</b>"))
        self.lbl_total = QLabel("<b>$0.00</b>")
        self.lbl_total.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        self.lbl_total.setStyleSheet("color: #0284c7;")
        bot_layout.addWidget(self.lbl_total)
        main_layout.addWidget(bot_frame)

        # Actions
        btn_layout = QHBoxLayout()
        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(self.btn_cancel)

        btn_layout.addStretch()

        self.btn_save = QPushButton("📦 Record Purchase & Restock")
        self.btn_save.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        self.btn_save.setStyleSheet("background-color: #0284c7; color: white; padding: 8px 20px; font-weight: bold; border-radius: 6px;")
        self.btn_save.clicked.connect(self._on_save_clicked)
        btn_layout.addWidget(self.btn_save)

        main_layout.addLayout(btn_layout)

    def _load_suppliers(self) -> None:
        suppliers = self.partner_service.get_all_suppliers()
        for s in suppliers:
            contact = f" ({s['contact_person']})" if s.get("contact_person") else ""
            self.cmb_supplier.addItem(f"🏭 {s['name']}{contact}", s["id"])

    def _load_products(self) -> None:
        self.raw_products = self.product_service.search_products(limit=500)
        self.cmb_product.clear()
        self.cmb_product.addItem("— Select product to restock —", None)
        for p in self.raw_products:
            self.cmb_product.addItem(f"{p['name']} (SKU: {p['sku']})", p)

    def _on_product_changed(self) -> None:
        p = self.cmb_product.currentData()
        if p and isinstance(p, dict):
            self.spn_cost.setValue(float(p.get("cost_price", 0.0)))

    def _add_item_to_table(self) -> None:
        p = self.cmb_product.currentData()
        if not p or not isinstance(p, dict):
            QMessageBox.warning(self, "Select Product", "Please select a product from the list.")
            return

        cost = self.spn_cost.value()
        qty = self.spn_qty.value()

        existing = next((i for i in self.items if i["product_id"] == p["id"]), None)
        if existing:
            existing["quantity"] += qty
            existing["unit_cost"] = cost
        else:
            self.items.append({
                "product_id": p["id"],
                "sku": p["sku"],
                "name": p["name"],
                "unit_cost": cost,
                "quantity": qty,
            })

        self._refresh_table()

    def _refresh_table(self) -> None:
        self.table.setRowCount(len(self.items))
        total = 0.0
        for r_idx, itm in enumerate(self.items):
            line = itm["unit_cost"] * itm["quantity"]
            total += line
            self.table.setItem(r_idx, 0, QTableWidgetItem(itm["sku"]))
            self.table.setItem(r_idx, 1, QTableWidgetItem(itm["name"]))
            
            c_item = QTableWidgetItem(f"${itm['unit_cost']:.2f}")
            c_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.table.setItem(r_idx, 2, c_item)

            q_item = QTableWidgetItem(str(itm["quantity"]))
            q_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(r_idx, 3, q_item)

            tot_item = QTableWidgetItem(f"${line:.2f}")
            tot_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.table.setItem(r_idx, 4, tot_item)

        self.lbl_total.setText(f"<b>${total:.2f}</b>")

    def _on_save_clicked(self) -> None:
        if not check_permission("purchases.manage", parent=self, action_name="record purchases"):
            return

        if not self.items:
            QMessageBox.warning(self, "No Items", "Please add at least one item to the purchase order.")
            return

        supplier_id = self.cmb_supplier.currentData()
        if not supplier_id:
            QMessageBox.warning(self, "Select Supplier", "Please select a supplier.")
            return

        user_id = self.session.current_user.id if self.session.current_user else 1

        success, po_number, msg = self.partner_service.process_quick_purchase(
            user_id=user_id,
            supplier_id=supplier_id,
            items=self.items,
            payment_method=self.cmb_payment.currentText().lower().replace(" ", "_"),
        )

        if not success:
            QMessageBox.critical(self, "Purchase Error", msg)
            return

        QMessageBox.information(
            self,
            "Purchase Recorded",
            f"✅ Purchase Order <b>{po_number}</b> recorded successfully!\nProduct stock has been updated.",
        )
        self.accept()
