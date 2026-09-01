"""
Main Window for the Electronics Store System.
Hosts application navigation sidebar, live product search, module views, and permission-aware access.
"""

from typing import Dict, Optional, Tuple, List
from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QStatusBar,
    QMenuBar,
    QMenu,
    QMessageBox,
    QPushButton,
    QFrame,
    QStackedWidget,
    QScrollArea,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QAction, QFont, QIcon, QKeySequence, QShortcut

from business.session import get_session
from business.permissions import can_view, check_permission
from ui.views.products_view import ProductsCatalogView
from ui.views.sales_view import SalesView
from ui.views.purchases_view import PurchasesView
from ui.views.customers_view import CustomersView
from ui.views.suppliers_view import SuppliersView
from ui.views.returns_view import ReturnsView
from ui.views.warranty_view import WarrantyView
from ui.views.reports_view import ReportsView
from ui.views.backup_view import BackupRestoreView
from ui.views.settings_view import SettingsView
from ui.users_view import UsersManagementWidget
from ui.dialogs.category_dialog import CategoryManagementDialog
from ui.dialogs.brand_dialog import BrandManagementDialog
from ui.dialogs.excel_import_dialog import ExcelProductImportDialog


class MainWindow(QMainWindow):
    """
    Main Application Window with live product search and permission-aware sidebar navigation.
    """

    logout_requested = Signal()

    def __init__(self, db_manager=None, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.session = get_session()

        self.setWindowTitle("Electronics Store System")
        self.resize(1240, 800)
        self.setMinimumSize(1000, 640)

        self.nav_buttons: Dict[str, QPushButton] = {}
        self.view_map: Dict[str, QWidget] = {}
        self.current_key: Optional[str] = None

        self._setup_styles()
        self._setup_menus()
        self._setup_ui()
        self._setup_shortcuts()
        self._setup_status_bar()

    def _setup_styles(self) -> None:
        """Apply modern, clutter-free application styles."""
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f8fafc;
                font-family: 'Segoe UI', sans-serif;
            }
            QFrame#sidebar {
                background-color: #0f172a;
                border-right: 1px solid #1e293b;
            }
            QLabel#sidebarTitle {
                color: #ffffff;
                font-size: 15px;
                font-weight: 700;
                padding: 16px 14px 6px 14px;
            }
            QLabel#userBadge {
                background-color: #1e293b;
                color: #e2e8f0;
                font-size: 12px;
                padding: 10px 12px;
                border-radius: 8px;
                margin: 4px 10px 12px 10px;
                border: 1px solid #334155;
            }
            QPushButton.navBtn {
                background-color: transparent;
                color: #94a3b8;
                border: none;
                border-radius: 6px;
                text-align: left;
                padding: 9px 14px;
                font-size: 13px;
                font-weight: 500;
                margin: 2px 10px;
            }
            QPushButton.navBtn:hover {
                background-color: #1e293b;
                color: #f8fafc;
            }
            QPushButton.navBtn:checked {
                background-color: #2563eb;
                color: #ffffff;
                font-weight: 600;
            }
            QPushButton#sidebarLogout {
                background-color: #1e293b;
                color: #f87171;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 9px 14px;
                font-size: 13px;
                font-weight: 600;
                margin: 10px 10px 14px 10px;
            }
            QPushButton#sidebarLogout:hover {
                background-color: #7f1d1d;
                color: #ffffff;
                border-color: #991b1b;
            }
            QFrame#contentArea {
                background-color: #f8fafc;
            }
            QStatusBar {
                background-color: #ffffff;
                border-top: 1px solid #e2e8f0;
                color: #64748b;
                font-size: 12px;
                padding: 3px 10px;
            }
        """)

    def _setup_menus(self) -> None:
        """Set up standard application menu bar."""
        menubar = self.menuBar()

        # File Menu
        file_menu = menubar.addMenu("&File")

        search_action = QAction("🔍 &Find Product", self)
        search_action.setShortcut(QKeySequence.Find)
        search_action.triggered.connect(self._focus_product_search)
        file_menu.addAction(search_action)

        new_sale_action = QAction("🛒 &New Sale (POS)", self)
        new_sale_action.setShortcut(QKeySequence.New)
        new_sale_action.triggered.connect(self._trigger_new_sale)
        file_menu.addAction(new_sale_action)

        file_menu.addSeparator()

        logout_action = QAction("Sign &Out", self)
        logout_action.setStatusTip("Log out of current user session")
        logout_action.triggered.connect(self._handle_logout)
        file_menu.addAction(logout_action)

        file_menu.addSeparator()

        exit_action = QAction("E&xit", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.setStatusTip("Exit application")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # View Menu
        view_menu = menubar.addMenu("&View")
        refresh_action = QAction("↻ &Refresh Current View", self)
        refresh_action.setShortcut(QKeySequence.Refresh)
        refresh_action.triggered.connect(self._refresh_current_view)
        view_menu.addAction(refresh_action)

        # Manage Menu
        manage_menu = menubar.addMenu("&Manage")

        cat_action = QAction("🏷️ &Manage Categories...", self)
        cat_action.setStatusTip("Open Category Management list and editor")
        cat_action.triggered.connect(self.open_category_management)
        manage_menu.addAction(cat_action)

        brand_action = QAction("🏢 &Manage Brands...", self)
        brand_action.setStatusTip("Open Brand Management list and editor")
        brand_action.triggered.connect(self.open_brand_management)
        manage_menu.addAction(brand_action)

        manage_menu.addSeparator()

        import_action = QAction("📥 &Import Products from Excel...", self)
        import_action.setStatusTip("Bulk import product catalog from an Excel (.xlsx) file")
        import_action.triggered.connect(self.open_excel_import)
        manage_menu.addAction(import_action)

        # Help Menu
        help_menu = menubar.addMenu("&Help")
        about_action = QAction("&About", self)
        about_action.setStatusTip("About Electronics Store System")
        about_action.triggered.connect(self._show_about_dialog)
        help_menu.addAction(about_action)

    def _setup_shortcuts(self) -> None:
        """Setup global keyboard shortcuts."""
        # Ctrl+F to focus search
        self.shortcut_search = QShortcut(QKeySequence("Ctrl+F"), self)
        self.shortcut_search.activated.connect(self._focus_product_search)

        # / key to focus search (when not already focused in an input)
        self.shortcut_slash = QShortcut(QKeySequence("/"), self)
        self.shortcut_slash.activated.connect(self._focus_product_search)

    def _setup_ui(self) -> None:
        """Set up main window structure with sidebar and stacked views."""
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)

        root_layout = QHBoxLayout(central_widget)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # ---------------------------------------------------------------------
        # 1. LEFT NAVIGATION SIDEBAR
        # ---------------------------------------------------------------------
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(230)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        sidebar_layout.setSpacing(2)

        # Sidebar Header / Branding
        lbl_app = QLabel("⚡ Electronics Store")
        lbl_app.setObjectName("sidebarTitle")
        sidebar_layout.addWidget(lbl_app)

        # User Profile Badge in Sidebar
        self.lbl_user_badge = QLabel()
        self.lbl_user_badge.setObjectName("userBadge")
        self.lbl_user_badge.setWordWrap(True)
        sidebar_layout.addWidget(self.lbl_user_badge)

        # Sidebar Scroll Container for navigation items
        scroll_nav = QScrollArea()
        scroll_nav.setWidgetResizable(True)
        scroll_nav.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        scroll_nav.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        nav_container = QWidget()
        nav_container_layout = QVBoxLayout(nav_container)
        nav_container_layout.setContentsMargins(0, 0, 0, 0)
        nav_container_layout.setSpacing(2)

        # Navigation Items (Matching exact required listing)
        self.nav_items: List[Tuple[str, str, str]] = [
            ("products", "📦 Products", "products"),
            ("sales", "🛒 Sales", "sales"),
            ("purchases", "🚚 Purchases", "purchases"),
            ("customers", "👤 Customers", "customers"),
            ("suppliers", "🏭 Suppliers", "suppliers"),
            ("returns", "🔄 Returns", "returns"),
            ("warranty", "🛡️ Warranty", "warranty"),
            ("reports", "📈 Reports", "reports"),
            ("users", "👥 Users & Permissions", "users"),
            ("backup_restore", "💾 Backup & Restore", "backup_restore"),
            ("settings", "⚙️ Settings", "settings"),
        ]

        self.nav_buttons.clear()
        for key, label_text, req_module in self.nav_items:
            btn = QPushButton(label_text)
            btn.setProperty("class", "navBtn")
            btn.setCheckable(True)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda _, k=key: self._on_nav_clicked(k))
            nav_container_layout.addWidget(btn)
            self.nav_buttons[key] = btn

        nav_container_layout.addStretch()
        scroll_nav.setWidget(nav_container)
        sidebar_layout.addWidget(scroll_nav, stretch=1)

        # Sign Out button at bottom of sidebar
        btn_sidebar_logout = QPushButton("🚪 Sign Out")
        btn_sidebar_logout.setObjectName("sidebarLogout")
        btn_sidebar_logout.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_sidebar_logout.clicked.connect(self._handle_logout)
        sidebar_layout.addWidget(btn_sidebar_logout)

        root_layout.addWidget(sidebar)

        # ---------------------------------------------------------------------
        # 2. MAIN CONTENT STACK
        # ---------------------------------------------------------------------
        self.content_stack = QStackedWidget()
        self.content_stack.setObjectName("contentArea")

        # View 0: Products & Live Search (Main Screen)
        self.page_products = ProductsCatalogView(parent=self)
        self.content_stack.addWidget(self.page_products)
        self.view_map["products"] = self.page_products

        # View 1: Sales & POS
        self.page_sales = SalesView(parent=self)
        self.content_stack.addWidget(self.page_sales)
        self.view_map["sales"] = self.page_sales

        # View 2: Purchases
        self.page_purchases = PurchasesView(parent=self)
        self.content_stack.addWidget(self.page_purchases)
        self.view_map["purchases"] = self.page_purchases

        # View 3: Customers
        self.page_customers = CustomersView(parent=self)
        self.content_stack.addWidget(self.page_customers)
        self.view_map["customers"] = self.page_customers

        # View 4: Suppliers
        self.page_suppliers = SuppliersView(parent=self)
        self.content_stack.addWidget(self.page_suppliers)
        self.view_map["suppliers"] = self.page_suppliers

        # View 5: Returns
        self.page_returns = ReturnsView(parent=self)
        self.content_stack.addWidget(self.page_returns)
        self.view_map["returns"] = self.page_returns

        # View 6: Warranty
        self.page_warranty = WarrantyView(parent=self)
        self.content_stack.addWidget(self.page_warranty)
        self.view_map["warranty"] = self.page_warranty

        # View 7: Reports
        self.page_reports = ReportsView(parent=self)
        self.content_stack.addWidget(self.page_reports)
        self.view_map["reports"] = self.page_reports

        # View 8: Users & Permissions
        self.page_users = UsersManagementWidget(parent=self)
        self.content_stack.addWidget(self.page_users)
        self.view_map["users"] = self.page_users

        # View 9: Backup & Restore
        self.page_backup = BackupRestoreView(parent=self)
        self.content_stack.addWidget(self.page_backup)
        self.view_map["backup_restore"] = self.page_backup

        # View 10: Settings
        self.page_settings = SettingsView(parent=self)
        self.content_stack.addWidget(self.page_settings)
        self.view_map["settings"] = self.page_settings

        root_layout.addWidget(self.content_stack, stretch=1)

        self._refresh_nav_state()

    def _on_nav_clicked(self, key: str) -> None:
        """Handle sidebar navigation button clicks with permission enforcement."""
        req_module = next((item[2] for item in self.nav_items if item[0] == key), key)

        if not check_permission(f"{req_module}.view", parent=self, action_name=f"access {key.title()}"):
            self._update_nav_selection()
            return

        self._switch_to_view(key)

    def _switch_to_view(self, key: str) -> None:
        """Switch active widget and refresh its dataset."""
        if key not in self.view_map:
            return

        target_widget = self.view_map[key]
        self.content_stack.setCurrentWidget(target_widget)
        self.current_key = key

        # Update button checked states
        for k, btn in self.nav_buttons.items():
            btn.setChecked(k == key)

        # Trigger data reload for the activated view
        if key == "products":
            self.page_products.load_data()
        elif key == "sales":
            self.page_sales.load_sales()
        elif key == "purchases":
            self.page_purchases.load_purchases()
        elif key == "customers":
            self.page_customers.load_customers()
        elif key == "suppliers":
            self.page_suppliers.load_suppliers()
        elif key == "returns":
            self.page_returns.load_returns()
        elif key == "warranty":
            self.page_warranty.load_claims()
        elif key == "reports":
            self.page_reports.load_analytics()
        elif key == "users":
            self.page_users.load_users()
        elif key == "backup_restore":
            self.page_backup.load_backups()
        elif key == "settings":
            self.page_settings.load_settings()

    def _update_nav_selection(self) -> None:
        """Keep active button state consistent with visible page."""
        current_w = self.content_stack.currentWidget()
        for k, w in self.view_map.items():
            if w == current_w and k in self.nav_buttons:
                self.nav_buttons[k].setChecked(True)
                self.current_key = k

    def _refresh_nav_state(self) -> None:
        """Update navigation item visibility dynamically based on session user permissions."""
        user = self.session.current_user
        if not user:
            return

        # Update Sidebar User Badge
        role_upper = user.role_name.upper()
        self.lbl_user_badge.setText(
            f"👤 <b>{user.full_name}</b><br>"
            f"<span style='color: #94a3b8;'>@{user.username}</span> &bull; "
            f"<span style='color: #38bdf8; font-weight: bold;'>{role_upper}</span>"
        )

        # Show / Hide nav buttons based on can_view(module)
        first_visible_key = None
        for key, _, req_module in self.nav_items:
            allowed = can_view(req_module)
            btn = self.nav_buttons[key]
            btn.setVisible(allowed)
            if allowed and first_visible_key is None:
                first_visible_key = key

        # Default to "products" if permitted, else the first visible item
        if can_view("products"):
            self._switch_to_view("products")
        elif first_visible_key:
            self._switch_to_view(first_visible_key)

    def _setup_status_bar(self) -> None:
        """Set up status bar."""
        status_bar = QStatusBar(self)
        self.setStatusBar(status_bar)
        self.update_status_bar()

    def update_status_bar(self) -> None:
        """Refresh status bar details."""
        user = self.session.current_user
        user_str = f"{user.full_name} (@{user.username} - {user.role_name.upper()})" if user else "Not logged in"
        db_path = self.db_manager.db_path if self.db_manager else "store.db"
        self.statusBar().showMessage(f"🟢 Database: {db_path} | User: {user_str} | Press Ctrl+F to Search Products")

    def refresh_user_display(self) -> None:
        """Refresh entire view on session update or login."""
        self._refresh_nav_state()
        self.update_status_bar()

    def _focus_product_search(self) -> None:
        """Switch to products view and focus search bar."""
        if can_view("products"):
            self._switch_to_view("products")
            self.page_products.focus_search_bar()

    def _trigger_new_sale(self) -> None:
        """Open new sale dialog directly."""
        if can_view("products"):
            self.page_products.open_new_sale_dialog()
        elif can_view("sales"):
            self.page_sales._open_new_sale()

    def _refresh_current_view(self) -> None:
        """Refresh active page data."""
        if self.current_key:
            self._switch_to_view(self.current_key)

    def _handle_logout(self) -> None:
        """Logout user and notify controller."""
        self.session.logout()
        self.logout_requested.emit()
        self.close()

    def open_category_management(self) -> None:
        """Open Category Management Dialog."""
        if not check_permission("products.view", parent=self, action_name="view categories"):
            return
        dlg = CategoryManagementDialog(self.page_products.product_service, parent=self)
        dlg.categories_changed.connect(self.page_products.load_data)
        dlg.exec()
        self.page_products.load_data()

    def open_brand_management(self) -> None:
        """Open Brand Management Dialog."""
        if not check_permission("products.view", parent=self, action_name="view brands"):
            return
        dlg = BrandManagementDialog(self.page_products.product_service, parent=self)
        dlg.brands_changed.connect(self.page_products.load_data)
        dlg.exec()
        self.page_products.load_data()

    def open_excel_import(self) -> None:
        """Open Excel Product Import Dialog."""
        if not check_permission("products.manage", parent=self, action_name="import products"):
            return
        dlg = ExcelProductImportDialog(parent=self)
        dlg.import_completed.connect(lambda _: self.page_products.load_data())
        dlg.exec()
        self.page_products.load_data()

    def _show_about_dialog(self) -> None:
        """Show About dialog."""
        QMessageBox.about(
            self,
            "About Electronics Store System",
            "<h3>Electronics Store System</h3>"
            "<p>Modern Enterprise Point of Sale & Inventory Management System.</p>"
            "<p><b>Version:</b> 1.0.0</p>"
            "<p>Features live multi-field catalog search, POS invoicing, and modular RBAC permissions.</p>",
        )

