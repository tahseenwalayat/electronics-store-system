"""
Main Window for the Electronics Store System.
Hosts application navigation sidebar, module views, session status, and user management.
"""

from typing import Dict
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
from PySide6.QtGui import QAction, QFont, QIcon

from business.session import get_session
from business.permissions import can_view, check_permission
from ui.users_view import UsersManagementWidget


class MainWindow(QMainWindow):
    """
    Main Application Window with permission-aware sidebar navigation.
    """

    logout_requested = Signal()

    def __init__(self, db_manager=None, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.session = get_session()

        self.setWindowTitle("Electronics Store System")
        self.resize(1180, 760)
        self.setMinimumSize(950, 600)

        self.nav_buttons: Dict[str, QPushButton] = {}
        self._setup_styles()
        self._setup_menus()
        self._setup_ui()
        self._setup_status_bar()

    def _setup_styles(self) -> None:
        """Apply modern application styles."""
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f1f5f9;
                font-family: 'Segoe UI', sans-serif;
            }
            QFrame#sidebar {
                background-color: #0f172a;
                border-right: 1px solid #1e293b;
            }
            QLabel#sidebarTitle {
                color: #ffffff;
                font-size: 16px;
                font-weight: 700;
                padding: 16px 12px 6px 12px;
            }
            QLabel#userBadge {
                background-color: #1e293b;
                color: #e2e8f0;
                font-size: 12px;
                padding: 10px 12px;
                border-radius: 8px;
                margin: 4px 8px 12px 8px;
            }
            QPushButton.navBtn {
                background-color: transparent;
                color: #94a3b8;
                border: none;
                border-radius: 6px;
                text-align: left;
                padding: 10px 14px;
                font-size: 13px;
                font-weight: 500;
                margin: 2px 8px;
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
            QPushButton.navBtn:disabled {
                color: #475569;
            }
            QPushButton#sidebarLogout {
                background-color: #1e293b;
                color: #f87171;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 10px 14px;
                font-size: 13px;
                font-weight: 600;
                margin: 12px 8px 16px 8px;
            }
            QPushButton#sidebarLogout:hover {
                background-color: #7f1d1d;
                color: #ffffff;
            }
            QFrame#contentArea {
                background-color: #f8fafc;
            }
            QStatusBar {
                background-color: #ffffff;
                border-top: 1px solid #e2e8f0;
                color: #64748b;
            }
        """)

    def _setup_menus(self) -> None:
        """Set up standard application menu bar."""
        menubar = self.menuBar()

        # File Menu
        file_menu = menubar.addMenu("&File")

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

        # Help Menu
        help_menu = menubar.addMenu("&Help")
        about_action = QAction("&About", self)
        about_action.setStatusTip("About Electronics Store System")
        about_action.triggered.connect(self._show_about_dialog)
        help_menu.addAction(about_action)

    def _setup_ui(self) -> None:
        """Set up main window structure with sidebar and stacked views."""
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)

        root_layout = QHBoxLayout(central_widget)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # 1. Left Navigation Sidebar
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(230)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        sidebar_layout.setSpacing(4)

        # Sidebar Header / Branding
        lbl_app = QLabel("⚡ Electronics Store")
        lbl_app.setObjectName("sidebarTitle")
        sidebar_layout.addWidget(lbl_app)

        # User Badge in Sidebar
        self.lbl_user_badge = QLabel()
        self.lbl_user_badge.setObjectName("userBadge")
        self.lbl_user_badge.setWordWrap(True)
        sidebar_layout.addWidget(self.lbl_user_badge)

        # Navigation Items
        self.nav_items = [
            ("dashboard", "📊 Dashboard", None),
            ("users", "👥 Users & Permissions", "users"),
            ("sales", "🛒 Sales & POS", "sales"),
            ("products", "📦 Products & Inventory", "products"),
            ("purchases", "🚚 Purchases", "purchases"),
            ("stock_adj", "⚖️ Stock Adjustments", "stock_adjustment"),
            ("reports", "📈 Reports & Analytics", "reports"),
            ("customers", "👤 Customers", "customers"),
            ("suppliers", "🏭 Suppliers", "suppliers"),
            ("warranty", "🛡️ Warranty Claims", "warranty"),
            ("backup", "💾 Backup & Restore", "backup_restore"),
        ]

        self.nav_buttons.clear()
        for key, label_text, req_module in self.nav_items:
            btn = QPushButton(label_text)
            btn.setProperty("class", "navBtn")
            btn.setCheckable(True)
            btn.clicked.connect(lambda _, k=key: self._on_nav_clicked(k))
            sidebar_layout.addWidget(btn)
            self.nav_buttons[key] = btn

        sidebar_layout.addStretch()

        # Sign Out button at bottom of sidebar
        btn_sidebar_logout = QPushButton("🚪 Sign Out")
        btn_sidebar_logout.setObjectName("sidebarLogout")
        btn_sidebar_logout.clicked.connect(self._handle_logout)
        sidebar_layout.addWidget(btn_sidebar_logout)

        root_layout.addWidget(sidebar)

        # 2. Main Content Stack
        self.content_stack = QStackedWidget()
        self.content_stack.setObjectName("contentArea")

        # Page 0: Dashboard Home
        self.page_dashboard = self._create_dashboard_page()
        self.content_stack.addWidget(self.page_dashboard)

        # Page 1: Users & Permissions Module
        self.page_users = UsersManagementWidget()
        self.content_stack.addWidget(self.page_users)

        # Page 2: Generic Placeholder for other modules
        self.page_placeholder = self._create_placeholder_page()
        self.content_stack.addWidget(self.page_placeholder)

        root_layout.addWidget(self.content_stack, stretch=1)

        self._refresh_nav_state()

    def _create_dashboard_page(self) -> QWidget:
        """Create dashboard overview page."""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(36, 36, 36, 36)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        card = QFrame()
        card.setStyleSheet("""
            QFrame {
                background-color: #ffffff;
                border: 1px solid #e2e8f0;
                border-radius: 12px;
                padding: 32px;
            }
        """)
        card.setFixedWidth(600)
        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(16)
        card_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        lbl_title = QLabel("⚡ Electronics Store System")
        lbl_title.setFont(QFont("Segoe UI", 22, QFont.Weight.Bold))
        lbl_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_title.setStyleSheet("color: #0f172a;")
        card_layout.addWidget(lbl_title)

        self.lbl_dash_user = QLabel()
        self.lbl_dash_user.setFont(QFont("Segoe UI", 12))
        self.lbl_dash_user.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(self.lbl_dash_user)

        desc = QLabel(
            "Use the sidebar navigation to manage users, configure modular permissions, "
            "and access application modules."
        )
        desc.setFont(QFont("Segoe UI", 11))
        desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        desc.setStyleSheet("color: #64748b; line-height: 1.4;")
        desc.setWordWrap(True)
        card_layout.addWidget(desc)

        layout.addWidget(card)
        return page

    def _create_placeholder_page(self) -> QWidget:
        """Generic placeholder page for upcoming modules."""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(36, 36, 36, 36)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        card = QFrame()
        card.setStyleSheet("background-color: #ffffff; border: 1px solid #e2e8f0; border-radius: 12px; padding: 32px;")
        card.setFixedWidth(520)
        card_layout = QVBoxLayout(card)
        card_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.setSpacing(12)

        self.lbl_placeholder_title = QLabel("Module Ready")
        self.lbl_placeholder_title.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        self.lbl_placeholder_title.setStyleSheet("color: #0f172a;")
        card_layout.addWidget(self.lbl_placeholder_title)

        self.lbl_placeholder_desc = QLabel("This module skeleton is configured and ready for implementation.")
        self.lbl_placeholder_desc.setFont(QFont("Segoe UI", 11))
        self.lbl_placeholder_desc.setStyleSheet("color: #64748b;")
        self.lbl_placeholder_desc.setWordWrap(True)
        card_layout.addWidget(self.lbl_placeholder_desc)

        layout.addWidget(card)
        return page

    def _on_nav_clicked(self, key: str) -> None:
        """Handle sidebar navigation button clicks with permission enforcement."""
        # Find module requirement
        req_module = next((item[2] for item in self.nav_items if item[0] == key), None)

        if req_module:
            # Check view permission for requested module
            if not check_permission(f"{req_module}.view", parent=self, action_name=f"access {key.title()}"):
                # Keep previously checked nav button active
                self._update_nav_selection()
                return

        for k, btn in self.nav_buttons.items():
            btn.setChecked(k == key)

        if key == "dashboard":
            self.content_stack.setCurrentIndex(0)
        elif key == "users":
            self.page_users.load_users()
            self.content_stack.setCurrentIndex(1)
        else:
            item_label = next((item[1] for item in self.nav_items if item[0] == key), key)
            self.lbl_placeholder_title.setText(item_label)
            self.lbl_placeholder_desc.setText(
                f"The <b>{item_label}</b> module is registered with modular permission control."
            )
            self.content_stack.setCurrentIndex(2)

    def _update_nav_selection(self) -> None:
        """Keep active button state consistent with visible page."""
        idx = self.content_stack.currentIndex()
        if idx == 0 and "dashboard" in self.nav_buttons:
            self.nav_buttons["dashboard"].setChecked(True)
        elif idx == 1 and "users" in self.nav_buttons:
            self.nav_buttons["users"].setChecked(True)

    def _refresh_nav_state(self) -> None:
        """Update navigation button availability based on session user permissions."""
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

        # Update Dashboard text
        self.lbl_dash_user.setText(
            f"👤 Logged in as: <b>{user.full_name}</b> (<span style='color: #2563eb;'>@{user.username}</span>) &nbsp;|&nbsp; Role: <b>{role_upper}</b>"
        )

        # Enable / Disable nav items based on can_view(module)
        for key, _, req_module in self.nav_items:
            if req_module is None:
                self.nav_buttons[key].setEnabled(True)
            else:
                allowed = can_view(req_module)
                self.nav_buttons[key].setEnabled(allowed)
                if not allowed:
                    self.nav_buttons[key].setToolTip(f"Access to {key.title()} is restricted for your role.")
                else:
                    self.nav_buttons[key].setToolTip("")

        # Default to Dashboard
        self._on_nav_clicked("dashboard")

    def _setup_status_bar(self) -> None:
        """Set up status bar."""
        status_bar = QStatusBar(self)
        self.setStatusBar(status_bar)
        self.update_status_bar()

    def update_status_bar(self) -> None:
        """Refresh status bar details."""
        user = self.session.current_user
        user_str = f"{user.username} ({user.role_name.upper()})" if user else "Not logged in"
        db_path = self.db_manager.db_path if self.db_manager else "store.db"
        self.statusBar().showMessage(f"🟢 Connected: {db_path} | Active User: {user_str}")

    def refresh_user_display(self) -> None:
        """Refresh entire view on session update or login."""
        self._refresh_nav_state()
        self.update_status_bar()

    def _handle_logout(self) -> None:
        """Logout user and notify controller."""
        self.session.logout()
        self.logout_requested.emit()
        self.close()

    def _show_about_dialog(self) -> None:
        """Show About dialog."""
        QMessageBox.about(
            self,
            "About Electronics Store System",
            "<h3>Electronics Store System</h3>"
            "<p>Enterprise Desktop Management System with modular Role-Based Access Control (RBAC).</p>"
            "<p>Version 0.2.0</p>",
        )
