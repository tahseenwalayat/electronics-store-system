"""
Supplier Detail Dialog.
Displays supplier profile information and complete historical purchase orders list.
Explicitly excludes supplier payment/payable/refund tracking.
"""

from typing import Optional, Dict, Any, List
from PySide6.QtWidgets import (
    QDialog,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QFrame,
    QMessageBox,
    QScrollArea,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QColor

from business.partner_service import PartnerService
from business.permissions import check_permission, can_manage
from ui.dialogs.supplier_dialog import SupplierDialog


class SupplierDetailDialog(QDialog):
    """
    Detailed inspection dialog for a supplier showing contact profile and full purchase order history.
    """

    supplier_updated = Signal()

    def __init__(self, supplier_id: int, partner_service: Optional[PartnerService] = None, parent=None):
        super().__init__(parent)
        self.supplier_id = supplier_id
        self.partner_service = partner_service or PartnerService()
        self.supplier: Optional[Dict[str, Any]] = None
        self.purchases: List[Dict[str, Any]] = []

        self.setWindowTitle("🏢 Supplier Profile & Purchase History — Electronics Store System")
        self.resize(920, 640)
        self.setMinimumSize(800, 520)

        self._setup_ui()
        self.load_data()

    def _setup_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(22, 20, 22, 20)
        main_layout.setSpacing(14)

        # ---------------------------------------------------------------------
        # 1. TOP SUPPLIER PROFILE HEADER CARD
        # ---------------------------------------------------------------------
        profile_card = QFrame()
        profile_card.setStyleSheet("""
            QFrame {
                background-color: #ffffff;
                border: 1px solid #e2e8f0;
                border-radius: 10px;
                padding: 14px;
            }
        """)
        profile_layout = QVBoxLayout(profile_card)
        profile_layout.setContentsMargins(12, 10, 12, 10)
        profile_layout.setSpacing(10)

        # Top row: Name, Badge, and Edit button
        hdr_row = QHBoxLayout()
        self.lbl_company_name = QLabel("Loading Company...")
        self.lbl_company_name.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        self.lbl_company_name.setStyleSheet("color: #0f172a;")
        hdr_row.addWidget(self.lbl_company_name)

        hdr_row.addStretch()

        self.btn_edit = QPushButton("✏️ Edit Supplier")
        self.btn_edit.setStyleSheet("""
            QPushButton {
                background-color: #eff6ff;
                color: #1d4ed8;
                border: 1px solid #bfdbfe;
                padding: 6px 14px;
                border-radius: 6px;
                font-weight: 600;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #dbeafe;
            }
        """)
        self.btn_edit.clicked.connect(self._on_edit_clicked)
        hdr_row.addWidget(self.btn_edit)

        profile_layout.addLayout(hdr_row)

        # Profile fields grid
        grid = QGridLayout()
        grid.setContentsMargins(0, 4, 0, 0)
        grid.setHorizontalSpacing(24)
        grid.setVerticalSpacing(6)

        # Supplier Name (Representative)
        self.lbl_rep_val = QLabel("—")
        self.lbl_rep_val.setStyleSheet("color: #1e293b; font-weight: 500;")
        grid.addWidget(self._create_field_label("Supplier Name:"), 0, 0)
        grid.addWidget(self.lbl_rep_val, 0, 1)

        # Phone Number
        self.lbl_phone_val = QLabel("—")
        self.lbl_phone_val.setStyleSheet("color: #1e293b; font-weight: 500;")
        grid.addWidget(self._create_field_label("Phone Number:"), 0, 2)
        grid.addWidget(self.lbl_phone_val, 0, 3)

        # Email
        self.lbl_email_val = QLabel("—")
        self.lbl_email_val.setStyleSheet("color: #1e293b; font-weight: 500;")
        grid.addWidget(self._create_field_label("Email:"), 1, 0)
        grid.addWidget(self.lbl_email_val, 1, 1)

        # Address
        self.lbl_address_val = QLabel("—")
        self.lbl_address_val.setStyleSheet("color: #1e293b; font-weight: 500;")
        grid.addWidget(self._create_field_label("Address:"), 1, 2)
        grid.addWidget(self.lbl_address_val, 1, 3)

        # Notes (if any)
        self.lbl_notes_val = QLabel("—")
        self.lbl_notes_val.setStyleSheet("color: #64748b; font-style: italic;")
        grid.addWidget(self._create_field_label("Notes:"), 2, 0)
        grid.addWidget(self.lbl_notes_val, 2, 1, 1, 3)

        profile_layout.addLayout(grid)
        main_layout.addWidget(profile_card)

        # ---------------------------------------------------------------------
        # 2. KPI SUMMARY METRIC CHIPS
        # ---------------------------------------------------------------------
        kpi_bar = QHBoxLayout()
        kpi_bar.setSpacing(12)

        self.card_orders = self._create_kpi_card("📦 Total Purchase Orders", "0 orders", "#0284c7")
        kpi_bar.addWidget(self.card_orders)

        self.card_units = self._create_kpi_card("📊 Total Units Received", "0 units", "#4338ca")
        kpi_bar.addWidget(self.card_units)

        self.card_spend = self._create_kpi_card("💰 Total Purchase Spend", "$0.00", "#15803d")
        kpi_bar.addWidget(self.card_spend)

        main_layout.addLayout(kpi_bar)

        # ---------------------------------------------------------------------
        # 3. PURCHASE HISTORY SECTION
        # ---------------------------------------------------------------------
        history_header = QHBoxLayout()
        lbl_hist_title = QLabel("📜 Purchase Order History")
        lbl_hist_title.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        lbl_hist_title.setStyleSheet("color: #0f172a;")
        history_header.addWidget(lbl_hist_title)

        history_header.addStretch()

        self.lbl_order_count = QLabel("0 purchases recorded")
        self.lbl_order_count.setStyleSheet("color: #64748b; font-size: 12px;")
        history_header.addWidget(self.lbl_order_count)

        main_layout.addLayout(history_header)

        # Purchases Table
        self.table_purchases = QTableWidget()
        self.table_purchases.setColumnCount(6)
        self.table_purchases.setHorizontalHeaderLabels([
            "Purchase Date", "Invoice / PO #", "Items Received", "Units", "Total Amount", "Details"
        ])
        self.table_purchases.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table_purchases.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table_purchases.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table_purchases.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table_purchases.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.table_purchases.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)
        self.table_purchases.setColumnWidth(5, 110)

        self.table_purchases.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table_purchases.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table_purchases.verticalHeader().setVisible(False)
        self.table_purchases.setStyleSheet("""
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
        self.table_purchases.cellDoubleClicked.connect(self._on_table_double_clicked)
        main_layout.addWidget(self.table_purchases, stretch=1)

        # ---------------------------------------------------------------------
        # 4. BOTTOM ACTION BAR
        # ---------------------------------------------------------------------
        bottom_bar = QHBoxLayout()
        bottom_bar.addStretch()

        btn_close = QPushButton("Close")
        btn_close.setStyleSheet("""
            background-color: #f1f5f9; color: #334155; border: 1px solid #cbd5e1; padding: 7px 22px; border-radius: 5px; font-weight: 600;
        """)
        btn_close.clicked.connect(self.accept)
        bottom_bar.addWidget(btn_close)

        main_layout.addLayout(bottom_bar)

    def _create_field_label(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setStyleSheet("color: #64748b; font-size: 11px; font-weight: 600;")
        return lbl

    def _create_kpi_card(self, title: str, initial_val: str, color_hex: str) -> QFrame:
        card = QFrame()
        card.setStyleSheet("""
            QFrame {
                background-color: #ffffff;
                border: 1px solid #e2e8f0;
                border-radius: 8px;
                padding: 6px 12px;
            }
        """)
        lay = QVBoxLayout(card)
        lay.setContentsMargins(6, 4, 6, 4)
        lay.setSpacing(2)

        lbl_t = QLabel(title)
        lbl_t.setStyleSheet("color: #64748b; font-size: 11px; font-weight: 500;")
        lay.addWidget(lbl_t)

        lbl_v = QLabel(initial_val)
        lbl_v.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        lbl_v.setStyleSheet(f"color: {color_hex};")
        lay.addWidget(lbl_v)

        card.lbl_val = lbl_v
        return card

    # -------------------------------------------------------------------------
    # DATA LOADING & POPULATION
    # -------------------------------------------------------------------------

    def load_data(self) -> None:
        """Fetch supplier profile and complete purchase order history."""
        self.supplier = self.partner_service.get_supplier_by_id(self.supplier_id)
        if not self.supplier:
            QMessageBox.warning(self, "Supplier Not Found", f"Supplier #{self.supplier_id} could not be loaded.")
            self.reject()
            return

        # Update profile header
        company = self.supplier.get("name", "Unknown Company")
        contact = self.supplier.get("contact_person") or "—"
        phone = self.supplier.get("phone") or "—"
        email = self.supplier.get("email") or "—"
        address = self.supplier.get("address") or "—"
        notes = self.supplier.get("notes") or "None"

        self.lbl_company_name.setText(company)
        self.lbl_rep_val.setText(contact)
        self.lbl_phone_val.setText(phone)
        self.lbl_email_val.setText(email)
        self.lbl_address_val.setText(address)
        self.lbl_notes_val.setText(notes)

        # Fetch purchase history
        self.purchases = self.partner_service.get_supplier_purchase_history(self.supplier_id)

        # Update KPI Cards
        total_orders = len(self.purchases)
        total_units = sum(p.get("total_units_received", 0) for p in self.purchases)
        total_spend = sum(p.get("total_amount", 0.0) for p in self.purchases)

        self.card_orders.lbl_val.setText(f"{total_orders} orders")
        self.card_units.lbl_val.setText(f"{total_units} units")
        self.card_spend.lbl_val.setText(f"${total_spend:,.2f}")
        self.lbl_order_count.setText(f"{total_orders} purchase order(s) found")

        # Populate Purchases Table
        self._populate_purchases_table()

    def _populate_purchases_table(self) -> None:
        """Render purchase order records."""
        self.table_purchases.setRowCount(len(self.purchases))

        for row_idx, p in enumerate(self.purchases):
            # 0. Date
            raw_date = p.get("purchase_date", "")
            date_str = str(raw_date)[:16].replace("T", " ") if raw_date else "—"
            c_date = QTableWidgetItem(date_str)
            c_date.setForeground(QColor("#475569"))
            self.table_purchases.setItem(row_idx, 0, c_date)

            # 1. Invoice / PO #
            po_num = p.get("purchase_number", "—")
            c_po = QTableWidgetItem(po_num)
            c_po.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
            c_po.setForeground(QColor("#1e40af"))
            self.table_purchases.setItem(row_idx, 1, c_po)

            # 2. Items Summary
            summary_txt = p.get("items_summary") or "No items listed"
            c_summary = QTableWidgetItem(summary_txt)
            c_summary.setToolTip(summary_txt)
            self.table_purchases.setItem(row_idx, 2, c_summary)

            # 3. Units
            units_val = p.get("total_units_received", 0)
            c_units = QTableWidgetItem(f"{units_val} pcs")
            c_units.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.table_purchases.setItem(row_idx, 3, c_units)

            # 4. Total Amount
            total_val = p.get("total_amount", 0.0)
            c_total = QTableWidgetItem(f"${total_val:,.2f}")
            c_total.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
            c_total.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            c_total.setForeground(QColor("#15803d"))
            self.table_purchases.setItem(row_idx, 4, c_total)

            # 5. Details Action
            btn_details = QPushButton("🔍 View Items")
            btn_details.setStyleSheet("""
                background-color: #f8fafc;
                color: #2563eb;
                border: 1px solid #cbd5e1;
                border-radius: 4px;
                padding: 3px 8px;
                font-size: 11px;
                font-weight: 600;
            """)
            btn_details.clicked.connect(lambda _, p_id=p["id"]: self._view_purchase_breakdown(p_id))
            self.table_purchases.setCellWidget(row_idx, 5, btn_details)

            self.table_purchases.setRowHeight(row_idx, 34)

    def _on_table_double_clicked(self, row: int, col: int) -> None:
        """Handle double-clicking a purchase order row to view item breakdown."""
        if 0 <= row < len(self.purchases):
            p = self.purchases[row]
            self._view_purchase_breakdown(p["id"])

    def _view_purchase_breakdown(self, purchase_id: int) -> None:
        """Display dialog showing itemized breakdown of products in the purchase order."""
        details = self.partner_service.get_purchase_details(purchase_id)
        if not details:
            QMessageBox.warning(self, "Details Unavailable", f"Could not load items for Purchase #{purchase_id}.")
            return

        dlg = QDialog(self)
        dlg.setWindowTitle(f"Purchase Order Items — {details.get('purchase_number', '')}")
        dlg.resize(680, 420)
        d_lay = QVBoxLayout(dlg)
        d_lay.setContentsMargins(18, 16, 18, 16)
        d_lay.setSpacing(12)

        # Header
        top_h = QHBoxLayout()
        lbl_po = QLabel(f"📦 <b>Invoice / PO:</b> {details.get('purchase_number', '')}")
        lbl_po.setFont(QFont("Segoe UI", 12))
        top_h.addWidget(lbl_po)
        top_h.addStretch()

        lbl_tot = QLabel(f"<b>Total:</b> <span style='color: #15803d;'>${details.get('total_amount', 0.0):,.2f}</span>")
        lbl_tot.setFont(QFont("Segoe UI", 12))
        top_h.addWidget(lbl_tot)
        d_lay.addLayout(top_h)

        # Items table
        tbl = QTableWidget()
        tbl.setColumnCount(5)
        tbl.setHorizontalHeaderLabels(["Product Name", "Model", "Unit Cost", "Quantity", "Subtotal"])
        tbl.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        tbl.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        tbl.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        tbl.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        tbl.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        tbl.verticalHeader().setVisible(False)
        tbl.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

        items = details.get("items", [])
        tbl.setRowCount(len(items))
        for r_idx, itm in enumerate(items):
            c_name = QTableWidgetItem(itm.get("product_name", ""))
            c_name.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
            tbl.setItem(r_idx, 0, c_name)

            tbl.setItem(r_idx, 1, QTableWidgetItem(itm.get("product_model") or "—"))

            c_cost = QTableWidgetItem(f"${itm.get('unit_cost', 0.0):,.2f}")
            c_cost.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            tbl.setItem(r_idx, 2, c_cost)

            c_qty = QTableWidgetItem(f"{itm.get('quantity', 0)} pcs")
            c_qty.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            tbl.setItem(r_idx, 3, c_qty)

            c_sub = QTableWidgetItem(f"${itm.get('subtotal', 0.0):,.2f}")
            c_sub.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            c_sub.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
            c_sub.setForeground(QColor("#15803d"))
            tbl.setItem(r_idx, 4, c_sub)

            tbl.setRowHeight(r_idx, 32)

        d_lay.addWidget(tbl, stretch=1)

        btn_close_sub = QPushButton("Close")
        btn_close_sub.setStyleSheet("background-color: #f1f5f9; padding: 6px 16px; border-radius: 4px;")
        btn_close_sub.clicked.connect(dlg.accept)
        d_lay.addWidget(btn_close_sub, alignment=Qt.AlignmentFlag.AlignRight)

        dlg.exec()

    def _on_edit_clicked(self) -> None:
        """Open supplier editor modal."""
        if not check_permission("suppliers.manage", parent=self, action_name="edit supplier"):
            return

        dlg = SupplierDialog(self.partner_service, supplier_data=self.supplier, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.load_data()
            self.supplier_updated.emit()
