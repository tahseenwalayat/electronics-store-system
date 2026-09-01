"""
Suppliers Directory and Profiles View.
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

from business.partner_service import PartnerService
from business.permissions import check_permission, can_manage
from ui.dialogs.supplier_dialog import SupplierDialog


class SuppliersView(QWidget):
    """
    Suppliers and Vendors Directory Screen.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.partner_service = PartnerService()

        self._setup_ui()
        self.load_suppliers()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        # Header
        top_bar = QHBoxLayout()
        header_layout = QVBoxLayout()
        lbl_title = QLabel("🏭 Supplier & Vendor Profiles")
        lbl_title.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        lbl_title.setStyleSheet("color: #0f172a;")
        lbl_subtitle = QLabel("Manage wholesale vendor accounts, distributor contacts, and tax IDs.")
        lbl_subtitle.setStyleSheet("color: #64748b; font-size: 12px;")
        header_layout.addWidget(lbl_title)
        header_layout.addWidget(lbl_subtitle)
        top_bar.addLayout(header_layout)

        top_bar.addStretch()

        self.btn_new_supplier = QPushButton("+ Add New Supplier")
        self.btn_new_supplier.setStyleSheet("""
            background-color: #2563eb; color: white; padding: 8px 18px; border-radius: 6px; font-weight: bold; font-size: 13px;
        """)
        self.btn_new_supplier.clicked.connect(self._open_new_supplier)
        top_bar.addWidget(self.btn_new_supplier)

        layout.addLayout(top_bar)

        # Search Bar & Filter
        filter_bar = QHBoxLayout()
        self.txt_search = QLineEdit()
        self.txt_search.setPlaceholderText("🔍 Search suppliers by Company Name, Contact Person...")
        self.txt_search.setFixedHeight(34)
        self.txt_search.textChanged.connect(self._filter_suppliers)
        filter_bar.addWidget(self.txt_search, stretch=3)

        self.btn_refresh = QPushButton("↻ Refresh")
        self.btn_refresh.setFixedHeight(34)
        self.btn_refresh.clicked.connect(self.load_suppliers)
        filter_bar.addWidget(self.btn_refresh)

        layout.addLayout(filter_bar)

        # Suppliers Table
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            "Company / Vendor", "Contact Person", "Phone", "Email", "Tax / VAT #", "Address"
        ])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self.table)

    def load_suppliers(self) -> None:
        """Query suppliers directory."""
        self.raw_suppliers = self.partner_service.get_all_suppliers()
        self._filter_suppliers()

    def _filter_suppliers(self) -> None:
        query = self.txt_search.text().strip().lower()
        filtered = []
        for s in getattr(self, "raw_suppliers", []):
            if query:
                name_m = query in (s.get("name") or "").lower()
                cp_m = query in (s.get("contact_person") or "").lower()
                phone_m = query in (s.get("phone") or "").lower()
                if not (name_m or cp_m or phone_m):
                    continue
            filtered.append(s)

        self.table.setRowCount(len(filtered))
        for row_idx, s in enumerate(filtered):
            # Company
            name_item = QTableWidgetItem(s.get("name", ""))
            name_item.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
            self.table.setItem(row_idx, 0, name_item)

            # Contact
            self.table.setItem(row_idx, 1, QTableWidgetItem(s.get("contact_person") or "—"))

            # Phone
            self.table.setItem(row_idx, 2, QTableWidgetItem(s.get("phone") or "—"))

            # Email
            self.table.setItem(row_idx, 3, QTableWidgetItem(s.get("email") or "—"))

            # Tax #
            self.table.setItem(row_idx, 4, QTableWidgetItem(s.get("tax_number") or "—"))

            # Address
            self.table.setItem(row_idx, 5, QTableWidgetItem(s.get("address") or "—"))
            self.table.setRowHeight(row_idx, 38)

    def _open_new_supplier(self) -> None:
        if not check_permission("suppliers.manage", parent=self, action_name="manage suppliers"):
            return
        dlg = SupplierDialog(self.partner_service, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.load_suppliers()
