"""
Sales and POS View.
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
    QFrame,
    QMessageBox,
    QDialog,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QColor

from data.db import DatabaseManager, get_db
from business.product_service import ProductService
from business.partner_service import PartnerService
from business.permissions import check_permission, can_manage
from ui.dialogs.quick_sale_dialog import QuickSaleDialog


class SalesView(QWidget):
    """
    Sales and Invoicing Management Screen.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.db = get_db()
        self.product_service = ProductService()
        self.partner_service = PartnerService()

        self._setup_ui()
        self.load_sales()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        # Header
        top_bar = QHBoxLayout()
        header_layout = QVBoxLayout()
        lbl_title = QLabel("🛒 Sales & Point of Sale")
        lbl_title.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        lbl_title.setStyleSheet("color: #0f172a;")
        lbl_subtitle = QLabel("View transaction history, customer invoices, and initiate POS sales.")
        lbl_subtitle.setStyleSheet("color: #64748b; font-size: 12px;")
        header_layout.addWidget(lbl_title)
        header_layout.addWidget(lbl_subtitle)
        top_bar.addLayout(header_layout)

        top_bar.addStretch()

        self.btn_new_sale = QPushButton("+ New POS Sale")
        self.btn_new_sale.setStyleSheet("""
            background-color: #16a34a; color: white; padding: 8px 18px; border-radius: 6px; font-weight: bold; font-size: 13px;
        """)
        self.btn_new_sale.clicked.connect(self._open_new_sale)
        top_bar.addWidget(self.btn_new_sale)

        layout.addLayout(top_bar)

        # Search Bar & Filter
        filter_bar = QHBoxLayout()
        self.txt_search = QLineEdit()
        self.txt_search.setPlaceholderText("🔍 Search sales by Invoice Number, Customer Name...")
        self.txt_search.setFixedHeight(34)
        self.txt_search.textChanged.connect(self._filter_sales)
        filter_bar.addWidget(self.txt_search, stretch=3)

        self.btn_refresh = QPushButton("↻ Refresh")
        self.btn_refresh.setFixedHeight(34)
        self.btn_refresh.clicked.connect(self.load_sales)
        filter_bar.addWidget(self.btn_refresh)

        layout.addLayout(filter_bar)

        # Sales Table
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "Invoice #", "Customer", "Date & Time", "Subtotal", "Tax", "Total Amount", "Payment Status"
        ])
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self.table)

    def load_sales(self) -> None:
        """Query sales history from database."""
        sql = """
            SELECT 
                s.id,
                s.invoice_number,
                COALESCE(c.name, s.guest_name, 'Guest Customer') AS customer_name,
                s.sale_date,
                s.subtotal,
                s.tax_amount,
                s.total_amount,
                s.payment_status,
                s.status
            FROM sales s
            LEFT JOIN customers c ON s.customer_id = c.id
            ORDER BY s.sale_date DESC, s.id DESC LIMIT 300;
        """
        try:
            self.raw_sales = [dict(r) for r in self.db.execute_query(sql)]
        except Exception as e:
            self.raw_sales = []
        self._filter_sales()

    def _filter_sales(self) -> None:
        query = self.txt_search.text().strip().lower()
        filtered = []
        for s in getattr(self, "raw_sales", []):
            if query:
                if query not in s["invoice_number"].lower() and query not in s["customer_name"].lower():
                    continue
            filtered.append(s)

        self.table.setRowCount(len(filtered))
        for row_idx, s in enumerate(filtered):
            # Invoice #
            inv_item = QTableWidgetItem(s["invoice_number"])
            inv_item.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
            self.table.setItem(row_idx, 0, inv_item)

            # Customer
            self.table.setItem(row_idx, 1, QTableWidgetItem(s["customer_name"]))

            # Date
            self.table.setItem(row_idx, 2, QTableWidgetItem(str(s["sale_date"])))

            # Subtotal
            sub_item = QTableWidgetItem(f"${s['subtotal']:.2f}")
            sub_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.table.setItem(row_idx, 3, sub_item)

            # Tax
            tax_item = QTableWidgetItem(f"${s['tax_amount']:.2f}")
            tax_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.table.setItem(row_idx, 4, tax_item)

            # Total
            tot_item = QTableWidgetItem(f"${s['total_amount']:.2f}")
            tot_item.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
            tot_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.table.setItem(row_idx, 5, tot_item)

            # Payment Status
            stat_item = QTableWidgetItem(s["payment_status"].upper())
            stat_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            stat_item.setForeground(QColor("#16a34a" if s["payment_status"] == "paid" else "#d97706"))
            self.table.setItem(row_idx, 6, stat_item)
            self.table.setRowHeight(row_idx, 38)

    def _open_new_sale(self) -> None:
        if not check_permission("sales.manage", parent=self, action_name="create sales"):
            return
        dlg = QuickSaleDialog(self.product_service, self.partner_service, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.load_sales()
