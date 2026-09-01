"""
Add Inbound Purchase Dialog.
Workflow:
1. Select Supplier
2. Select Existing Product (searched from catalog, no new duplicate creation)
3. Enter Quantity
4. Enter Purchase Price (manual, per-unit, entered fresh every time — NOT pulled from any saved default)
5. Enter Supplier Invoice Number
6. Select Purchase Date
7. Save Purchase (increases products.current_stock, stores actual unit price paid, logs audit entry)
"""

from typing import Optional, Dict, Any, List
import datetime
from PySide6.QtWidgets import (
    QDialog,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QLabel,
    QLineEdit,
    QDoubleSpinBox,
    QSpinBox,
    QComboBox,
    QDateEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QMessageBox,
    QGroupBox,
    QFrame,
)
from PySide6.QtCore import Qt, QDate
from PySide6.QtGui import QFont, QColor

from business.product_service import ProductService
from business.partner_service import PartnerService
from business.session import get_session
from business.permissions import check_permission


class AddPurchaseDialog(QDialog):
    """
    Inbound Purchase Creation Dialog.
    Multi-item purchase order entry that increments inventory stock.
    """

    def __init__(self, product_service: ProductService, partner_service: PartnerService, parent=None):
        super().__init__(parent)
        self.product_service = product_service
        self.partner_service = partner_service
        self.session = get_session()
        self.items: List[Dict[str, Any]] = []

        self.setWindowTitle("📦 New Inbound Purchase Order — Electronics Store System")
        self.resize(860, 640)
        self.setMinimumSize(780, 540)

        self._setup_ui()
        self._load_suppliers()
        self._load_products()

    def _setup_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 18, 20, 18)
        main_layout.setSpacing(14)

        # ---------------------------------------------------------------------
        # 1. SUPPLIER & INVOICE DETAILS SECTION
        # ---------------------------------------------------------------------
        meta_group = QGroupBox("1. Supplier & Invoice Information")
        meta_group.setStyleSheet("QGroupBox { font-weight: bold; color: #0f172a; font-size: 12px; }")
        meta_grid = QGridLayout(meta_group)
        meta_grid.setContentsMargins(14, 14, 14, 12)
        meta_grid.setHorizontalSpacing(14)
        meta_grid.setVerticalSpacing(10)

        # Supplier Dropdown
        lbl_sup = QLabel("Supplier *:")
        lbl_sup.setStyleSheet("font-weight: 600; color: #334155;")
        meta_grid.addWidget(lbl_sup, 0, 0)

        self.cmb_supplier = QComboBox()
        self.cmb_supplier.setFixedHeight(32)
        meta_grid.addWidget(self.cmb_supplier, 0, 1)

        # Supplier Invoice Number
        lbl_inv = QLabel("Supplier Invoice # *:")
        lbl_inv.setStyleSheet("font-weight: 600; color: #334155;")
        meta_grid.addWidget(lbl_inv, 0, 2)

        self.txt_invoice_num = QLineEdit()
        self.txt_invoice_num.setPlaceholderText("e.g. INV-98432 or PO-2026-001")
        self.txt_invoice_num.setFixedHeight(32)
        self.txt_invoice_num.setStyleSheet("padding: 4px 8px; border: 1px solid #cbd5e1; border-radius: 5px;")
        meta_grid.addWidget(self.txt_invoice_num, 0, 3)

        # Purchase Date
        lbl_date = QLabel("Purchase Date *:")
        lbl_date.setStyleSheet("font-weight: 600; color: #334155;")
        meta_grid.addWidget(lbl_date, 1, 0)

        self.date_purchase = QDateEdit()
        self.date_purchase.setCalendarPopup(True)
        self.date_purchase.setDate(QDate.currentDate())
        self.date_purchase.setDisplayFormat("yyyy-MM-dd")
        self.date_purchase.setFixedHeight(32)
        meta_grid.addWidget(self.date_purchase, 1, 1)

        # Payment Method
        lbl_pay = QLabel("Payment Method:")
        lbl_pay.setStyleSheet("font-weight: 600; color: #334155;")
        meta_grid.addWidget(lbl_pay, 1, 2)

        self.cmb_payment = QComboBox()
        self.cmb_payment.addItems(["Bank Transfer", "Cash", "Credit Card", "Cheque", "Store Credit"])
        self.cmb_payment.setFixedHeight(32)
        meta_grid.addWidget(self.cmb_payment, 1, 3)

        main_layout.addWidget(meta_group)

        # ---------------------------------------------------------------------
        # 2. SELECT PRODUCT & ADD LINE ITEM SECTION
        # ---------------------------------------------------------------------
        item_group = QGroupBox("2. Add Inbound Products (Multi-Line Items)")
        item_group.setStyleSheet("QGroupBox { font-weight: bold; color: #0f172a; font-size: 12px; }")
        item_layout = QHBoxLayout(item_group)
        item_layout.setContentsMargins(14, 14, 14, 12)
        item_layout.setSpacing(10)

        # Product Selector
        prod_col = QVBoxLayout()
        prod_col.setSpacing(3)
        lbl_prod = QLabel("Select Existing Product *:")
        lbl_prod.setStyleSheet("font-weight: 600; color: #334155; font-size: 11px;")
        prod_col.addWidget(lbl_prod)

        self.cmb_product = QComboBox()
        self.cmb_product.setFixedHeight(34)
        self.cmb_product.setMinimumWidth(320)
        self.cmb_product.setPlaceholderText("Search and select product from catalog...")
        prod_col.addWidget(self.cmb_product)
        item_layout.addLayout(prod_col, stretch=3)

        # Purchase Price (Manual fresh input every time - NOT pulled from saved default)
        cost_col = QVBoxLayout()
        cost_col.setSpacing(3)
        lbl_cost = QLabel("Unit Purchase Price ($) *:")
        lbl_cost.setStyleSheet("font-weight: 600; color: #334155; font-size: 11px;")
        cost_col.addWidget(lbl_cost)

        self.spn_cost = QDoubleSpinBox()
        self.spn_cost.setRange(0.0, 9999999.99)
        self.spn_cost.setDecimals(2)
        self.spn_cost.setPrefix("$ ")
        self.spn_cost.setValue(0.00)  # Manual entry: fresh every time, not auto-pulled
        self.spn_cost.setFixedHeight(34)
        self.spn_cost.setFixedWidth(130)
        cost_col.addWidget(self.spn_cost)
        item_layout.addLayout(cost_col, stretch=1)

        # Quantity
        qty_col = QVBoxLayout()
        qty_col.setSpacing(3)
        lbl_qty = QLabel("Quantity *:")
        lbl_qty.setStyleSheet("font-weight: 600; color: #334155; font-size: 11px;")
        qty_col.addWidget(lbl_qty)

        self.spn_qty = QSpinBox()
        self.spn_qty.setRange(1, 999999)
        self.spn_qty.setValue(1)
        self.spn_qty.setFixedHeight(34)
        self.spn_qty.setFixedWidth(90)
        qty_col.addWidget(self.spn_qty)
        item_layout.addLayout(qty_col, stretch=1)

        # Add Line Button
        btn_col = QVBoxLayout()
        btn_col.setSpacing(3)
        btn_col.addWidget(QLabel(""))  # align spacer
        self.btn_add_item = QPushButton("➕ Add Line Item")
        self.btn_add_item.setFixedHeight(34)
        self.btn_add_item.setStyleSheet("""
            QPushButton {
                background-color: #2563eb; color: white; padding: 6px 14px; font-weight: bold; border-radius: 5px; font-size: 12px;
            }
            QPushButton:hover {
                background-color: #1d4ed8;
            }
        """)
        self.btn_add_item.clicked.connect(self._add_item_to_table)
        btn_col.addWidget(self.btn_add_item)
        item_layout.addLayout(btn_col)

        main_layout.addWidget(item_group)

        # ---------------------------------------------------------------------
        # 3. PURCHASE ITEMS DATA TABLE
        # ---------------------------------------------------------------------
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            "Product Name", "Model", "Category", "Unit Cost Paid", "Qty", "Line Subtotal"
        ])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.verticalHeader().setVisible(False)
        self.table.setStyleSheet("""
            QTableWidget {
                background-color: #ffffff;
                border: 1px solid #e2e8f0;
                border-radius: 8px;
                gridline-color: #f1f5f9;
            }
            QHeaderView::section {
                background-color: #f8fafc;
                color: #475569;
                font-weight: 600;
                padding: 7px;
                border: none;
                border-bottom: 1.5px solid #cbd5e1;
            }
        """)
        main_layout.addWidget(self.table, stretch=1)

        # ---------------------------------------------------------------------
        # 4. RUNNING TOTAL & SUMMARY BAR
        # ---------------------------------------------------------------------
        summary_frame = QFrame()
        summary_frame.setStyleSheet("background-color: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 8px 14px;")
        sum_layout = QHBoxLayout(summary_frame)
        sum_layout.setContentsMargins(8, 4, 8, 4)

        self.lbl_items_summary = QLabel("0 line item(s) • 0 total units")
        self.lbl_items_summary.setStyleSheet("color: #64748b; font-weight: 500; font-size: 12px;")
        sum_layout.addWidget(self.lbl_items_summary)

        sum_layout.addStretch()

        self.btn_remove_selected = QPushButton("🗑️ Remove Selected Item")
        self.btn_remove_selected.setStyleSheet("background-color: #fee2e2; color: #991b1b; border: 1px solid #fecaca; border-radius: 4px; padding: 4px 10px; font-size: 11px;")
        self.btn_remove_selected.clicked.connect(self._remove_selected_item)
        sum_layout.addWidget(self.btn_remove_selected)

        sum_layout.addSpacing(20)

        sum_layout.addWidget(QLabel("<b>Total Purchase Cost:</b>"))
        self.lbl_total = QLabel("<b>$0.00</b>")
        self.lbl_total.setFont(QFont("Segoe UI", 15, QFont.Weight.Bold))
        self.lbl_total.setStyleSheet("color: #15803d;")
        sum_layout.addWidget(self.lbl_total)

        main_layout.addWidget(summary_frame)

        # ---------------------------------------------------------------------
        # 5. BOTTOM ACTIONS BAR
        # ---------------------------------------------------------------------
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)

        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.setStyleSheet("background-color: #f1f5f9; color: #334155; border: 1px solid #cbd5e1; padding: 8px 20px; border-radius: 6px; font-weight: 500;")
        self.btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(self.btn_cancel)

        btn_layout.addStretch()

        self.btn_save = QPushButton("📦 Save Purchase & Increase Stock")
        self.btn_save.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        self.btn_save.setStyleSheet("""
            QPushButton {
                background-color: #16a34a;
                color: #ffffff;
                padding: 9px 24px;
                border-radius: 6px;
                border: none;
            }
            QPushButton:hover {
                background-color: #15803d;
            }
        """)
        self.btn_save.clicked.connect(self._on_save_clicked)
        btn_layout.addWidget(self.btn_save)

        main_layout.addLayout(btn_layout)

    def _load_suppliers(self) -> None:
        self.cmb_supplier.clear()
        self.cmb_supplier.addItem("— Select Supplier —", 0)
        suppliers = self.partner_service.get_all_suppliers()
        for s in suppliers:
            contact = f" (Rep: {s['contact_person']})" if s.get("contact_person") else ""
            self.cmb_supplier.addItem(f"🏭 {s['name']}{contact}", s["id"])

    def _load_products(self) -> None:
        self.raw_products = self.product_service.search_products(limit=500)
        self.cmb_product.clear()
        self.cmb_product.addItem("— Select Product from Catalog —", None)
        for p in self.raw_products:
            stock_info = f"[Stock: {p['current_stock']}]"
            model_info = f" ({p['model']})" if p.get("model") and p["model"] != "—" else ""
            label = f"{p['name']}{model_info} {stock_info}"
            self.cmb_product.addItem(label, p)

    def _add_item_to_table(self) -> None:
        p = self.cmb_product.currentData()
        if not p or not isinstance(p, dict):
            QMessageBox.warning(self, "Select Product", "Please select an existing product from the catalog.")
            self.cmb_product.setFocus()
            return

        cost = self.spn_cost.value()
        if cost <= 0.0:
            reply = QMessageBox.question(
                self,
                "Confirm Zero Unit Price",
                f"The unit purchase price for <b>'{p['name']}'</b> is entered as <b>$0.00</b>.\n\nDo you wish to continue?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply != QMessageBox.StandardButton.Yes:
                self.spn_cost.setFocus()
                return

        qty = self.spn_qty.value()

        # Check if already added in table -> update line or add separate
        existing = next((i for i in self.items if i["product_id"] == p["id"]), None)
        if existing:
            existing["quantity"] += qty
            existing["unit_cost"] = cost
        else:
            self.items.append({
                "product_id": p["id"],
                "name": p["name"],
                "model": p.get("model") or "—",
                "category_name": p.get("category_name") or "General",
                "unit_cost": cost,
                "quantity": qty,
            })

        self._refresh_table()

        # Reset inputs for next item
        self.cmb_product.setCurrentIndex(0)
        self.spn_cost.setValue(0.00)
        self.spn_qty.setValue(1)
        self.cmb_product.setFocus()

    def _remove_selected_item(self) -> None:
        selected_rows = self.table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.information(self, "Remove Item", "Please select an item row in the table to remove.")
            return

        row_idx = selected_rows[0].row()
        if 0 <= row_idx < len(self.items):
            del self.items[row_idx]
            self._refresh_table()

    def _refresh_table(self) -> None:
        self.table.setRowCount(len(self.items))
        total_amount = 0.0
        total_units = 0

        for r_idx, itm in enumerate(self.items):
            line_total = itm["unit_cost"] * itm["quantity"]
            total_amount += line_total
            total_units += itm["quantity"]

            # Name
            c0 = QTableWidgetItem(itm["name"])
            c0.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
            self.table.setItem(r_idx, 0, c0)

            # Model
            self.table.setItem(r_idx, 1, QTableWidgetItem(itm["model"]))

            # Category
            self.table.setItem(r_idx, 2, QTableWidgetItem(itm["category_name"]))

            # Unit Cost Paid
            c3 = QTableWidgetItem(f"${itm['unit_cost']:,.2f}")
            c3.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.table.setItem(r_idx, 3, c3)

            # Qty
            c4 = QTableWidgetItem(f"{itm['quantity']} pcs")
            c4.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(r_idx, 4, c4)

            # Line Subtotal
            c5 = QTableWidgetItem(f"${line_total:,.2f}")
            c5.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            c5.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
            c5.setForeground(QColor("#15803d"))
            self.table.setItem(r_idx, 5, c5)

            self.table.setRowHeight(r_idx, 32)

        self.lbl_total.setText(f"<b>${total_amount:,.2f}</b>")
        self.lbl_items_summary.setText(f"{len(self.items)} line item(s) • {total_units} total units")

    def _on_save_clicked(self) -> None:
        if not check_permission("purchases.manage", parent=self, action_name="record purchases"):
            return

        supplier_id = self.cmb_supplier.currentData()
        if not supplier_id or supplier_id <= 0:
            QMessageBox.warning(self, "Validation Error", "Please select a Supplier.")
            self.cmb_supplier.setFocus()
            return

        invoice_num = self.txt_invoice_num.text().strip()
        if not invoice_num:
            QMessageBox.warning(self, "Validation Error", "Supplier Invoice Number is required.")
            self.txt_invoice_num.setFocus()
            return

        if not self.items:
            QMessageBox.warning(self, "Validation Error", "Please add at least one product line item to this purchase order.")
            return

        purchase_date_str = self.date_purchase.date().toString("yyyy-MM-dd") + " " + datetime.datetime.now().strftime("%H:%M:%S")
        user_id = self.session.current_user.id if self.session.current_user else 1
        payment_method = self.cmb_payment.currentText().lower().replace(" ", "_")

        total_cost = sum(i["unit_cost"] * i["quantity"] for i in self.items)
        total_units = sum(i["quantity"] for i in self.items)

        # Confirmation
        confirm_msg = (
            f"Record Inbound Purchase for <b>{self.cmb_supplier.currentText()}</b>?\n\n"
            f"• <b>Invoice #:</b> {invoice_num}\n"
            f"• <b>Date:</b> {self.date_purchase.date().toString('yyyy-MM-dd')}\n"
            f"• <b>Line Items:</b> {len(self.items)} products\n"
            f"• <b>Total Units to Restock:</b> +{total_units} units\n"
            f"• <b>Total Purchase Cost:</b> ${total_cost:,.2f}\n\n"
            f"This will immediately increase current inventory stock for all {len(self.items)} products."
        )

        reply = QMessageBox.question(
            self,
            "Confirm Inbound Purchase",
            confirm_msg,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        success, po_number, msg = self.partner_service.record_purchase(
            user_id=user_id,
            supplier_id=supplier_id,
            items=self.items,
            invoice_number=invoice_num,
            purchase_date=purchase_date_str,
            payment_method=payment_method,
        )

        if not success:
            QMessageBox.critical(self, "Purchase Error", msg)
            return

        QMessageBox.information(
            self,
            "Purchase Recorded & Stock Updated",
            f"🎉 <b>Purchase Order '{po_number}' Recorded!</b>\n\n"
            f"• Inventory stock for <b>{len(self.items)}</b> product(s) increased by <b>+{total_units}</b> units.\n"
            f"• Actual unit costs recorded in purchase ledger.\n"
            f"• Audit log entry generated.",
        )
        self.accept()

