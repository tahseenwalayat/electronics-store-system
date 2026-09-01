"""
Purchase Order Detail Dialog.
Displays full inspection view of a recorded inbound purchase order with itemized product lines.
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


class PurchaseDetailDialog(QDialog):
    """
    Dialog displaying detailed invoice metadata and line-by-line product breakdown for a purchase order.
    """

    def __init__(self, purchase_id: int, partner_service: Optional[PartnerService] = None, parent=None):
        super().__init__(parent)
        self.purchase_id = purchase_id
        self.partner_service = partner_service or PartnerService()
        self.details: Optional[Dict[str, Any]] = None

        self.setWindowTitle("📦 Purchase Order Details — Electronics Store System")
        self.resize(780, 560)
        self.setMinimumSize(680, 460)

        self._setup_ui()
        self._load_data()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(14)

        # ---------------------------------------------------------------------
        # 1. TOP INVOICE METADATA CARD
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
        self.lbl_po_num = QLabel("Invoice / PO: Loading...")
        self.lbl_po_num.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        self.lbl_po_num.setStyleSheet("color: #0f172a;")
        t_row.addWidget(self.lbl_po_num)

        t_row.addStretch()

        self.lbl_status_badge = QLabel("RECEIVED")
        self.lbl_status_badge.setStyleSheet("""
            background-color: #dcfce7; color: #15803d; font-weight: bold; padding: 4px 10px; border-radius: 4px; font-size: 11px;
        """)
        t_row.addWidget(self.lbl_status_badge)

        self.btn_return = QPushButton("↩️ Return Purchase")
        self.btn_return.setStyleSheet("""
            QPushButton {
                background-color: #fee2e2;
                color: #991b1b;
                border: 1px solid #fecaca;
                font-weight: 600;
                padding: 4px 12px;
                border-radius: 4px;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #fecaca;
            }
        """)
        self.btn_return.clicked.connect(self._on_return_clicked)
        t_row.addWidget(self.btn_return)

        c_lay.addLayout(t_row)

        # Metadata grid
        grid = QGridLayout()
        grid.setContentsMargins(0, 4, 0, 0)
        grid.setHorizontalSpacing(24)
        grid.setVerticalSpacing(6)

        self.lbl_supplier_val = QLabel("—")
        self.lbl_supplier_val.setStyleSheet("font-weight: 600; color: #1e293b;")
        grid.addWidget(self._make_label("Supplier:"), 0, 0)
        grid.addWidget(self.lbl_supplier_val, 0, 1)

        self.lbl_date_val = QLabel("—")
        self.lbl_date_val.setStyleSheet("color: #475569;")
        grid.addWidget(self._make_label("Purchase Date:"), 0, 2)
        grid.addWidget(self.lbl_date_val, 0, 3)

        self.lbl_payment_val = QLabel("—")
        self.lbl_payment_val.setStyleSheet("color: #475569;")
        grid.addWidget(self._make_label("Payment Method:"), 1, 0)
        grid.addWidget(self.lbl_payment_val, 1, 1)

        self.lbl_notes_val = QLabel("—")
        self.lbl_notes_val.setStyleSheet("color: #64748b; font-style: italic;")
        grid.addWidget(self._make_label("Notes:"), 1, 2)
        grid.addWidget(self.lbl_notes_val, 1, 3)

        c_lay.addLayout(grid)
        layout.addWidget(card)

        # ---------------------------------------------------------------------
        # 2. LINE ITEMS TABLE
        # ---------------------------------------------------------------------
        layout.addWidget(QLabel("<b>Purchased Line Items:</b>"))

        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels([
            "Product Name", "Model", "Unit Cost Paid", "Quantity", "Line Subtotal"
        ])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
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

        # ---------------------------------------------------------------------
        # 3. SUMMARY & TOTAL FOOTER
        # ---------------------------------------------------------------------
        bot_frame = QFrame()
        bot_frame.setStyleSheet("background-color: #f8fafc; border: 1px solid #e2e8f0; border-radius: 6px; padding: 8px 14px;")
        bot_lay = QHBoxLayout(bot_frame)
        bot_lay.setContentsMargins(6, 4, 6, 4)

        self.lbl_units_sum = QLabel("0 items • 0 units")
        self.lbl_units_sum.setStyleSheet("color: #64748b; font-size: 12px; font-weight: 500;")
        bot_lay.addWidget(self.lbl_units_sum)

        bot_lay.addStretch()

        bot_lay.addWidget(QLabel("<b>Grand Total:</b>"))
        self.lbl_grand_total = QLabel("<b>$0.00</b>")
        self.lbl_grand_total.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        self.lbl_grand_total.setStyleSheet("color: #15803d;")
        bot_lay.addWidget(self.lbl_grand_total)

        layout.addWidget(bot_frame)

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
        self.details = self.partner_service.get_purchase_details(self.purchase_id)
        if not self.details:
            QMessageBox.warning(self, "Error", f"Could not load purchase order #{self.purchase_id}.")
            self.reject()
            return

        po_num = self.details.get("purchase_number", "")
        supplier = self.details.get("supplier_name", "Unknown Supplier")
        raw_date = self.details.get("purchase_date", "")
        date_str = str(raw_date)[:16].replace("T", " ") if raw_date else "—"
        payment = self.details.get("payment_method", "").replace("_", " ").title()
        notes = self.details.get("notes") or "None"
        total = self.details.get("total_amount", 0.0)
        status = self.details.get("status", "received")

        self.lbl_po_num.setText(f"📦 Invoice / PO: {po_num}")
        self.lbl_supplier_val.setText(supplier)
        self.lbl_date_val.setText(date_str)
        self.lbl_payment_val.setText(payment)
        self.lbl_notes_val.setText(notes)
        self.lbl_grand_total.setText(f"<b>${total:,.2f}</b>")

        if status == "cancelled":
            self.lbl_status_badge.setText("FULLY RETURNED")
            self.lbl_status_badge.setStyleSheet("background-color: #fee2e2; color: #991b1b; font-weight: bold; padding: 4px 10px; border-radius: 4px; font-size: 11px;")
            self.btn_return.setVisible(False)
        else:
            self.lbl_status_badge.setText("RECEIVED")
            self.lbl_status_badge.setStyleSheet("background-color: #dcfce7; color: #15803d; font-weight: bold; padding: 4px 10px; border-radius: 4px; font-size: 11px;")
            self.btn_return.setVisible(True)

        # Items
        items = self.details.get("items", [])
        self.table.setRowCount(len(items))
        total_units = sum(i.get("quantity", 0) for i in items)
        self.lbl_units_sum.setText(f"{len(items)} line item(s) • {total_units} total units received")

        for r_idx, itm in enumerate(items):
            c_name = QTableWidgetItem(itm.get("product_name", ""))
            c_name.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
            self.table.setItem(r_idx, 0, c_name)

            self.table.setItem(r_idx, 1, QTableWidgetItem(itm.get("product_model") or "—"))

            c_cost = QTableWidgetItem(f"${itm.get('unit_cost', 0.0):,.2f}")
            c_cost.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.table.setItem(r_idx, 2, c_cost)

            c_qty = QTableWidgetItem(f"{itm.get('quantity', 0)} pcs")
            c_qty.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(r_idx, 3, c_qty)

            c_sub = QTableWidgetItem(f"${itm.get('subtotal', 0.0):,.2f}")
            c_sub.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            c_sub.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
            c_sub.setForeground(QColor("#15803d"))
            self.table.setItem(r_idx, 4, c_sub)

            self.table.setRowHeight(r_idx, 32)

    def _on_return_clicked(self) -> None:
        from ui.dialogs.purchase_return_dialog import PurchaseReturnDialog
        dlg = PurchaseReturnDialog(self.purchase_id, partner_service=self.partner_service, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self._load_data()

