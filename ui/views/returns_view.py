"""
Returns & RMA Processing View.
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


class ReturnsView(QWidget):
    """
    Returns and RMA Management Screen.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.partner_service = PartnerService()

        self._setup_ui()
        self.load_returns()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        # Header
        top_bar = QHBoxLayout()
        header_layout = QVBoxLayout()
        lbl_title = QLabel("🔄 Customer Returns & RMA")
        lbl_title.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        lbl_title.setStyleSheet("color: #0f172a;")
        lbl_subtitle = QLabel("Process returned items, manage refunds, and track restocked products.")
        lbl_subtitle.setStyleSheet("color: #64748b; font-size: 12px;")
        header_layout.addWidget(lbl_title)
        header_layout.addWidget(lbl_subtitle)
        top_bar.addLayout(header_layout)

        top_bar.addStretch()

        self.btn_new_return = QPushButton("+ Process New Return")
        self.btn_new_return.setStyleSheet("""
            background-color: #2563eb; color: white; padding: 8px 18px; border-radius: 6px; font-weight: bold; font-size: 13px;
        """)
        self.btn_new_return.clicked.connect(self._open_new_return)
        top_bar.addWidget(self.btn_new_return)

        layout.addLayout(top_bar)

        # Search Bar & Filter
        filter_bar = QHBoxLayout()
        self.txt_search = QLineEdit()
        self.txt_search.setPlaceholderText("🔍 Search returns by Return #, Invoice #, Customer...")
        self.txt_search.setFixedHeight(34)
        self.txt_search.textChanged.connect(self._filter_returns)
        filter_bar.addWidget(self.txt_search, stretch=3)

        self.btn_refresh = QPushButton("↻ Refresh")
        self.btn_refresh.setFixedHeight(34)
        self.btn_refresh.clicked.connect(self.load_returns)
        filter_bar.addWidget(self.btn_refresh)

        layout.addLayout(filter_bar)

        # Returns Table
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            "Return #", "Invoice #", "Customer", "Refund Amount", "Refund Method", "Status"
        ])
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self.table)

    def load_returns(self) -> None:
        """Query returns."""
        self.raw_returns = self.partner_service.get_all_returns()
        self._filter_returns()

    def _filter_returns(self) -> None:
        query = self.txt_search.text().strip().lower()
        filtered = []
        for r in getattr(self, "raw_returns", []):
            if query:
                rn_m = query in (r.get("return_number") or "").lower()
                inv_m = query in (r.get("invoice_number") or "").lower()
                cust_m = query in (r.get("customer_name") or "").lower()
                if not (rn_m or inv_m or cust_m):
                    continue
            filtered.append(r)

        self.table.setRowCount(len(filtered))
        for row_idx, r in enumerate(filtered):
            # Return #
            rn_item = QTableWidgetItem(r.get("return_number", ""))
            rn_item.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
            self.table.setItem(row_idx, 0, rn_item)

            # Invoice #
            self.table.setItem(row_idx, 1, QTableWidgetItem(r.get("invoice_number") or "—"))

            # Customer
            self.table.setItem(row_idx, 2, QTableWidgetItem(r.get("customer_name") or "—"))

            # Refund Amount
            ref_item = QTableWidgetItem(f"${float(r.get('total_refund_amount', 0.0)):.2f}")
            ref_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.table.setItem(row_idx, 3, ref_item)

            # Refund Method
            self.table.setItem(row_idx, 4, QTableWidgetItem(str(r.get("refund_method", "cash")).replace("_", " ").title()))

            # Status
            stat_item = QTableWidgetItem(str(r.get("status", "completed")).upper())
            stat_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            stat_item.setForeground(QColor("#16a34a"))
            self.table.setItem(row_idx, 5, stat_item)
            self.table.setRowHeight(row_idx, 38)

    def _open_new_return(self) -> None:
        if not check_permission("returns.manage", parent=self, action_name="process returns"):
            return
        QMessageBox.information(
            self,
            "Returns & RMA",
            "Returns & RMA processing dialog is ready to initiate. Select a completed invoice to process returned items."
        )
