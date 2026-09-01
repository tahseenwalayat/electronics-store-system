"""
Suppliers Directory and Management View.
Provides live search, KPI metrics, CRUD operations, and access to full purchase history.
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
    QFrame,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QColor

from business.partner_service import PartnerService
from business.permissions import check_permission, can_manage, can_delete
from ui.dialogs.supplier_dialog import SupplierDialog
from ui.dialogs.supplier_detail_dialog import SupplierDetailDialog


class SuppliersView(QWidget):
    """
    Suppliers and Vendors Directory Screen.
    Fields: Supplier Name, Company/Shop Name, Phone Number, Address, Email.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.partner_service = PartnerService()
        self.raw_suppliers: List[Dict[str, Any]] = []

        self._setup_ui()
        self.load_suppliers()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        # ---------------------------------------------------------------------
        # 1. HEADER SECTION & PRIMARY ACTION
        # ---------------------------------------------------------------------
        top_bar = QHBoxLayout()
        header_layout = QVBoxLayout()
        header_layout.setSpacing(2)

        lbl_title = QLabel("🏭 Supplier Management")
        lbl_title.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        lbl_title.setStyleSheet("color: #0f172a;")
        lbl_subtitle = QLabel("Maintain wholesale distributor profiles, contact representatives, and inspect purchase histories.")
        lbl_subtitle.setStyleSheet("color: #64748b; font-size: 12px;")
        header_layout.addWidget(lbl_title)
        header_layout.addWidget(lbl_subtitle)
        top_bar.addLayout(header_layout)

        top_bar.addStretch()

        self.btn_new_supplier = QPushButton("➕ Add Supplier")
        self.btn_new_supplier.setStyleSheet("""
            QPushButton {
                background-color: #2563eb;
                color: white;
                padding: 8px 18px;
                border-radius: 6px;
                font-weight: bold;
                font-size: 13px;
                border: none;
            }
            QPushButton:hover {
                background-color: #1d4ed8;
            }
        """)
        self.btn_new_supplier.clicked.connect(self._open_new_supplier)
        top_bar.addWidget(self.btn_new_supplier)

        layout.addLayout(top_bar)

        # ---------------------------------------------------------------------
        # 2. KPI SUMMARY METRIC CHIPS
        # ---------------------------------------------------------------------
        kpi_bar = QHBoxLayout()
        kpi_bar.setSpacing(12)

        self.card_total = self._create_kpi_card("🏢 Total Suppliers", "0", "#0f172a")
        kpi_bar.addWidget(self.card_total)

        self.card_active = self._create_kpi_card("📦 With Purchase History", "0", "#0284c7")
        kpi_bar.addWidget(self.card_active)

        self.card_spend = self._create_kpi_card("💰 Total Inventory Sourced", "$0.00", "#15803d")
        kpi_bar.addWidget(self.card_spend)

        kpi_bar.addStretch()

        layout.addLayout(kpi_bar)

        # ---------------------------------------------------------------------
        # 3. LIVE SEARCH & FILTER BAR
        # ---------------------------------------------------------------------
        filter_bar = QHBoxLayout()
        filter_bar.setSpacing(10)

        self.txt_search = QLineEdit()
        self.txt_search.setPlaceholderText("🔍 Search suppliers by Company / Shop Name, Supplier Name, Phone, Email, Address...")
        self.txt_search.setFixedHeight(36)
        self.txt_search.setStyleSheet("padding: 6px 12px; border: 1.5px solid #cbd5e1; border-radius: 6px; font-size: 13px; background-color: #ffffff;")
        self.txt_search.textChanged.connect(self._filter_suppliers)
        filter_bar.addWidget(self.txt_search, stretch=1)

        self.btn_refresh = QPushButton("↻ Refresh")
        self.btn_refresh.setFixedHeight(36)
        self.btn_refresh.setStyleSheet("background-color: #ffffff; color: #1e293b; border: 1px solid #cbd5e1; padding: 6px 14px; border-radius: 6px; font-weight: 500;")
        self.btn_refresh.clicked.connect(self.load_suppliers)
        filter_bar.addWidget(self.btn_refresh)

        layout.addLayout(filter_bar)

        # ---------------------------------------------------------------------
        # 4. SUPPLIERS DATA TABLE
        # ---------------------------------------------------------------------
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "Company / Shop Name", "Supplier Name", "Phone Number", "Email", "Address", "Purchases", "Actions"
        ])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(6, 180)

        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setStyleSheet("""
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
                padding: 8px;
                border: none;
                border-bottom: 1.5px solid #cbd5e1;
            }
        """)
        self.table.cellDoubleClicked.connect(self._on_table_double_clicked)
        layout.addWidget(self.table)

    def _create_kpi_card(self, title: str, initial_val: str, color_hex: str) -> QFrame:
        card = QFrame()
        card.setStyleSheet("""
            QFrame {
                background-color: #ffffff;
                border: 1px solid #e2e8f0;
                border-radius: 8px;
                padding: 6px 14px;
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
    # DATA LOADING & FILTERING
    # -------------------------------------------------------------------------

    def load_suppliers(self) -> None:
        """Query suppliers directory and update metrics."""
        self.raw_suppliers = self.partner_service.get_all_suppliers()
        self._update_kpi_metrics()
        self._filter_suppliers()

    def _update_kpi_metrics(self) -> None:
        total_count = len(self.raw_suppliers)
        with_orders = sum(1 for s in self.raw_suppliers if s.get("total_purchases", 0) > 0)
        total_spend = sum(s.get("total_purchase_amount", 0.0) for s in self.raw_suppliers)

        self.card_total.lbl_val.setText(str(total_count))
        self.card_active.lbl_val.setText(f"{with_orders} suppliers")
        self.card_spend.lbl_val.setText(f"${total_spend:,.2f}")

    def _filter_suppliers(self) -> None:
        query = self.txt_search.text().strip().lower()
        filtered = []
        for s in getattr(self, "raw_suppliers", []):
            if query:
                name_m = query in (s.get("name") or "").lower()
                cp_m = query in (s.get("contact_person") or "").lower()
                phone_m = query in (s.get("phone") or "").lower()
                email_m = query in (s.get("email") or "").lower()
                addr_m = query in (s.get("address") or "").lower()
                if not (name_m or cp_m or phone_m or email_m or addr_m):
                    continue
            filtered.append(s)

        self.current_filtered_suppliers = filtered
        self._populate_table(filtered)

    def _populate_table(self, suppliers: List[Dict[str, Any]]) -> None:
        self.table.setRowCount(len(suppliers))
        can_edit = can_manage("suppliers")
        can_del = can_delete("suppliers")

        for row_idx, s in enumerate(suppliers):
            # 0. Company / Shop Name
            name_item = QTableWidgetItem(s.get("name", ""))
            name_item.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
            self.table.setItem(row_idx, 0, name_item)

            # 1. Supplier Name (Representative)
            rep_text = s.get("contact_person") or "—"
            c_rep = QTableWidgetItem(rep_text)
            c_rep.setForeground(QColor("#1e293b"))
            self.table.setItem(row_idx, 1, c_rep)

            # 2. Phone
            self.table.setItem(row_idx, 2, QTableWidgetItem(s.get("phone") or "—"))

            # 3. Email
            self.table.setItem(row_idx, 3, QTableWidgetItem(s.get("email") or "—"))

            # 4. Address
            self.table.setItem(row_idx, 4, QTableWidgetItem(s.get("address") or "—"))

            # 5. Purchases Count
            p_count = s.get("total_purchases", 0)
            p_item = QTableWidgetItem(f"{p_count} orders")
            p_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            p_item.setForeground(QColor("#0284c7") if p_count > 0 else QColor("#94a3b8"))
            self.table.setItem(row_idx, 5, p_item)

            # 6. Actions (View History / Edit / Delete)
            act_widget = QWidget()
            act_lay = QHBoxLayout(act_widget)
            act_lay.setContentsMargins(4, 2, 4, 2)
            act_lay.setSpacing(4)

            # View History
            btn_view = QPushButton("👁️ History")
            btn_view.setToolTip("View full purchase order history for this supplier")
            btn_view.setStyleSheet("background-color: #f0fdf4; color: #166534; border: 1px solid #bbf7d0; border-radius: 4px; padding: 3px 6px; font-size: 11px; font-weight: 600;")
            btn_view.clicked.connect(lambda _, s_data=s: self._open_supplier_detail(s_data))
            act_lay.addWidget(btn_view)

            # Edit
            btn_edit = QPushButton("Edit")
            btn_edit.setToolTip("Edit supplier contact and profile")
            btn_edit.setEnabled(can_edit)
            btn_edit.setStyleSheet("background-color: #eff6ff; color: #1d4ed8; border: 1px solid #bfdbfe; border-radius: 4px; padding: 3px 6px; font-size: 11px; font-weight: 600;")
            btn_edit.clicked.connect(lambda _, s_data=s: self._open_edit_supplier(s_data))
            act_lay.addWidget(btn_edit)

            # Delete
            btn_del = QPushButton("Delete")
            btn_del.setToolTip("Delete or archive supplier")
            btn_del.setEnabled(can_edit)
            btn_del.setStyleSheet("background-color: #fef2f2; color: #dc2626; border: 1px solid #fecaca; border-radius: 4px; padding: 3px 6px; font-size: 11px; font-weight: 600;")
            btn_del.clicked.connect(lambda _, s_data=s: self._on_delete_supplier(s_data))
            act_lay.addWidget(btn_del)

            self.table.setCellWidget(row_idx, 6, act_widget)
            self.table.setRowHeight(row_idx, 38)

    def _on_table_double_clicked(self, row: int, col: int) -> None:
        """Double clicking a row opens the Supplier Detail Dialog."""
        if 0 <= row < len(getattr(self, "current_filtered_suppliers", [])):
            s = self.current_filtered_suppliers[row]
            self._open_supplier_detail(s)

    def _open_new_supplier(self) -> None:
        if not check_permission("suppliers.manage", parent=self, action_name="create suppliers"):
            return
        dlg = SupplierDialog(self.partner_service, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.load_suppliers()

    def _open_edit_supplier(self, supplier_data: Dict[str, Any]) -> None:
        if not check_permission("suppliers.manage", parent=self, action_name="edit supplier"):
            return
        dlg = SupplierDialog(self.partner_service, supplier_data=supplier_data, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.load_suppliers()

    def _open_supplier_detail(self, supplier_data: Dict[str, Any]) -> None:
        """Open detailed supplier view with full purchase order history."""
        dlg = SupplierDetailDialog(supplier_data["id"], partner_service=self.partner_service, parent=self)
        dlg.supplier_updated.connect(self.load_suppliers)
        dlg.exec()
        self.load_suppliers()

    def _on_delete_supplier(self, supplier_data: Dict[str, Any]) -> None:
        """Delete or archive supplier with user confirmation."""
        if not check_permission("suppliers.manage", parent=self, action_name="delete supplier"):
            return

        s_id = supplier_data["id"]
        s_name = supplier_data["name"]
        p_count = supplier_data.get("total_purchases", 0)

        warn_msg = f"Are you sure you want to delete supplier '<b>{s_name}</b>'?"
        if p_count > 0:
            warn_msg += (
                f"\n\n• This supplier has <b>{p_count}</b> historical purchase order(s).\n"
                "• The supplier will be archived from active lists while preserving historical purchase records."
            )

        reply = QMessageBox.question(
            self,
            "Confirm Supplier Deletion",
            warn_msg,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        ok, msg = self.partner_service.delete_supplier(s_id)
        if not ok:
            QMessageBox.critical(self, "Error Deleting Supplier", msg)
            return

        QMessageBox.information(self, "Supplier Deleted", msg)
        self.load_suppliers()

