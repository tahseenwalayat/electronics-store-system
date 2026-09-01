"""
Purchases and Inbound Inventory View.
"""

from typing import Optional, Dict, Any, List
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QMessageBox,
    QDialog,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QColor

from business.product_service import ProductService
from business.partner_service import PartnerService
from business.permissions import check_permission, can_manage
from ui.dialogs.add_purchase_dialog import AddPurchaseDialog


class PurchasesView(QWidget):
    """
    Purchases & Inbound Inventory Management Screen.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.product_service = ProductService()
        self.partner_service = PartnerService()

        self._setup_ui()
        self.load_purchases()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        # Header
        top_bar = QHBoxLayout()
        header_layout = QVBoxLayout()
        lbl_title = QLabel("🚚 Purchases & Inbound Inventory")
        lbl_title.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        lbl_title.setStyleSheet("color: #0f172a;")
        lbl_subtitle = QLabel("Track supplier purchase orders, restock inventory levels, and manage vendor billing.")
        lbl_subtitle.setStyleSheet("color: #64748b; font-size: 12px;")
        header_layout.addWidget(lbl_title)
        header_layout.addWidget(lbl_subtitle)
        top_bar.addLayout(header_layout)

        top_bar.addStretch()

        self.btn_new_purchase = QPushButton("+ Add Purchase Order")
        self.btn_new_purchase.setStyleSheet("""
            background-color: #2563eb; color: white; padding: 8px 18px; border-radius: 6px; font-weight: bold; font-size: 13px;
        """)
        self.btn_new_purchase.clicked.connect(self._open_new_purchase)
        top_bar.addWidget(self.btn_new_purchase)

        layout.addLayout(top_bar)

        # Search Bar & Filter
        filter_bar = QHBoxLayout()
        self.txt_search = QLineEdit()
        self.txt_search.setPlaceholderText("🔍 Search purchases by PO Number, Supplier Name...")
        self.txt_search.setFixedHeight(34)
        self.txt_search.textChanged.connect(self._filter_purchases)
        filter_bar.addWidget(self.txt_search, stretch=3)

        self.btn_refresh = QPushButton("↻ Refresh")
        self.btn_refresh.setFixedHeight(34)
        self.btn_refresh.clicked.connect(self.load_purchases)
        filter_bar.addWidget(self.btn_refresh)

        layout.addLayout(filter_bar)

        # Purchases Table
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            "PO Number", "Supplier", "Date & Time", "Total Cost", "Payment Method", "Status"
        ])
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self.table)

    def load_purchases(self) -> None:
        """Query purchases history."""
        self.raw_purchases = self.partner_service.get_all_purchases()
        self._filter_purchases()

    def _filter_purchases(self) -> None:
        query = self.txt_search.text().strip().lower()
        filtered = []
        for p in getattr(self, "raw_purchases", []):
            if query:
                if query not in p["purchase_number"].lower() and query not in p["supplier_name"].lower():
                    continue
            filtered.append(p)

        self.table.setRowCount(len(filtered))
        for row_idx, p in enumerate(filtered):
            # PO Number
            po_item = QTableWidgetItem(p["purchase_number"])
            po_item.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
            self.table.setItem(row_idx, 0, po_item)

            # Supplier
            self.table.setItem(row_idx, 1, QTableWidgetItem(p["supplier_name"]))

            # Date
            self.table.setItem(row_idx, 2, QTableWidgetItem(str(p["purchase_date"])))

            # Total
            tot_item = QTableWidgetItem(f"${p['total_amount']:.2f}")
            tot_item.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
            tot_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.table.setItem(row_idx, 3, tot_item)

            # Payment Method
            self.table.setItem(row_idx, 4, QTableWidgetItem(p.get("payment_method", "bank_transfer").replace("_", " ").title()))

            # Status
            stat_item = QTableWidgetItem(p["status"].upper())
            stat_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            stat_item.setForeground(QColor("#16a34a" if p["status"] == "received" else "#d97706"))
            self.table.setItem(row_idx, 5, stat_item)
            self.table.setRowHeight(row_idx, 38)

    def _open_new_purchase(self) -> None:
        if not check_permission("purchases.manage", parent=self, action_name="record purchases"):
            return
        dlg = AddPurchaseDialog(self.product_service, self.partner_service, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.load_purchases()
