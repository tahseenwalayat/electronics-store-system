"""
Purchases and Inbound Inventory View.
Provides complete Purchase Management and Purchase Return History screens:
- Tab 1: Purchase Orders History (with supplier & date filters, stock receipt, full return action)
- Tab 2: Purchase Return History (audit log of returned purchases and stock deductions)
"""

from typing import Optional, Dict, Any, List
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QComboBox,
    QDateEdit,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QMessageBox,
    QDialog,
    QFrame,
    QTabWidget,
)
from PySide6.QtCore import Qt, QDate
from PySide6.QtGui import QFont, QColor

from business.product_service import ProductService
from business.partner_service import PartnerService
from business.permissions import check_permission, can_manage
from ui.dialogs.add_purchase_dialog import AddPurchaseDialog
from ui.dialogs.purchase_detail_dialog import PurchaseDetailDialog
from ui.dialogs.purchase_return_dialog import PurchaseReturnDialog
from ui.dialogs.purchase_return_detail_dialog import PurchaseReturnDetailDialog


class PurchasesView(QWidget):
    """
    Purchases & Inbound Inventory Management and Returns Screen.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.product_service = ProductService()
        self.partner_service = PartnerService()
        self.raw_purchases: List[Dict[str, Any]] = []
        self.raw_returns: List[Dict[str, Any]] = []

        self._setup_ui()
        self._load_supplier_filters()
        self.load_all_data()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        # ---------------------------------------------------------------------
        # 1. TOP HEADER & PRIMARY ACTION BAR
        # ---------------------------------------------------------------------
        top_bar = QHBoxLayout()
        header_layout = QVBoxLayout()
        header_layout.setSpacing(2)

        lbl_title = QLabel("🚚 Inbound Purchases & Stock Management")
        lbl_title.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        lbl_title.setStyleSheet("color: #0f172a;")
        lbl_subtitle = QLabel("Record supplier shipments to increase catalog stock, execute full purchase returns, and audit wholesale history.")
        lbl_subtitle.setStyleSheet("color: #64748b; font-size: 12px;")
        header_layout.addWidget(lbl_title)
        header_layout.addWidget(lbl_subtitle)
        top_bar.addLayout(header_layout)

        top_bar.addStretch()

        self.btn_new_purchase = QPushButton("➕ Record New Purchase")
        self.btn_new_purchase.setStyleSheet("""
            QPushButton {
                background-color: #2563eb;
                color: white;
                padding: 9px 20px;
                border-radius: 6px;
                font-weight: bold;
                font-size: 13px;
                border: none;
            }
            QPushButton:hover {
                background-color: #1d4ed8;
            }
        """)
        self.btn_new_purchase.clicked.connect(self._open_new_purchase)
        top_bar.addWidget(self.btn_new_purchase)

        layout.addLayout(top_bar)

        # ---------------------------------------------------------------------
        # 2. MAIN TABS (Purchase Orders vs Purchase Returns)
        # ---------------------------------------------------------------------
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #e2e8f0;
                border-radius: 8px;
                background-color: #ffffff;
                padding: 12px;
            }
            QTabBar::tab {
                background: #f1f5f9;
                color: #475569;
                font-weight: 600;
                padding: 8px 18px;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                margin-right: 4px;
            }
            QTabBar::tab:selected {
                background: #ffffff;
                color: #2563eb;
                border: 1px solid #e2e8f0;
                border-bottom: none;
            }
        """)

        # Tab 1: Inbound Purchase Orders
        self.tab_purchases = QWidget()
        self._setup_purchases_tab(self.tab_purchases)
        self.tabs.addTab(self.tab_purchases, "📦 Inbound Purchase Orders")

        # Tab 2: Purchase Return History
        self.tab_returns = QWidget()
        self._setup_returns_tab(self.tab_returns)
        self.tabs.addTab(self.tab_returns, "↩️ Purchase Return History")

        layout.addWidget(self.tabs, stretch=1)

    # -------------------------------------------------------------------------
    # TAB 1: PURCHASES ORDERS
    # -------------------------------------------------------------------------

    def _setup_purchases_tab(self, tab: QWidget) -> None:
        t_lay = QVBoxLayout(tab)
        t_lay.setContentsMargins(4, 4, 4, 4)
        t_lay.setSpacing(12)

        # KPI Bar
        kpi_bar = QHBoxLayout()
        kpi_bar.setSpacing(12)
        self.card_orders = self._create_kpi_card("📦 Purchase Orders", "0", "#0f172a")
        kpi_bar.addWidget(self.card_orders)
        self.card_units = self._create_kpi_card("📊 Units Restocked", "0 units", "#0284c7")
        kpi_bar.addWidget(self.card_units)
        self.card_spend = self._create_kpi_card("💰 Total Sourced Cost", "$0.00", "#15803d")
        kpi_bar.addWidget(self.card_spend)
        kpi_bar.addStretch()
        self.lbl_record_count = QLabel("Showing 0 purchases")
        self.lbl_record_count.setStyleSheet("color: #64748b; font-size: 12px; font-weight: 500;")
        kpi_bar.addWidget(self.lbl_record_count)
        t_lay.addLayout(kpi_bar)

        # Filters
        filter_card = QFrame()
        filter_card.setStyleSheet("background-color: #f8fafc; border: 1px solid #e2e8f0; border-radius: 6px; padding: 6px 10px;")
        f_lay = QHBoxLayout(filter_card)
        f_lay.setContentsMargins(2, 2, 2, 2)
        f_lay.setSpacing(10)

        f_lay.addWidget(QLabel("<b>Search:</b>"))
        self.txt_search = QLineEdit()
        self.txt_search.setPlaceholderText("Invoice / PO #, Supplier name...")
        self.txt_search.setFixedHeight(30)
        self.txt_search.setStyleSheet("padding: 3px 8px; border: 1px solid #cbd5e1; border-radius: 4px; background-color: #ffffff;")
        self.txt_search.textChanged.connect(self._apply_purchase_filters)
        f_lay.addWidget(self.txt_search, stretch=2)

        f_lay.addWidget(QLabel("<b>Supplier:</b>"))
        self.cmb_supplier_filter = QComboBox()
        self.cmb_supplier_filter.setFixedHeight(30)
        self.cmb_supplier_filter.addItem("All Suppliers", 0)
        self.cmb_supplier_filter.currentIndexChanged.connect(self._apply_purchase_filters)
        f_lay.addWidget(self.cmb_supplier_filter, stretch=2)

        f_lay.addWidget(QLabel("<b>From:</b>"))
        self.date_start = QDateEdit()
        self.date_start.setCalendarPopup(True)
        self.date_start.setDate(QDate.currentDate().addMonths(-6))
        self.date_start.setDisplayFormat("yyyy-MM-dd")
        self.date_start.setFixedHeight(30)
        self.date_start.dateChanged.connect(self._apply_purchase_filters)
        f_lay.addWidget(self.date_start)

        f_lay.addWidget(QLabel("<b>To:</b>"))
        self.date_end = QDateEdit()
        self.date_end.setCalendarPopup(True)
        self.date_end.setDate(QDate.currentDate().addDays(1))
        self.date_end.setDisplayFormat("yyyy-MM-dd")
        self.date_end.setFixedHeight(30)
        self.date_end.dateChanged.connect(self._apply_purchase_filters)
        f_lay.addWidget(self.date_end)

        self.btn_reset_dates = QPushButton("Reset Dates")
        self.btn_reset_dates.setFixedHeight(30)
        self.btn_reset_dates.setStyleSheet("background-color: #ffffff; color: #475569; border: 1px solid #cbd5e1; padding: 3px 8px; border-radius: 4px; font-size: 11px;")
        self.btn_reset_dates.clicked.connect(self._reset_purchase_dates)
        f_lay.addWidget(self.btn_reset_dates)

        self.btn_refresh = QPushButton("↻ Refresh")
        self.btn_refresh.setFixedHeight(30)
        self.btn_refresh.setStyleSheet("background-color: #ffffff; color: #1e293b; border: 1px solid #cbd5e1; padding: 3px 10px; border-radius: 4px; font-weight: 500;")
        self.btn_refresh.clicked.connect(self.load_all_data)
        f_lay.addWidget(self.btn_refresh)

        t_lay.addWidget(filter_card)

        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels([
            "Invoice / PO #", "Supplier", "Purchase Date", "Items Summary", "Units", "Total Amount", "Status", "Actions"
        ])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(7, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(7, 160)

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
                padding: 7px;
                border: none;
                border-bottom: 1.5px solid #cbd5e1;
            }
        """)
        self.table.cellDoubleClicked.connect(self._on_purchase_double_clicked)
        t_lay.addWidget(self.table, stretch=1)

    # -------------------------------------------------------------------------
    # TAB 2: PURCHASE RETURNS HISTORY
    # -------------------------------------------------------------------------

    def _setup_returns_tab(self, tab: QWidget) -> None:
        r_lay = QVBoxLayout(tab)
        r_lay.setContentsMargins(4, 4, 4, 4)
        r_lay.setSpacing(12)

        # KPI Bar
        kpi_bar = QHBoxLayout()
        kpi_bar.setSpacing(12)
        self.card_ret_count = self._create_kpi_card("↩️ Full Returns Processed", "0", "#991b1b")
        kpi_bar.addWidget(self.card_ret_count)
        self.card_ret_units = self._create_kpi_card("📉 Units Deducted", "0 units", "#dc2626")
        kpi_bar.addWidget(self.card_ret_units)
        kpi_bar.addStretch()
        self.lbl_returns_count = QLabel("Showing 0 returns")
        self.lbl_returns_count.setStyleSheet("color: #64748b; font-size: 12px; font-weight: 500;")
        kpi_bar.addWidget(self.lbl_returns_count)
        r_lay.addLayout(kpi_bar)

        # Filter Bar
        f_card = QFrame()
        f_card.setStyleSheet("background-color: #f8fafc; border: 1px solid #e2e8f0; border-radius: 6px; padding: 6px 10px;")
        f_lay = QHBoxLayout(f_card)
        f_lay.setContentsMargins(2, 2, 2, 2)
        f_lay.setSpacing(10)

        f_lay.addWidget(QLabel("<b>Search:</b>"))
        self.txt_ret_search = QLineEdit()
        self.txt_ret_search.setPlaceholderText("Return #, Invoice #, Supplier...")
        self.txt_ret_search.setFixedHeight(30)
        self.txt_ret_search.setStyleSheet("padding: 3px 8px; border: 1px solid #cbd5e1; border-radius: 4px; background-color: #ffffff;")
        self.txt_ret_search.textChanged.connect(self._apply_return_filters)
        f_lay.addWidget(self.txt_ret_search, stretch=2)

        f_lay.addWidget(QLabel("<b>Supplier:</b>"))
        self.cmb_ret_supplier_filter = QComboBox()
        self.cmb_ret_supplier_filter.setFixedHeight(30)
        self.cmb_ret_supplier_filter.addItem("All Suppliers", 0)
        self.cmb_ret_supplier_filter.currentIndexChanged.connect(self._apply_return_filters)
        f_lay.addWidget(self.cmb_ret_supplier_filter, stretch=2)

        f_lay.addWidget(QLabel("<b>From:</b>"))
        self.date_ret_start = QDateEdit()
        self.date_ret_start.setCalendarPopup(True)
        self.date_ret_start.setDate(QDate.currentDate().addMonths(-6))
        self.date_ret_start.setDisplayFormat("yyyy-MM-dd")
        self.date_ret_start.setFixedHeight(30)
        self.date_ret_start.dateChanged.connect(self._apply_return_filters)
        f_lay.addWidget(self.date_ret_start)

        f_lay.addWidget(QLabel("<b>To:</b>"))
        self.date_ret_end = QDateEdit()
        self.date_ret_end.setCalendarPopup(True)
        self.date_ret_end.setDate(QDate.currentDate().addDays(1))
        self.date_ret_end.setDisplayFormat("yyyy-MM-dd")
        self.date_ret_end.setFixedHeight(30)
        self.date_ret_end.dateChanged.connect(self._apply_return_filters)
        f_lay.addWidget(self.date_ret_end)

        btn_ret_refresh = QPushButton("↻ Refresh")
        btn_ret_refresh.setFixedHeight(30)
        btn_ret_refresh.setStyleSheet("background-color: #ffffff; color: #1e293b; border: 1px solid #cbd5e1; padding: 3px 10px; border-radius: 4px; font-weight: 500;")
        btn_ret_refresh.clicked.connect(self.load_all_data)
        f_lay.addWidget(btn_ret_refresh)

        r_lay.addWidget(f_card)

        # Returns Table
        self.table_returns = QTableWidget()
        self.table_returns.setColumnCount(8)
        self.table_returns.setHorizontalHeaderLabels([
            "Return #", "Invoice #", "Supplier", "Return Date", "Returned Items", "Units Deducted", "Processed By", "Actions"
        ])
        self.table_returns.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table_returns.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table_returns.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table_returns.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table_returns.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        self.table_returns.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        self.table_returns.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)
        self.table_returns.horizontalHeader().setSectionResizeMode(7, QHeaderView.ResizeMode.Fixed)
        self.table_returns.setColumnWidth(7, 100)

        self.table_returns.verticalHeader().setVisible(False)
        self.table_returns.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table_returns.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table_returns.setStyleSheet("""
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
        self.table_returns.cellDoubleClicked.connect(self._on_return_double_clicked)
        r_lay.addWidget(self.table_returns, stretch=1)

    def _create_kpi_card(self, title: str, initial_val: str, color_hex: str) -> QFrame:
        card = QFrame()
        card.setStyleSheet("background-color: #ffffff; border: 1px solid #e2e8f0; border-radius: 8px; padding: 6px 14px;")
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

    def _load_supplier_filters(self) -> None:
        suppliers = self.partner_service.get_all_suppliers()
        for cmb in (self.cmb_supplier_filter, self.cmb_ret_supplier_filter):
            cur = cmb.currentData()
            cmb.blockSignals(True)
            cmb.clear()
            cmb.addItem("All Suppliers", 0)
            for s in suppliers:
                cmb.addItem(s["name"], s["id"])
            idx = cmb.findData(cur)
            if idx >= 0:
                cmb.setCurrentIndex(idx)
            cmb.blockSignals(False)

    def _reset_purchase_dates(self) -> None:
        self.date_start.blockSignals(True)
        self.date_end.blockSignals(True)
        self.date_start.setDate(QDate.currentDate().addYears(-3))
        self.date_end.setDate(QDate.currentDate().addDays(1))
        self.date_start.blockSignals(False)
        self.date_end.blockSignals(False)
        self._apply_purchase_filters()

    def load_all_data(self) -> None:
        self._load_supplier_filters()
        self._apply_purchase_filters()
        self._apply_return_filters()

    def _apply_purchase_filters(self) -> None:
        query = self.txt_search.text().strip()
        supplier_id = self.cmb_supplier_filter.currentData()
        start_date = self.date_start.date().toString("yyyy-MM-dd")
        end_date = self.date_end.date().toString("yyyy-MM-dd")

        purchases = self.partner_service.get_all_purchases(
            query=query,
            supplier_id=supplier_id if supplier_id and supplier_id > 0 else None,
            start_date=start_date,
            end_date=end_date,
            limit=300,
        )

        self.current_purchases = purchases
        self._populate_purchases_table(purchases)

        # Update KPIs
        total_orders = len(purchases)
        total_units = sum(p.get("total_units_received", 0) for p in purchases)
        total_spend = sum(p.get("total_amount", 0.0) for p in purchases)
        self.card_orders.lbl_val.setText(str(total_orders))
        self.card_units.lbl_val.setText(f"{total_units} units")
        self.card_spend.lbl_val.setText(f"${total_spend:,.2f}")
        self.lbl_record_count.setText(f"Showing {total_orders} purchase order(s)")

    def _populate_purchases_table(self, purchases: List[Dict[str, Any]]) -> None:
        self.table.setRowCount(len(purchases))

        for row_idx, p in enumerate(purchases):
            # 0. PO Number
            po_item = QTableWidgetItem(p["purchase_number"])
            po_item.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
            po_item.setForeground(QColor("#1e40af"))
            self.table.setItem(row_idx, 0, po_item)

            # 1. Supplier
            s_name = p.get("supplier_name", "Unknown Supplier")
            self.table.setItem(row_idx, 1, QTableWidgetItem(s_name))

            # 2. Date
            raw_date = p.get("purchase_date", "")
            date_str = str(raw_date)[:16].replace("T", " ") if raw_date else "—"
            c_date = QTableWidgetItem(date_str)
            c_date.setForeground(QColor("#475569"))
            self.table.setItem(row_idx, 2, c_date)

            # 3. Items Summary
            summary_txt = p.get("items_summary") or "No items listed"
            c_summary = QTableWidgetItem(summary_txt)
            c_summary.setToolTip(summary_txt)
            self.table.setItem(row_idx, 3, c_summary)

            # 4. Units
            units_val = p.get("total_units_received", 0)
            c_units = QTableWidgetItem(f"{units_val} pcs")
            c_units.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row_idx, 4, c_units)

            # 5. Total Cost
            tot_val = p.get("total_amount", 0.0)
            tot_item = QTableWidgetItem(f"${tot_val:,.2f}")
            tot_item.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
            tot_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            tot_item.setForeground(QColor("#15803d"))
            self.table.setItem(row_idx, 5, tot_item)

            # 6. Status
            is_returned = p.get("status") == "cancelled"
            stat_item = QTableWidgetItem("RETURNED" if is_returned else "RECEIVED")
            stat_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            stat_item.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
            stat_item.setForeground(QColor("#dc2626" if is_returned else "#15803d"))
            self.table.setItem(row_idx, 6, stat_item)

            # 7. Actions (Details & Return)
            act_w = QWidget()
            act_l = QHBoxLayout(act_w)
            act_l.setContentsMargins(4, 2, 4, 2)
            act_l.setSpacing(4)

            btn_details = QPushButton("🔍 Details")
            btn_details.setStyleSheet("background-color: #eff6ff; color: #1d4ed8; border: 1px solid #bfdbfe; border-radius: 4px; padding: 2px 6px; font-size: 11px; font-weight: 600;")
            btn_details.clicked.connect(lambda _, p_data=p: self._open_purchase_detail(p_data))
            act_l.addWidget(btn_details)

            if not is_returned:
                btn_ret = QPushButton("↩️ Return")
                btn_ret.setToolTip("Process a FULL return of this purchase order and deduct stock")
                btn_ret.setStyleSheet("background-color: #fee2e2; color: #991b1b; border: 1px solid #fecaca; border-radius: 4px; padding: 2px 6px; font-size: 11px; font-weight: 600;")
                btn_ret.clicked.connect(lambda _, p_data=p: self._open_purchase_return(p_data))
                act_l.addWidget(btn_ret)

            self.table.setCellWidget(row_idx, 7, act_w)
            self.table.setRowHeight(row_idx, 38)

    def _apply_return_filters(self) -> None:
        query = self.txt_ret_search.text().strip()
        supplier_id = self.cmb_ret_supplier_filter.currentData()
        start_date = self.date_ret_start.date().toString("yyyy-MM-dd")
        end_date = self.date_ret_end.date().toString("yyyy-MM-dd")

        returns = self.partner_service.get_all_purchase_returns(
            query=query,
            supplier_id=supplier_id if supplier_id and supplier_id > 0 else None,
            start_date=start_date,
            end_date=end_date,
            limit=300,
        )

        self.current_returns = returns
        self._populate_returns_table(returns)

        # Update KPIs
        total_ret = len(returns)
        total_units = sum(r.get("total_units_returned", 0) for r in returns)
        self.card_ret_count.lbl_val.setText(str(total_ret))
        self.card_ret_units.lbl_val.setText(f"-{total_units} units")
        self.lbl_returns_count.setText(f"Showing {total_ret} purchase return(s)")

    def _populate_returns_table(self, returns: List[Dict[str, Any]]) -> None:
        self.table_returns.setRowCount(len(returns))

        for row_idx, r in enumerate(returns):
            # 0. Return #
            r_item = QTableWidgetItem(r["return_number"])
            r_item.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
            r_item.setForeground(QColor("#991b1b"))
            self.table_returns.setItem(row_idx, 0, r_item)

            # 1. Invoice #
            self.table_returns.setItem(row_idx, 1, QTableWidgetItem(r.get("invoice_number") or "—"))

            # 2. Supplier
            self.table_returns.setItem(row_idx, 2, QTableWidgetItem(r.get("supplier_name") or "—"))

            # 3. Date
            raw_date = r.get("return_date", "")
            date_str = str(raw_date)[:16].replace("T", " ") if raw_date else "—"
            c_date = QTableWidgetItem(date_str)
            c_date.setForeground(QColor("#475569"))
            self.table_returns.setItem(row_idx, 3, c_date)

            # 4. Returned Items Summary
            summary_txt = r.get("items_summary") or "No items listed"
            c_summary = QTableWidgetItem(summary_txt)
            c_summary.setToolTip(summary_txt)
            self.table_returns.setItem(row_idx, 4, c_summary)

            # 5. Units Deducted
            units_val = r.get("total_units_returned", 0)
            c_units = QTableWidgetItem(f"-{units_val} pcs")
            c_units.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            c_units.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
            c_units.setForeground(QColor("#dc2626"))
            self.table_returns.setItem(row_idx, 5, c_units)

            # 6. Processed By
            self.table_returns.setItem(row_idx, 6, QTableWidgetItem(r.get("processed_by") or "System"))

            # 7. Actions (Details)
            btn_details = QPushButton("🔍 Details")
            btn_details.setStyleSheet("background-color: #fef2f2; color: #991b1b; border: 1px solid #fecaca; border-radius: 4px; padding: 2px 6px; font-size: 11px; font-weight: 600;")
            btn_details.clicked.connect(lambda _, r_data=r: self._open_return_detail(r_data))
            self.table_returns.setCellWidget(row_idx, 7, btn_details)

            self.table_returns.setRowHeight(row_idx, 38)

    # -------------------------------------------------------------------------
    # ACTION HANDLERS
    # -------------------------------------------------------------------------

    def _on_purchase_double_clicked(self, row: int, col: int) -> None:
        if 0 <= row < len(getattr(self, "current_purchases", [])):
            p = self.current_purchases[row]
            self._open_purchase_detail(p)

    def _on_return_double_clicked(self, row: int, col: int) -> None:
        if 0 <= row < len(getattr(self, "current_returns", [])):
            r = self.current_returns[row]
            self._open_return_detail(r)

    def _open_new_purchase(self) -> None:
        if not check_permission("purchases.manage", parent=self, action_name="record purchases"):
            return
        dlg = AddPurchaseDialog(self.product_service, self.partner_service, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.load_all_data()

    def _open_purchase_detail(self, purchase_data: Dict[str, Any]) -> None:
        dlg = PurchaseDetailDialog(purchase_data["id"], partner_service=self.partner_service, parent=self)
        dlg.exec()
        self.load_all_data()

    def _open_purchase_return(self, purchase_data: Dict[str, Any]) -> None:
        if not check_permission("purchases.manage", parent=self, action_name="process purchase returns"):
            return
        dlg = PurchaseReturnDialog(purchase_data["id"], partner_service=self.partner_service, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.load_all_data()

    def _open_return_detail(self, return_data: Dict[str, Any]) -> None:
        dlg = PurchaseReturnDetailDialog(return_data["id"], partner_service=self.partner_service, parent=self)
        dlg.exec()

