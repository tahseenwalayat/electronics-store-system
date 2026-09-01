"""
Purchase Return Confirmation Dialog.
Enforces FULL return of an entire purchase order transaction.
Decreases stock for each item, writes audit log, and performs zero financial tracking.
"""

from typing import Optional, Dict, Any, List
from PySide6.QtWidgets import (
    QDialog,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QMessageBox,
    QFrame,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QColor

from business.partner_service import PartnerService
from business.session import get_session
from business.permissions import check_permission


class PurchaseReturnDialog(QDialog):
    """
    Dialog to process a FULL return of a supplier purchase order.
    """

    def __init__(self, purchase_id: int, partner_service: Optional[PartnerService] = None, parent=None):
        super().__init__(parent)
        self.purchase_id = purchase_id
        self.partner_service = partner_service or PartnerService()
        self.session = get_session()
        self.purchase_details: Optional[Dict[str, Any]] = None

        self.setWindowTitle("↩️ Process Full Purchase Return — Electronics Store System")
        self.resize(760, 540)
        self.setMinimumSize(680, 460)

        self._setup_ui()
        self._load_purchase_data()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(14)

        # ---------------------------------------------------------------------
        # 1. WARNING & POLICY BANNER
        # ---------------------------------------------------------------------
        warn_box = QFrame()
        warn_box.setStyleSheet("""
            QFrame {
                background-color: #fffbeb;
                border: 1.5px solid #fde68a;
                border-radius: 8px;
                padding: 10px 14px;
            }
        """)
        wb_lay = QVBoxLayout(warn_box)
        wb_lay.setContentsMargins(4, 2, 4, 2)
        wb_lay.setSpacing(4)

        lbl_w_title = QLabel("⚠️ Full Purchase Return Policy")
        lbl_w_title.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        lbl_w_title.setStyleSheet("color: #92400e;")
        wb_lay.addWidget(lbl_w_title)

        lbl_w_desc = QLabel(
            "• Only a <b>FULL return</b> of this purchase transaction is permitted (no partial returns).<br>"
            "• Current inventory stock for each product will immediately <b>decrease</b> by the quantities below.<br>"
            "• This strictly affects physical inventory stock (no financial refund or payable tracking)."
        )
        lbl_w_desc.setStyleSheet("color: #78350f; font-size: 11px;")
        wb_lay.addWidget(lbl_w_desc)

        layout.addWidget(warn_box)

        # ---------------------------------------------------------------------
        # 2. PURCHASE DETAILS CARD
        # ---------------------------------------------------------------------
        card = QFrame()
        card.setStyleSheet("""
            QFrame {
                background-color: #ffffff;
                border: 1px solid #e2e8f0;
                border-radius: 8px;
                padding: 10px 14px;
            }
        """)
        c_grid = QGridLayout(card)
        c_grid.setContentsMargins(6, 4, 6, 4)
        c_grid.setHorizontalSpacing(20)
        c_grid.setVerticalSpacing(6)

        self.lbl_po_val = QLabel("—")
        self.lbl_po_val.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        self.lbl_po_val.setStyleSheet("color: #1e40af;")
        c_grid.addWidget(self._make_label("Invoice / PO #:"), 0, 0)
        c_grid.addWidget(self.lbl_po_val, 0, 1)

        self.lbl_supplier_val = QLabel("—")
        self.lbl_supplier_val.setStyleSheet("font-weight: 600; color: #1e293b;")
        c_grid.addWidget(self._make_label("Supplier:"), 0, 2)
        c_grid.addWidget(self.lbl_supplier_val, 0, 3)

        self.lbl_date_val = QLabel("—")
        self.lbl_date_val.setStyleSheet("color: #475569;")
        c_grid.addWidget(self._make_label("Purchase Date:"), 1, 0)
        c_grid.addWidget(self.lbl_date_val, 1, 1)

        self.lbl_status_val = QLabel("—")
        self.lbl_status_val.setStyleSheet("font-weight: 600; color: #16a34a;")
        c_grid.addWidget(self._make_label("Order Status:"), 1, 2)
        c_grid.addWidget(self.lbl_status_val, 1, 3)

        layout.addWidget(card)

        # ---------------------------------------------------------------------
        # 3. ITEMS TO BE DEDUCTED TABLE
        # ---------------------------------------------------------------------
        layout.addWidget(QLabel("<b>Items Being Returned (Stock will be deducted):</b>"))

        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels([
            "Product Name", "Model", "Qty to Deduct", "Unit Cost"
        ])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
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
                padding: 6px;
                border: none;
                border-bottom: 1.5px solid #cbd5e1;
            }
        """)
        layout.addWidget(self.table, stretch=1)

        # ---------------------------------------------------------------------
        # 4. RETURN REASON INPUT
        # ---------------------------------------------------------------------
        reason_row = QHBoxLayout()
        reason_row.setSpacing(10)
        lbl_r = QLabel("<b>Return Reason *:</b>")
        reason_row.addWidget(lbl_r)

        self.txt_reason = QLineEdit()
        self.txt_reason.setPlaceholderText("e.g. Defective shipment batch, damaged in transit, supplier recall...")
        self.txt_reason.setFixedHeight(34)
        self.txt_reason.setStyleSheet("padding: 4px 10px; border: 1.5px solid #cbd5e1; border-radius: 6px;")
        reason_row.addWidget(self.txt_reason, stretch=1)

        layout.addLayout(reason_row)

        # ---------------------------------------------------------------------
        # 5. BOTTOM ACTIONS
        # ---------------------------------------------------------------------
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.setStyleSheet("background-color: #f1f5f9; color: #334155; border: 1px solid #cbd5e1; padding: 8px 18px; border-radius: 6px; font-weight: 500;")
        self.btn_cancel.clicked.connect(self.reject)
        btn_row.addWidget(self.btn_cancel)

        btn_row.addStretch()

        self.btn_confirm_return = QPushButton("↩️ Confirm Full Return & Deduct Stock")
        self.btn_confirm_return.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        self.btn_confirm_return.setStyleSheet("""
            QPushButton {
                background-color: #dc2626;
                color: #ffffff;
                padding: 9px 22px;
                border-radius: 6px;
                border: none;
            }
            QPushButton:hover {
                background-color: #b91c1c;
            }
        """)
        self.btn_confirm_return.clicked.connect(self._on_confirm_return)
        btn_row.addWidget(self.btn_confirm_return)

        layout.addLayout(btn_row)

    def _make_label(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setStyleSheet("color: #64748b; font-size: 11px; font-weight: 600;")
        return lbl

    def _load_purchase_data(self) -> None:
        self.purchase_details = self.partner_service.get_purchase_details(self.purchase_id)
        if not self.purchase_details:
            QMessageBox.warning(self, "Error", f"Purchase order #{self.purchase_id} details could not be loaded.")
            self.reject()
            return

        po_num = self.purchase_details.get("purchase_number", "")
        supplier = self.purchase_details.get("supplier_name", "Unknown Supplier")
        raw_date = self.purchase_details.get("purchase_date", "")
        date_str = str(raw_date)[:16].replace("T", " ") if raw_date else "—"

        self.lbl_po_val.setText(po_num)
        self.lbl_supplier_val.setText(supplier)
        self.lbl_date_val.setText(date_str)
        self.lbl_status_val.setText("COMPLETED / RECEIVED")

        # Load Items
        items = self.purchase_details.get("items", [])
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

    def _on_confirm_return(self) -> None:
        if not check_permission("purchases.manage", parent=self, action_name="process purchase returns"):
            return

        reason = self.txt_reason.text().strip()
        if not reason:
            QMessageBox.warning(self, "Reason Required", "Please enter a reason for returning this purchase order.")
            self.txt_reason.setFocus()
            return

        user_id = self.session.current_user.id if self.session.current_user else 1

        confirm_msg = (
            f"Are you sure you want to execute a <b>FULL RETURN</b> for Purchase <b>{self.lbl_po_val.text()}</b>?\n\n"
            f"• <b>Supplier:</b> {self.lbl_supplier_val.text()}\n"
            f"• <b>Items to Return:</b> {len(self.purchase_details.get('items', []))} products\n"
            f"• <b>Reason:</b> {reason}\n\n"
            "Inventory stock will be deducted immediately. This action cannot be undone."
        )

        reply = QMessageBox.question(
            self,
            "Confirm Full Purchase Return",
            confirm_msg,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        success, ret_num, msg = self.partner_service.process_purchase_return(
            user_id=user_id,
            purchase_id=self.purchase_id,
            reason=reason,
        )

        if not success:
            QMessageBox.critical(self, "Return Failed", msg)
            return

        QMessageBox.information(
            self,
            "Purchase Returned",
            f"🎉 <b>Full Purchase Return '{ret_num}' Processed!</b>\n\n"
            "• Inventory stock has been decreased back to previous levels.\n"
            "• Purchase status updated to Cancelled/Returned.\n"
            "• Audit log entry recorded.",
        )
        self.accept()
