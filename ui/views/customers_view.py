"""
Customers Directory and Profile View.
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
from ui.dialogs.customer_dialog import CustomerDialog


class CustomersView(QWidget):
    """
    Customer Directory & Credit Management Screen.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.partner_service = PartnerService()

        self._setup_ui()
        self.load_customers()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        # Header
        top_bar = QHBoxLayout()
        header_layout = QVBoxLayout()
        lbl_title = QLabel("👤 Customer Directory & Credit")
        lbl_title.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        lbl_title.setStyleSheet("color: #0f172a;")
        lbl_subtitle = QLabel("Manage customer profiles, contact info, loyalty points, and credit limits.")
        lbl_subtitle.setStyleSheet("color: #64748b; font-size: 12px;")
        header_layout.addWidget(lbl_title)
        header_layout.addWidget(lbl_subtitle)
        top_bar.addLayout(header_layout)

        top_bar.addStretch()

        self.btn_new_customer = QPushButton("+ Add New Customer")
        self.btn_new_customer.setStyleSheet("""
            background-color: #2563eb; color: white; padding: 8px 18px; border-radius: 6px; font-weight: bold; font-size: 13px;
        """)
        self.btn_new_customer.clicked.connect(self._open_new_customer)
        top_bar.addWidget(self.btn_new_customer)

        layout.addLayout(top_bar)

        # Search Bar & Filter
        filter_bar = QHBoxLayout()
        self.txt_search = QLineEdit()
        self.txt_search.setPlaceholderText("🔍 Search customers by Name, Phone, Email...")
        self.txt_search.setFixedHeight(34)
        self.txt_search.textChanged.connect(self._filter_customers)
        filter_bar.addWidget(self.txt_search, stretch=3)

        self.btn_refresh = QPushButton("↻ Refresh")
        self.btn_refresh.setFixedHeight(34)
        self.btn_refresh.clicked.connect(self.load_customers)
        filter_bar.addWidget(self.btn_refresh)

        layout.addLayout(filter_bar)

        # Customers Table
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            "Name", "Phone", "Email", "Address", "Loyalty Points", "Credit Limit"
        ])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self.table)

    def load_customers(self) -> None:
        """Query customers directory."""
        self.raw_customers = self.partner_service.get_all_customers()
        self._filter_customers()

    def _filter_customers(self) -> None:
        query = self.txt_search.text().strip().lower()
        filtered = []
        for c in getattr(self, "raw_customers", []):
            if query:
                name_m = query in (c.get("name") or "").lower()
                phone_m = query in (c.get("phone") or "").lower()
                email_m = query in (c.get("email") or "").lower()
                if not (name_m or phone_m or email_m):
                    continue
            filtered.append(c)

        self.table.setRowCount(len(filtered))
        for row_idx, c in enumerate(filtered):
            # Name
            name_item = QTableWidgetItem(c.get("name", ""))
            name_item.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
            self.table.setItem(row_idx, 0, name_item)

            # Phone
            self.table.setItem(row_idx, 1, QTableWidgetItem(c.get("phone") or "—"))

            # Email
            self.table.setItem(row_idx, 2, QTableWidgetItem(c.get("email") or "—"))

            # Address
            self.table.setItem(row_idx, 3, QTableWidgetItem(c.get("address") or "—"))

            # Loyalty Points
            pts_item = QTableWidgetItem(f"⭐ {c.get('loyalty_points', 0)} pts")
            pts_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row_idx, 4, pts_item)

            # Credit Limit
            cred_item = QTableWidgetItem(f"${float(c.get('credit_limit', 0.0)):.2f}")
            cred_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.table.setItem(row_idx, 5, cred_item)
            self.table.setRowHeight(row_idx, 38)

    def _open_new_customer(self) -> None:
        if not check_permission("customers.manage", parent=self, action_name="manage customers"):
            return
        dlg = CustomerDialog(self.partner_service, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.load_customers()
