"""
Purchase Return Detail Dialog.
Displays full inspection view of a recorded purchase return transaction.
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
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QColor

from business.partner_service import PartnerService


class PurchaseReturnDetailDialog(QDialog):
    """
    Detailed inspection dialog for a purchase return transaction.
    """

    def __init__(self, return_id: int, partner_service: Optional[PartnerService] = None, parent=None):
        super().__init__(parent)
        self.return_id = return_id
        self.partner_service = partner_service or PartnerService()
        self.details: Optional[Dict[str, Any]] = None

        self.setWindowTitle("↩️ Purchase Return Record — Electronics Store System")
        self.resize(760, 520)
        self.setMinimumSize(660, 440)

        self._setup_ui()
        self._load_data()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(14)

        # ---------------------------------------------------------------------
        # 1. TOP RETURN METADATA CARD
        # ---------------------------------------------------------------------
        card = QFrame()
        card.setStyleSheet("""
            QFrame {
                background-color: #ffffff;
                border: 1px solid #e2e8f0;
                border-radius: 8px;
                padding: 12px;
            }
        """)
        c_lay = QVBoxLayout(card)
        c_lay.setContentsMargins(10, 8, 10, 8)
        c_lay.setSpacing(8)

        # Title row
        t_row = QHBoxLayout()
        self.lbl_ret_num = QLabel("Return #: Loading...")
        self.lbl_ret_num.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        self.lbl_ret_num.setStyleSheet("color: #991b1b;")
        t_row.addWidget(self.lbl_ret_num)

        t_row.addStretch()

        self.lbl_status_badge = QLabel("COMPLETED / RETURNED")
        self.lbl_status_badge.setStyleSheet("""
            background-color: #fee2e2; color: #991b1b; font-weight: bold; padding: 4px 10px; border-radius: 4px; font-size: 11px;
        """)
        t_row.addWidget(self.lbl_status_badge)
        c_lay.addLayout(t_row)

        # Metadata grid
        grid = QGridLayout()
        grid.setContentsMargins(0, 4, 0, 0)
        grid.setHorizontalSpacing(24)
        grid.setVerticalSpacing(6)

        self.lbl_invoice_val = QLabel("—")
        self.lbl_invoice_val.setStyleSheet("font-weight: 600; color: #1e40af;")
        grid.addWidget(self._make_label("Original Purchase / Invoice #:"), 0, 0)
        grid.addWidget(self.lbl_invoice_val, 0, 1)

        self.lbl_supplier_val = QLabel("—")
        self.lbl_supplier_val.setStyleSheet("font-weight: 600; color: #1e293b;")
        grid.addWidget(self._make_label("Supplier:"), 0, 2)
        grid.addWidget(self.lbl_supplier_val, 0, 3)

        self.lbl_date_val = QLabel("—")
        self.lbl_date_val.setStyleSheet("color: #475569;")
        grid.addWidget(self._make_label("Return Date:"), 1, 0)
        grid.addWidget(self.lbl_date_val, 1, 1)

        self.lbl_user_val = QLabel("—")
        self.lbl_user_val.setStyleSheet("color: #475569;")
        grid.addWidget(self._make_label("Processed By:"), 1, 2)
        grid.addWidget(self.lbl_user_val, 1, 3)

        self.lbl_reason_val = QLabel("—")
        self.lbl_reason_val.setStyleSheet("color: #0f172a; font-style: italic;")
        grid.addWidget(self._make_label("Return Reason:"), 2, 0)
        grid.addWidget(self.lbl_reason_val, 2, 1, 1, 3)

        c_lay.addLayout(grid)
        layout.addWidget(card)

        # ---------------------------------------------------------------------
        # 2. RETURNED ITEMS TABLE
        # ---------------------------------------------------------------------
        layout.addWidget(QLabel("<b>Returned Items (Stock Deducted):</b>"))

        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels([
            "Product Name", "Model", "Quantity Deducted", "Unit Cost Recorded"
        ])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setStyleSheet("""
            QTableWidget {
                background-color: #ffffff;
                border: 1px solid #e2e8f0;
                border-radius: 6px;
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
        layout.addWidget(self.table, stretch=1)

        # Close button
        btn_close = QPushButton("Close")
        btn_close.setStyleSheet("background-color: #f1f5f9; color: #334155; border: 1px solid #cbd5e1; padding: 7px 22px; border-radius: 5px; font-weight: 600;")
        btn_close.clicked.connect(self.accept)
        layout.addWidget(btn_close, alignment=Qt.AlignmentFlag.AlignRight)

    def _make_label(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setStyleSheet("color: #64748b; font-size: 11px; font-weight: 600;")
        return lbl

    def _load_data(self) -> None:
        self.details = self.partner_service.get_purchase_return_details(self.return_id)
        if not self.details:
            QMessageBox.warning(self, "Error", f"Could not load purchase return record #{self.return_id}.")
            self.reject()
            return

        ret_num = self.details.get("return_number", "")
        invoice = self.details.get("invoice_number", "—")
        supplier = self.details.get("supplier_name", "Unknown Supplier")
        raw_date = self.details.get("return_date", "")
        date_str = str(raw_date)[:16].replace("T", " ") if raw_date else "—"
        user = self.details.get("processed_by", "System")
        reason = self.details.get("reason") or "No reason provided"

        self.lbl_ret_num.setText(f"↩️ Return: {ret_num}")
        self.lbl_invoice_val.setText(invoice)
        self.lbl_supplier_val.setText(supplier)
        self.lbl_date_val.setText(date_str)
        self.lbl_user_val.setText(user)
        self.lbl_reason_val.setText(reason)

        items = self.details.get("items", [])
        self.table.setRowCount(len(items))

        for r_idx, itm in enumerate(items):
            c_name = QTableWidgetItem(itm.get("product_name", ""))
            c_name.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
            self.table.setItem(r_idx, 0, c_name)

            self.table.setItem(r_idx, 1, QTableWidgetItem(itm.get("product_model") or "—"))

            c_qty = QTableWidgetItem(f"-{itm.get('quantity', 0)} pcs")
            c_qty.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            c_qty.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
            c_qty.setForeground(QColor("#dc2626"))
            self.table.setItem(r_idx, 2, c_qty)

            c_cost = QTableWidgetItem(f"${itm.get('unit_cost', 0.0):,.2f}")
            c_cost.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.table.setItem(r_idx, 3, c_cost)

            self.table.setRowHeight(r_idx, 32)
