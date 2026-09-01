"""
Warranty Claims & Technical Support View.
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
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QColor

from business.partner_service import PartnerService
from business.permissions import check_permission, can_manage


class WarrantyView(QWidget):
    """
    Warranty Claims & Repair Tracking Screen.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.partner_service = PartnerService()

        self._setup_ui()
        self.load_claims()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        # Header
        top_bar = QHBoxLayout()
        header_layout = QVBoxLayout()
        lbl_title = QLabel("🛡️ Warranty Claims & Service")
        lbl_title.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        lbl_title.setStyleSheet("color: #0f172a;")
        lbl_subtitle = QLabel("Track RMA claims, hardware repairs, technician inspection, and manufacturer warranties.")
        lbl_subtitle.setStyleSheet("color: #64748b; font-size: 12px;")
        header_layout.addWidget(lbl_title)
        header_layout.addWidget(lbl_subtitle)
        top_bar.addLayout(header_layout)

        top_bar.addStretch()

        self.btn_new_claim = QPushButton("+ File Warranty Claim")
        self.btn_new_claim.setStyleSheet("""
            background-color: #2563eb; color: white; padding: 8px 18px; border-radius: 6px; font-weight: bold; font-size: 13px;
        """)
        self.btn_new_claim.clicked.connect(self._open_new_claim)
        top_bar.addWidget(self.btn_new_claim)

        layout.addLayout(top_bar)

        # Search Bar & Filter
        filter_bar = QHBoxLayout()
        self.txt_search = QLineEdit()
        self.txt_search.setPlaceholderText("🔍 Search warranty claims by Claim #, Product, Customer...")
        self.txt_search.setFixedHeight(34)
        self.txt_search.textChanged.connect(self._filter_claims)
        filter_bar.addWidget(self.txt_search, stretch=3)

        self.btn_refresh = QPushButton("↻ Refresh")
        self.btn_refresh.setFixedHeight(34)
        self.btn_refresh.clicked.connect(self.load_claims)
        filter_bar.addWidget(self.btn_refresh)

        layout.addLayout(filter_bar)

        # Claims Table
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            "Claim #", "Product", "Customer", "Serial #", "Issue / Symptoms", "Status"
        ])
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self.table)

    def load_claims(self) -> None:
        """Query warranty claims."""
        self.raw_claims = self.partner_service.get_all_warranty_claims()
        self._filter_claims()

    def _filter_claims(self) -> None:
        query = self.txt_search.text().strip().lower()
        filtered = []
        for c in getattr(self, "raw_claims", []):
            if query:
                cn_m = query in (c.get("claim_number") or "").lower()
                prod_m = query in (c.get("product_name") or "").lower()
                cust_m = query in (c.get("customer_name") or "").lower()
                if not (cn_m or prod_m or cust_m):
                    continue
            filtered.append(c)

        self.table.setRowCount(len(filtered))
        for row_idx, c in enumerate(filtered):
            # Claim #
            cn_item = QTableWidgetItem(c.get("claim_number", ""))
            cn_item.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
            self.table.setItem(row_idx, 0, cn_item)

            # Product
            self.table.setItem(row_idx, 1, QTableWidgetItem(c.get("product_name") or "—"))

            # Customer
            self.table.setItem(row_idx, 2, QTableWidgetItem(c.get("customer_name") or "—"))

            # Serial #
            self.table.setItem(row_idx, 3, QTableWidgetItem(c.get("serial_number") or "—"))

            # Issue
            self.table.setItem(row_idx, 4, QTableWidgetItem(c.get("issue_description") or "—"))

            # Status
            stat_item = QTableWidgetItem(str(c.get("status", "pending")).upper())
            stat_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            stat_item.setForeground(QColor("#d97706" if c.get("status") == "pending" else "#16a34a"))
            self.table.setItem(row_idx, 5, stat_item)
            self.table.setRowHeight(row_idx, 38)

    def _open_new_claim(self) -> None:
        if not check_permission("warranty.manage", parent=self, action_name="manage warranty claims"):
            return
        QMessageBox.information(
            self,
            "Warranty Claims",
            "Warranty Claim Intake Dialog is ready to accept hardware RMA requests."
        )
