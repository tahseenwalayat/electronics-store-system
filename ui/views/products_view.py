"""
Products and Inventory Catalog View.
Hosts Live Search Bar, Category & Brand Filters, Stock KPI Metrics, and Full Product Management Table.
Fields: Product Name, Brand, Model, Category, Minimum Stock Level, Warranty Duration (months), Current Stock (read-only).
Excludes: SKU, barcode, product code, default purchase/sale price fields.
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
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QFrame,
    QMessageBox,
    QDialog,
)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QFont, QColor

from business.product_service import ProductService
from business.partner_service import PartnerService
from business.permissions import can_manage, can_delete, check_permission
from ui.dialogs.add_product_dialog import AddProductDialog
from ui.dialogs.product_detail_dialog import ProductDetailDialog
from ui.dialogs.category_dialog import CategoryManagementDialog
from ui.dialogs.brand_dialog import BrandManagementDialog
from ui.dialogs.excel_import_dialog import ExcelProductImportDialog


class ProductsCatalogView(QWidget):
    """
    Main Product Management and Search View.
    """

    request_navigation = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.product_service = ProductService()
        self.partner_service = PartnerService()

        # Debounce timer for live search
        self.search_timer = QTimer(self)
        self.search_timer.setSingleShot(True)
        self.search_timer.setInterval(120)
        self.search_timer.timeout.connect(self._execute_search)

        self._setup_styles()
        self._setup_ui()
        self.load_data()

    def _setup_styles(self) -> None:
        self.setStyleSheet("""
            QWidget {
                font-family: 'Segoe UI', sans-serif;
            }
            QFrame#searchContainer {
                background-color: #ffffff;
                border: 2px solid #3b82f6;
                border-radius: 10px;
                padding: 4px 10px;
            }
            QLineEdit#largeSearchBar {
                border: none;
                font-size: 15px;
                color: #0f172a;
                background: transparent;
                padding: 6px 4px;
            }
            QLineEdit#largeSearchBar:focus {
                outline: none;
            }
            QPushButton#clearSearchBtn {
                background: transparent;
                border: none;
                color: #94a3b8;
                font-size: 14px;
                font-weight: bold;
                padding: 4px 8px;
            }
            QPushButton#clearSearchBtn:hover {
                color: #ef4444;
            }
            QPushButton#primaryActionBtn {
                background-color: #2563eb;
                color: #ffffff;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-size: 13px;
                font-weight: 600;
            }
            QPushButton#primaryActionBtn:hover {
                background-color: #1d4ed8;
            }
            QPushButton#quickActionBtn {
                background-color: #ffffff;
                color: #1e293b;
                border: 1px solid #cbd5e1;
                border-radius: 6px;
                padding: 8px 14px;
                font-size: 13px;
                font-weight: 600;
            }
            QPushButton#quickActionBtn:hover {
                background-color: #f1f5f9;
                border-color: #94a3b8;
            }
            QFrame#kpiCard {
                background-color: #ffffff;
                border: 1px solid #e2e8f0;
                border-radius: 8px;
                padding: 10px 14px;
            }
            QTableWidget {
                background-color: #ffffff;
                border: 1px solid #e2e8f0;
                border-radius: 8px;
                gridline-color: #f1f5f9;
                selection-background-color: #eff6ff;
                selection-color: #1e3a8a;
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

    def _setup_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 20, 24, 20)
        main_layout.setSpacing(14)

        # ---------------------------------------------------------------------
        # 1. TOP MANDATORY LARGE PRODUCT SEARCH BAR
        # ---------------------------------------------------------------------
        search_frame = QFrame()
        search_frame.setObjectName("searchContainer")
        search_layout = QHBoxLayout(search_frame)
        search_layout.setContentsMargins(8, 2, 8, 2)
        search_layout.setSpacing(8)

        lbl_search_icon = QLabel("🔍")
        lbl_search_icon.setFont(QFont("Segoe UI", 14))
        search_layout.addWidget(lbl_search_icon)

        self.txt_search = QLineEdit()
        self.txt_search.setObjectName("largeSearchBar")
        self.txt_search.setPlaceholderText(
            "Search products live by Product Name, Brand, Model, or Category (e.g. 'Samsung', 'S24', 'MacBook')..."
        )
        self.txt_search.textChanged.connect(self._on_search_text_changed)
        search_layout.addWidget(self.txt_search, stretch=1)

        self.btn_clear_search = QPushButton("✕")
        self.btn_clear_search.setObjectName("clearSearchBtn")
        self.btn_clear_search.setToolTip("Clear search query")
        self.btn_clear_search.clicked.connect(self._clear_search)
        self.btn_clear_search.setVisible(False)
        search_layout.addWidget(self.btn_clear_search)

        main_layout.addWidget(search_frame)

        # ---------------------------------------------------------------------
        # 2. QUICK ACTIONS & FILTER TOOLBAR
        # ---------------------------------------------------------------------
        actions_bar = QHBoxLayout()
        actions_bar.setSpacing(10)

        # Add Product Button (Primary)
        self.btn_add_product = QPushButton("➕ Add Product")
        self.btn_add_product.setObjectName("primaryActionBtn")
        self.btn_add_product.setToolTip("Register a new product in the store catalog")
        self.btn_add_product.clicked.connect(self.open_add_product_dialog)
        actions_bar.addWidget(self.btn_add_product)

        # Import Excel Button
        self.btn_import_excel = QPushButton("📥 Import Excel")
        self.btn_import_excel.setObjectName("quickActionBtn")
        self.btn_import_excel.setToolTip("Bulk import products from Excel spreadsheet (.xlsx)")
        self.btn_import_excel.clicked.connect(self.open_excel_import_dialog)
        actions_bar.addWidget(self.btn_import_excel)

        # Category Management
        self.btn_categories = QPushButton("🏷️ Categories")
        self.btn_categories.setObjectName("quickActionBtn")
        self.btn_categories.setToolTip("Manage product categories and classifications")
        self.btn_categories.clicked.connect(self.open_category_management)
        actions_bar.addWidget(self.btn_categories)

        # Brand Management
        self.btn_brands = QPushButton("🏢 Brands")
        self.btn_brands.setObjectName("quickActionBtn")
        self.btn_brands.setToolTip("Manage hardware manufacturers and brand profiles")
        self.btn_brands.clicked.connect(self.open_brand_management)
        actions_bar.addWidget(self.btn_brands)

        actions_bar.addStretch()

        # Category Filter Dropdown
        actions_bar.addWidget(QLabel("Category:"))
        self.cmb_category_filter = QComboBox()
        self.cmb_category_filter.addItem("All Categories", 0)
        self.cmb_category_filter.currentIndexChanged.connect(self._on_filter_changed)
        self.cmb_category_filter.setFixedHeight(34)
        actions_bar.addWidget(self.cmb_category_filter)

        # Brand Filter Dropdown
        actions_bar.addWidget(QLabel("Brand:"))
        self.cmb_brand_filter = QComboBox()
        self.cmb_brand_filter.addItem("All Brands", 0)
        self.cmb_brand_filter.currentIndexChanged.connect(self._on_filter_changed)
        self.cmb_brand_filter.setFixedHeight(34)
        actions_bar.addWidget(self.cmb_brand_filter)

        # Stock Status Filter Dropdown
        actions_bar.addWidget(QLabel("Stock:"))
        self.cmb_stock_filter = QComboBox()
        self.cmb_stock_filter.addItem("All Stock", "all")
        self.cmb_stock_filter.addItem("🟢 In Stock", "in_stock")
        self.cmb_stock_filter.addItem("🟡 Low Stock (<= Min)", "low_stock")
        self.cmb_stock_filter.addItem("🔴 Out of Stock", "out_of_stock")
        self.cmb_stock_filter.currentIndexChanged.connect(self._on_filter_changed)
        self.cmb_stock_filter.setFixedHeight(34)
        actions_bar.addWidget(self.cmb_stock_filter)

        # Refresh
        self.btn_refresh = QPushButton("↻ Refresh")
        self.btn_refresh.setFixedHeight(34)
        self.btn_refresh.clicked.connect(self.load_data)
        actions_bar.addWidget(self.btn_refresh)

        main_layout.addLayout(actions_bar)

        # ---------------------------------------------------------------------
        # 3. KPI METRIC SUMMARY CHIPS
        # ---------------------------------------------------------------------
        kpi_bar = QHBoxLayout()
        kpi_bar.setSpacing(12)

        # Total Products Chip
        card_total = QFrame()
        card_total.setObjectName("kpiCard")
        c_tot_lay = QHBoxLayout(card_total)
        c_tot_lay.setContentsMargins(10, 6, 10, 6)
        self.lbl_kpi_total = QLabel("📦 <b>0</b> Products")
        self.lbl_kpi_total.setStyleSheet("color: #0f172a; font-size: 12px;")
        c_tot_lay.addWidget(self.lbl_kpi_total)
        kpi_bar.addWidget(card_total)

        # In Stock Units Chip
        card_units = QFrame()
        card_units.setObjectName("kpiCard")
        c_unt_lay = QHBoxLayout(card_units)
        c_unt_lay.setContentsMargins(10, 6, 10, 6)
        self.lbl_kpi_units = QLabel("📊 <b>0</b> Units In Stock")
        self.lbl_kpi_units.setStyleSheet("color: #0284c7; font-size: 12px;")
        c_unt_lay.addWidget(self.lbl_kpi_units)
        kpi_bar.addWidget(card_units)

        # Low Stock Chip
        card_low = QFrame()
        card_low.setObjectName("kpiCard")
        c_low_lay = QHBoxLayout(card_low)
        c_low_lay.setContentsMargins(10, 6, 10, 6)
        self.lbl_kpi_low = QLabel("⚠️ <b>0</b> Low Stock")
        self.lbl_kpi_low.setStyleSheet("color: #d97706; font-size: 12px;")
        c_low_lay.addWidget(self.lbl_kpi_low)
        kpi_bar.addWidget(card_low)

        # Out of Stock Chip
        card_out = QFrame()
        card_out.setObjectName("kpiCard")
        c_out_lay = QHBoxLayout(card_out)
        c_out_lay.setContentsMargins(10, 6, 10, 6)
        self.lbl_kpi_out = QLabel("❌ <b>0</b> Out of Stock")
        self.lbl_kpi_out.setStyleSheet("color: #dc2626; font-size: 12px;")
        c_out_lay.addWidget(self.lbl_kpi_out)
        kpi_bar.addWidget(card_out)

        kpi_bar.addStretch()

        # Result Counter Label
        self.lbl_result_count = QLabel("Showing 0 products")
        self.lbl_result_count.setStyleSheet("color: #64748b; font-size: 12px; font-weight: 500;")
        kpi_bar.addWidget(self.lbl_result_count)

        main_layout.addLayout(kpi_bar)

        # ---------------------------------------------------------------------
        # 4. PRODUCT LIST TABLE (Fields: Name, Brand, Model, Category, Current Stock, Min Stock, Warranty, Status, Actions)
        # ---------------------------------------------------------------------
        self.table = QTableWidget()
        self.table.setColumnCount(9)
        self.table.setHorizontalHeaderLabels([
            "Product Name", "Brand", "Model", "Category", "Current Stock", "Min Stock", "Warranty", "Stock Status", "Actions"
        ])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(7, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(8, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(8, 140)

        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.cellDoubleClicked.connect(self._on_table_double_clicked)

        main_layout.addWidget(self.table, stretch=1)

    # -------------------------------------------------------------------------
    # DATA LOADING & LIVE SEARCH
    # -------------------------------------------------------------------------

    def load_data(self) -> None:
        """Fetch categories/brands and trigger search execution."""
        self._load_filter_dropdowns()
        self._execute_search()
        self._update_kpi_metrics()

    def focus_search_bar(self) -> None:
        """Focus and select all text in the search input."""
        self.txt_search.setFocus()
        self.txt_search.selectAll()

    def _load_filter_dropdowns(self) -> None:
        """Refresh category and brand filter options."""
        # Category dropdown
        current_cat = self.cmb_category_filter.currentData()
        self.cmb_category_filter.blockSignals(True)
        self.cmb_category_filter.clear()
        self.cmb_category_filter.addItem("All Categories", 0)
        categories = self.product_service.get_all_categories()
        for cat in categories:
            self.cmb_category_filter.addItem(cat["name"], cat["id"])
        idx_c = self.cmb_category_filter.findData(current_cat)
        if idx_c >= 0:
            self.cmb_category_filter.setCurrentIndex(idx_c)
        self.cmb_category_filter.blockSignals(False)

        # Brand dropdown
        current_b = self.cmb_brand_filter.currentData()
        self.cmb_brand_filter.blockSignals(True)
        self.cmb_brand_filter.clear()
        self.cmb_brand_filter.addItem("All Brands", 0)
        brands = self.product_service.get_all_brands()
        for b in brands:
            self.cmb_brand_filter.addItem(b["name"], b["id"])
        idx_b = self.cmb_brand_filter.findData(current_b)
        if idx_b >= 0:
            self.cmb_brand_filter.setCurrentIndex(idx_b)
        self.cmb_brand_filter.blockSignals(False)

    def _update_kpi_metrics(self) -> None:
        """Fetch inventory metrics and update chips."""
        metrics = self.product_service.get_inventory_metrics()
        self.lbl_kpi_total.setText(f"📦 <b>{metrics['total_count']}</b> Products")
        self.lbl_kpi_units.setText(f"📊 <b>{metrics['total_units']}</b> Units In Stock")
        self.lbl_kpi_low.setText(f"⚠️ <b>{metrics['low_stock_count']}</b> Low Stock")
        self.lbl_kpi_out.setText(f"❌ <b>{metrics['out_of_stock_count']}</b> Out of Stock")

    def _on_search_text_changed(self, text: str) -> None:
        """Handle live text input with debounce."""
        self.btn_clear_search.setVisible(bool(text.strip()))
        self.search_timer.start()

    def _clear_search(self) -> None:
        """Clear search query."""
        self.txt_search.clear()
        self.txt_search.setFocus()

    def _on_filter_changed(self) -> None:
        """Handle category, brand, or stock filter changes."""
        self._execute_search()

    def _execute_search(self) -> None:
        """Execute database query and populate results table."""
        query = self.txt_search.text().strip()
        cat_id = self.cmb_category_filter.currentData()
        brand_id = self.cmb_brand_filter.currentData()
        stock_filter = self.cmb_stock_filter.currentData()

        products = self.product_service.search_products(
            query=query,
            category_id=cat_id if cat_id and cat_id > 0 else None,
            brand_id=brand_id if brand_id and brand_id > 0 else None,
            stock_status=stock_filter if stock_filter != "all" else None,
            limit=300,
        )

        self._populate_table(products)

        # Update count label
        total_msg = f"Showing {len(products)} products"
        if query:
            total_msg += f" matching '<b>{query}</b>'"
        self.lbl_result_count.setText(total_msg)

    def _populate_table(self, products: List[Dict[str, Any]]) -> None:
        """Render product rows into table with visual low stock indicators."""
        self.table.setRowCount(len(products))
        self.current_products = products

        can_edit_prod = can_manage("products")
        can_del_prod = can_delete("products")

        for row_idx, p in enumerate(products):
            # 0: Product Name
            name_item = QTableWidgetItem(p["name"])
            name_item.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
            self.table.setItem(row_idx, 0, name_item)

            # 1: Brand
            brand_item = QTableWidgetItem(p.get("brand_name", "—"))
            self.table.setItem(row_idx, 1, brand_item)

            # 2: Model
            model_item = QTableWidgetItem(p.get("model", "—"))
            model_item.setForeground(QColor("#475569"))
            self.table.setItem(row_idx, 2, model_item)

            # 3: Category
            cat_item = QTableWidgetItem(p.get("category_name", "General"))
            self.table.setItem(row_idx, 3, cat_item)

            # 4: Current Stock
            stock_val = p["current_stock"]
            min_alert = p["min_stock_alert"]
            stock_item = QTableWidgetItem(f"{stock_val} units")
            stock_item.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
            stock_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.table.setItem(row_idx, 4, stock_item)

            # 5: Min Stock Level
            min_item = QTableWidgetItem(f"{min_alert} units")
            min_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            min_item.setForeground(QColor("#64748b"))
            self.table.setItem(row_idx, 5, min_item)

            # 6: Warranty
            w_months = p.get("warranty_period_months", 0)
            w_text = f"{w_months} mos" if w_months > 0 else "None"
            w_item = QTableWidgetItem(w_text)
            w_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            w_item.setForeground(QColor("#64748b"))
            self.table.setItem(row_idx, 6, w_item)

            # 7: Visual Stock Status Indicator (Low stock indicator when current_stock <= min_stock)
            if stock_val <= 0:
                status_text = "🔴 Out of Stock"
                status_color = QColor("#b91c1c")
            elif stock_val <= min_alert:
                status_text = f"🟡 ⚠️ Low Stock ({stock_val}/{min_alert})"
                status_color = QColor("#b45309")
            else:
                status_text = "🟢 In Stock"
                status_color = QColor("#15803d")

            stat_item = QTableWidgetItem(status_text)
            stat_item.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
            stat_item.setForeground(status_color)
            stat_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row_idx, 7, stat_item)

            # 8: Actions Cell (Edit / Delete)
            action_widget = QWidget()
            action_layout = QHBoxLayout(action_widget)
            action_layout.setContentsMargins(4, 2, 4, 2)
            action_layout.setSpacing(6)

            # Edit button
            btn_edit = QPushButton("Edit")
            btn_edit.setStyleSheet("background-color: #eff6ff; color: #1d4ed8; border: 1px solid #bfdbfe; border-radius: 4px; padding: 3px 8px; font-size: 11px; font-weight: 600;")
            btn_edit.setEnabled(can_edit_prod)
            btn_edit.clicked.connect(lambda _, p_data=p: self._on_edit_clicked(p_data))
            action_layout.addWidget(btn_edit)

            # Delete button (Soft Delete)
            btn_del = QPushButton("Delete")
            btn_del.setStyleSheet("background-color: #fef2f2; color: #dc2626; border: 1px solid #fecaca; border-radius: 4px; padding: 3px 8px; font-size: 11px; font-weight: 600;")
            btn_del.setEnabled(can_edit_prod)
            btn_del.clicked.connect(lambda _, p_data=p: self._on_delete_clicked(p_data))
            action_layout.addWidget(btn_del)

            self.table.setCellWidget(row_idx, 8, action_widget)
            self.table.setRowHeight(row_idx, 38)

    def _on_table_double_clicked(self, row: int, col: int) -> None:
        """Open product details on double click."""
        if 0 <= row < len(getattr(self, "current_products", [])):
            p = self.current_products[row]
            dlg = ProductDetailDialog(p, parent=self)
            dlg.exec()

    def _on_edit_clicked(self, product: Dict[str, Any]) -> None:
        """Open edit modal for product."""
        if not check_permission("products.manage", parent=self, action_name="edit product"):
            return
        dlg = AddProductDialog(self.product_service, product_data=product, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.load_data()

    def _on_delete_clicked(self, product: Dict[str, Any]) -> None:
        """
        Soft delete product with confirmation.
        Historical sales and purchases referencing this product remain intact.
        """
        if not check_permission("products.manage", parent=self, action_name="delete product"):
            return

        prod_id = product["id"]
        prod_name = product["name"]

        reply = QMessageBox.question(
            self,
            "Confirm Product Deletion",
            f"Are you sure you want to delete product '<b>{prod_name}</b>'?\n\n"
            "• The product will be removed from the active catalog.\n"
            "• Historical purchase orders and sales invoices referencing this product will remain fully intact.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        success, msg = self.product_service.delete_product(prod_id)
        if not success:
            QMessageBox.critical(self, "Error Deleting Product", msg)
            return

        QMessageBox.information(self, "Product Deleted", msg)
        self.load_data()

    # -------------------------------------------------------------------------
    # QUICK ACTION HANDLERS
    # -------------------------------------------------------------------------

    def open_add_product_dialog(self) -> None:
        """Open Add Product dialog."""
        if not check_permission("products.manage", parent=self, action_name="create products"):
            return
        dlg = AddProductDialog(self.product_service, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.load_data()

    def open_category_management(self) -> None:
        """Open Category Management dialog."""
        if not check_permission("products.view", parent=self, action_name="view categories"):
            return
        dlg = CategoryManagementDialog(self.product_service, parent=self)
        dlg.categories_changed.connect(self.load_data)
        dlg.exec()
        self.load_data()

    def open_brand_management(self) -> None:
        """Open Brand Management dialog."""
        if not check_permission("products.view", parent=self, action_name="view brands"):
            return
        dlg = BrandManagementDialog(self.product_service, parent=self)
        dlg.brands_changed.connect(self.load_data)
        dlg.exec()
        self.load_data()

    def open_excel_import_dialog(self) -> None:
        """Open Excel Product Import dialog."""
        if not check_permission("products.manage", parent=self, action_name="import products"):
            return
        dlg = ExcelProductImportDialog(parent=self)
        dlg.import_completed.connect(lambda _: self.load_data())
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.load_data()

