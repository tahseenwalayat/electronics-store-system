"""
Users & Permissions Management UI (PySide6).
Provides comprehensive user list, creation/edit dialogs, modular permission grids, and password reset.
"""

from typing import Optional, Set, Dict, Any
from PySide6.QtWidgets import (
    QWidget,
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QComboBox,
    QCheckBox,
    QGroupBox,
    QScrollArea,
    QFrame,
    QMessageBox,
    QDialogButtonBox,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QColor

from business.user_service import UserService
from business.permissions import (
    MODULES,
    ACTIONS,
    DEFAULT_ROLE_PERMISSIONS,
    has_permission,
    can_manage,
    can_delete,
    check_permission,
)
from business.session import get_session


class PermissionGridWidget(QWidget):
    """
    Grid component showing 10 system modules x 3 actions (View, Create/Edit, Delete).
    Enforces that 'Delete' checkboxes can only be active for Administrators.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.checkbox_map: Dict[str, QCheckBox] = {}
        self.is_admin_role = False
        self._setup_ui()

    def _setup_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(8)

        grid_frame = QFrame()
        grid_frame.setStyleSheet("""
            QFrame {
                background-color: #ffffff;
                border: 1px solid #e2e8f0;
                border-radius: 8px;
            }
            QCheckBox {
                font-size: 12px;
                spacing: 6px;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
            }
            QLabel.headerCell {
                font-weight: 700;
                color: #1e293b;
                font-size: 12px;
                padding: 6px;
                border-bottom: 2px solid #cbd5e1;
            }
            QLabel.moduleCell {
                font-weight: 600;
                color: #334155;
                font-size: 12px;
                padding: 4px;
            }
        """)

        grid = QGridLayout(grid_frame)
        grid.setContentsMargins(12, 10, 12, 10)
        grid.setHorizontalSpacing(16)
        grid.setVerticalSpacing(8)

        # Header Row
        lbl_mod_hdr = QLabel("System Module")
        lbl_mod_hdr.setProperty("class", "headerCell")
        grid.addWidget(lbl_mod_hdr, 0, 0)

        for col_idx, action in enumerate(ACTIONS, start=1):
            lbl_act = QLabel(action["name"])
            lbl_act.setProperty("class", "headerCell")
            lbl_act.setAlignment(Qt.AlignmentFlag.AlignCenter)
            grid.addWidget(lbl_act, 0, col_idx)

        # Module Rows
        for row_idx, mod in enumerate(MODULES, start=1):
            lbl_mod = QLabel(f"📦 {mod['name']}")
            lbl_mod.setProperty("class", "moduleCell")
            grid.addWidget(lbl_mod, row_idx, 0)

            for col_idx, action in enumerate(ACTIONS, start=1):
                code = f"{mod['key']}.{action['key']}"
                cb = QCheckBox()
                cb.setToolTip(f"{mod['name']} - {action['desc']}")
                
                # Center checkbox in cell
                cell_widget = QWidget()
                cell_layout = QHBoxLayout(cell_widget)
                cell_layout.setContentsMargins(0, 0, 0, 0)
                cell_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
                cell_layout.addWidget(cb)

                grid.addWidget(cell_widget, row_idx, col_idx)
                self.checkbox_map[code] = cb

        main_layout.addWidget(grid_frame)

    def set_role(self, role_name: str, apply_defaults: bool = True) -> None:
        """Update checkbox state and accessibility according to selected role."""
        role_key = role_name.lower()
        self.is_admin_role = (role_key == "admin")

        if apply_defaults:
            default_perms = DEFAULT_ROLE_PERMISSIONS.get(role_key, set())
            for code, cb in self.checkbox_map.items():
                cb.setChecked(code in default_perms)

        # Enforce Rule: Delete column strictly disabled for non-admins
        for code, cb in self.checkbox_map.items():
            if code.endswith(".delete"):
                if not self.is_admin_role:
                    cb.setChecked(False)
                    cb.setEnabled(False)
                    cb.setToolTip("Delete capability is strictly restricted to Administrators.")
                else:
                    cb.setEnabled(True)
                    cb.setToolTip("Delete capability allowed for Administrator.")
            else:
                cb.setEnabled(True)

    def get_selected_permissions(self) -> Set[str]:
        """Return set of all checked permission codes."""
        selected = {code for code, cb in self.checkbox_map.items() if cb.isChecked()}
        # Enforce non-admins cannot hold delete permissions
        if not self.is_admin_role:
            selected = {p for p in selected if not p.endswith(".delete")}
        return selected

    def set_selected_permissions(self, permissions: Set[str]) -> None:
        """Load an explicit set of permissions into checkboxes."""
        for code, cb in self.checkbox_map.items():
            is_checked = code in permissions
            if code.endswith(".delete") and not self.is_admin_role:
                cb.setChecked(False)
                cb.setEnabled(False)
            else:
                cb.setChecked(is_checked)


class UserDialog(QDialog):
    """
    Dialog for adding or editing a user account with modular permissions.
    """

    def __init__(self, user_service: UserService, user_data: Optional[Dict[str, Any]] = None, parent=None):
        super().__init__(parent)
        self.user_service = user_service
        self.user_data = user_data
        self.is_edit_mode = user_data is not None

        title = f"Edit User: {user_data['username']}" if self.is_edit_mode else "Add New User"
        self.setWindowTitle(f"{title} — Electronics Store System")
        self.resize(620, 720)
        self.setMinimumSize(540, 600)

        self._setup_ui()
        if self.is_edit_mode:
            self._load_user_data()
        else:
            self._apply_initial_role_defaults()

    def _setup_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 16, 20, 16)
        main_layout.setSpacing(12)

        # Scroll Area for Form & Permissions Grid
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        container = QWidget()
        form_layout = QVBoxLayout(container)
        form_layout.setContentsMargins(4, 4, 4, 4)
        form_layout.setSpacing(12)

        # Basic Info Group
        info_group = QGroupBox("User Account Details")
        info_group.setStyleSheet("QGroupBox { font-weight: bold; color: #0f172a; }")
        grid_info = QGridLayout(info_group)
        grid_info.setSpacing(10)

        # Username
        grid_info.addWidget(QLabel("Username *"), 0, 0)
        self.txt_username = QLineEdit()
        self.txt_username.setPlaceholderText("e.g. john_sales")
        if self.is_edit_mode:
            self.txt_username.setEnabled(False)
        grid_info.addWidget(self.txt_username, 0, 1)

        # Full Name
        grid_info.addWidget(QLabel("Full Name *"), 1, 0)
        self.txt_fullname = QLineEdit()
        self.txt_fullname.setPlaceholderText("e.g. John Doe")
        grid_info.addWidget(self.txt_fullname, 1, 1)

        # Role Selection
        grid_info.addWidget(QLabel("Role *"), 2, 0)
        self.cmb_role = QComboBox()
        roles = self.user_service.get_all_roles()
        for r in roles:
            self.cmb_role.addItem(r["name"].capitalize(), r["id"])
        self.cmb_role.currentTextChanged.connect(self._on_role_changed)
        grid_info.addWidget(self.cmb_role, 2, 1)

        # Password (only visible/mandatory on Add)
        if not self.is_edit_mode:
            grid_info.addWidget(QLabel("Password *"), 3, 0)
            self.txt_password = QLineEdit()
            self.txt_password.setEchoMode(QLineEdit.EchoMode.Password)
            self.txt_password.setPlaceholderText("Minimum 6 characters")
            grid_info.addWidget(self.txt_password, 3, 1)

            grid_info.addWidget(QLabel("Confirm Password *"), 4, 0)
            self.txt_confirm = QLineEdit()
            self.txt_confirm.setEchoMode(QLineEdit.EchoMode.Password)
            self.txt_confirm.setPlaceholderText("Re-type password")
            grid_info.addWidget(self.txt_confirm, 4, 1)

        # Email & Phone
        row_offset = 5 if not self.is_edit_mode else 3
        grid_info.addWidget(QLabel("Email"), row_offset, 0)
        self.txt_email = QLineEdit()
        self.txt_email.setPlaceholderText("john@example.com")
        grid_info.addWidget(self.txt_email, row_offset, 1)

        grid_info.addWidget(QLabel("Phone"), row_offset + 1, 0)
        self.txt_phone = QLineEdit()
        self.txt_phone.setPlaceholderText("+1 555-0199")
        grid_info.addWidget(self.txt_phone, row_offset + 1, 1)

        # Active Status Checkbox
        self.chk_active = QCheckBox("Account is Active")
        self.chk_active.setChecked(True)
        grid_info.addWidget(self.chk_active, row_offset + 2, 1)

        form_layout.addWidget(info_group)

        # Permissions Grid Group
        perm_group = QGroupBox("Permissions Matrix")
        perm_group.setStyleSheet("QGroupBox { font-weight: bold; color: #0f172a; }")
        perm_layout = QVBoxLayout(perm_group)
        perm_layout.setContentsMargins(8, 12, 8, 8)

        perm_help = QLabel(
            "Select permissions for this user. "
            "Note: <b>Delete</b> capabilities are strictly reserved for Administrator accounts."
        )
        perm_help.setStyleSheet("color: #64748b; font-size: 11px;")
        perm_help.setWordWrap(True)
        perm_layout.addWidget(perm_help)

        self.perm_grid = PermissionGridWidget()
        perm_layout.addWidget(self.perm_grid)

        form_layout.addWidget(perm_group)
        scroll.setWidget(container)
        main_layout.addWidget(scroll)

        # Dialog Buttons
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(self._on_save_clicked)
        button_box.rejected.connect(self.reject)
        main_layout.addWidget(button_box)

    def _on_role_changed(self, role_text: str) -> None:
        """Notify permission grid of role change."""
        self.perm_grid.set_role(role_text, apply_defaults=not self.is_edit_mode)

    def _apply_initial_role_defaults(self) -> None:
        """Set default role to Cashier or Manager for new users."""
        default_index = self.cmb_role.findText("Cashier")
        if default_index >= 0:
            self.cmb_role.setCurrentIndex(default_index)
        self.perm_grid.set_role(self.cmb_role.currentText(), apply_defaults=True)

    def _load_user_data(self) -> None:
        """Populate form with existing user records."""
        if not self.user_data:
            return
        self.txt_username.setText(self.user_data.get("username", ""))
        self.txt_fullname.setText(self.user_data.get("full_name", ""))
        self.txt_email.setText(self.user_data.get("email", "") or "")
        self.txt_phone.setText(self.user_data.get("phone", "") or "")
        self.chk_active.setChecked(bool(self.user_data.get("is_active", 1)))

        role_name = self.user_data.get("role_name", "").capitalize()
        index = self.cmb_role.findText(role_name)
        if index >= 0:
            self.cmb_role.setCurrentIndex(index)

        # Load effective permissions
        user_id = self.user_data["id"]
        perms = self.user_service.get_user_effective_permissions(user_id)
        self.perm_grid.set_role(role_name, apply_defaults=False)
        self.perm_grid.set_selected_permissions(perms)

    def _on_save_clicked(self) -> None:
        """Validate and submit user data."""
        username = self.txt_username.text().strip()
        full_name = self.txt_fullname.text().strip()
        role_id = self.cmb_role.currentData()
        email = self.txt_email.text().strip() or None
        phone = self.txt_phone.text().strip() or None
        is_active = self.chk_active.isChecked()
        selected_permissions = self.perm_grid.get_selected_permissions()

        if not full_name:
            QMessageBox.warning(self, "Validation Error", "Full Name is required.")
            self.txt_fullname.setFocus()
            return

        if not self.is_edit_mode:
            # Create User
            if not username or len(username) < 3:
                QMessageBox.warning(self, "Validation Error", "Username must be at least 3 characters.")
                self.txt_username.setFocus()
                return

            password = self.txt_password.text()
            confirm = self.txt_confirm.text()

            if not password or len(password) < 6:
                QMessageBox.warning(self, "Validation Error", "Password must be at least 6 characters.")
                self.txt_password.setFocus()
                return

            if password != confirm:
                QMessageBox.warning(self, "Validation Error", "Passwords do not match.")
                self.txt_confirm.setFocus()
                return

            success, new_id, msg = self.user_service.create_user(
                username=username,
                password=password,
                full_name=full_name,
                role_id=role_id,
                email=email,
                phone=phone,
                is_active=is_active,
                permissions=selected_permissions,
            )

            if not success:
                QMessageBox.critical(self, "Error Creating User", msg)
                return

            QMessageBox.information(self, "Success", f"User '{username}' created successfully!")
            self.accept()

        else:
            # Update User
            user_id = self.user_data["id"]
            success, msg = self.user_service.update_user(
                user_id=user_id,
                full_name=full_name,
                role_id=role_id,
                email=email,
                phone=phone,
                is_active=is_active,
                permissions=selected_permissions,
            )

            if not success:
                QMessageBox.critical(self, "Error Updating User", msg)
                return

            QMessageBox.information(self, "Success", f"User '{username}' updated successfully!")
            self.accept()


class PasswordResetDialog(QDialog):
    """
    Dialog for administrators to reset a user's password.
    """

    def __init__(self, username: str, user_id: int, user_service: UserService, parent=None):
        super().__init__(parent)
        self.username = username
        self.user_id = user_id
        self.user_service = user_service

        self.setWindowTitle(f"Reset Password: {username} — Electronics Store System")
        self.setFixedSize(380, 240)

        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        lbl_info = QLabel(f"Set a new password for <b>{self.username}</b>:")
        lbl_info.setStyleSheet("color: #334155; font-size: 13px;")
        layout.addWidget(lbl_info)

        # New Password
        layout.addWidget(QLabel("New Password (min. 6 chars) *"))
        self.txt_pass = QLineEdit()
        self.txt_pass.setEchoMode(QLineEdit.EchoMode.Password)
        self.txt_pass.setPlaceholderText("••••••••")
        layout.addWidget(self.txt_pass)

        # Confirm Password
        layout.addWidget(QLabel("Confirm New Password *"))
        self.txt_confirm = QLineEdit()
        self.txt_confirm.setEchoMode(QLineEdit.EchoMode.Password)
        self.txt_confirm.setPlaceholderText("••••••••")
        layout.addWidget(self.txt_confirm)

        # Buttons
        btn_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        btn_box.button(QDialogButtonBox.StandardButton.Ok).setText("Reset Password")
        btn_box.accepted.connect(self._on_reset_clicked)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)

    def _on_reset_clicked(self) -> None:
        p1 = self.txt_pass.text()
        p2 = self.txt_confirm.text()

        if not p1 or len(p1) < 6:
            QMessageBox.warning(self, "Validation Error", "Password must be at least 6 characters.")
            self.txt_pass.setFocus()
            return
        if p1 != p2:
            QMessageBox.warning(self, "Validation Error", "Passwords do not match.")
            self.txt_confirm.setFocus()
            return

        success, msg = self.user_service.reset_password(self.user_id, p1)
        if not success:
            QMessageBox.critical(self, "Error", msg)
            return

        QMessageBox.information(self, "Success", msg)
        self.accept()


class UsersManagementWidget(QWidget):
    """
    Main widget for listing, filtering, adding, editing, and deleting users.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.user_service = UserService()
        self._setup_styles()
        self._setup_ui()
        self.load_users()

    def _setup_styles(self) -> None:
        self.setStyleSheet("""
            QWidget {
                font-family: 'Segoe UI', sans-serif;
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
            QPushButton#primaryBtn {
                background-color: #2563eb;
                color: #ffffff;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: 600;
                font-size: 13px;
            }
            QPushButton#primaryBtn:hover {
                background-color: #1d4ed8;
            }
            QPushButton#actionBtn {
                background-color: #f1f5f9;
                color: #334155;
                border: 1px solid #cbd5e1;
                border-radius: 4px;
                padding: 4px 10px;
                font-size: 12px;
                font-weight: 500;
            }
            QPushButton#actionBtn:hover {
                background-color: #e2e8f0;
            }
            QPushButton#deleteBtn {
                background-color: #fef2f2;
                color: #b91c1c;
                border: 1px solid #fca5a5;
                border-radius: 4px;
                padding: 4px 10px;
                font-size: 12px;
                font-weight: 500;
            }
            QPushButton#deleteBtn:hover {
                background-color: #fee2e2;
            }
            QPushButton#deleteBtn:disabled {
                background-color: #f1f5f9;
                color: #94a3b8;
                border-color: #e2e8f0;
            }
        """)

    def _setup_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 20, 24, 20)
        main_layout.setSpacing(16)

        # Header Title & Actions Bar
        top_bar = QHBoxLayout()

        header_layout = QVBoxLayout()
        lbl_title = QLabel("👥 Users & Permissions")
        lbl_title.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        lbl_title.setStyleSheet("color: #0f172a;")
        lbl_subtitle = QLabel("Manage employee user accounts, system roles, and modular access control.")
        lbl_subtitle.setStyleSheet("color: #64748b; font-size: 12px;")
        header_layout.addWidget(lbl_title)
        header_layout.addWidget(lbl_subtitle)
        top_bar.addLayout(header_layout)

        top_bar.addStretch()

        # Add User Button (Permission guarded)
        self.btn_add = QPushButton("+ Add New User")
        self.btn_add.setObjectName("primaryBtn")
        self.btn_add.clicked.connect(self._on_add_user_clicked)
        # Enable only if user has users.manage
        self.btn_add.setEnabled(can_manage("users"))
        if not can_manage("users"):
            self.btn_add.setToolTip("You do not have permission to add new users.")
        top_bar.addWidget(self.btn_add)

        main_layout.addLayout(top_bar)

        # Filters Bar
        filter_bar = QHBoxLayout()
        filter_bar.setSpacing(10)

        self.txt_search = QLineEdit()
        self.txt_search.setPlaceholderText("🔍 Search by username, name, email...")
        self.txt_search.textChanged.connect(self._filter_users)
        self.txt_search.setFixedHeight(34)
        filter_bar.addWidget(self.txt_search, stretch=3)

        self.cmb_role_filter = QComboBox()
        self.cmb_role_filter.addItem("All Roles", "")
        self.cmb_role_filter.addItem("Admin", "admin")
        self.cmb_role_filter.addItem("Manager", "manager")
        self.cmb_role_filter.addItem("Cashier", "cashier")
        self.cmb_role_filter.currentIndexChanged.connect(self._filter_users)
        self.cmb_role_filter.setFixedHeight(34)
        filter_bar.addWidget(self.cmb_role_filter, stretch=1)

        self.btn_refresh = QPushButton("↻ Refresh")
        self.btn_refresh.setFixedHeight(34)
        self.btn_refresh.clicked.connect(self.load_users)
        filter_bar.addWidget(self.btn_refresh)

        main_layout.addLayout(filter_bar)

        # Users Table
        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels([
            "ID", "Username", "Full Name", "Role", "Status", "Email / Phone", "Last Login", "Actions"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(7, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(0, 50)
        self.table.setColumnWidth(1, 120)
        self.table.setColumnWidth(3, 100)
        self.table.setColumnWidth(4, 90)
        self.table.setColumnWidth(5, 170)
        self.table.setColumnWidth(6, 140)
        self.table.setColumnWidth(7, 230)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

        main_layout.addWidget(self.table)

    def load_users(self) -> None:
        """Fetch and render all users."""
        self.raw_users = self.user_service.get_all_users()
        self._filter_users()

    def _filter_users(self) -> None:
        """Filter cached user list based on search and role selection."""
        search_query = self.txt_search.text().strip().lower()
        role_filter = self.cmb_role_filter.currentData()

        filtered = []
        for u in getattr(self, "raw_users", []):
            if role_filter and u["role_name"].lower() != role_filter:
                continue
            if search_query:
                match_user = (
                    search_query in u["username"].lower()
                    or search_query in u["full_name"].lower()
                    or search_query in (u["email"] or "").lower()
                    or search_query in (u["phone"] or "").lower()
                )
                if not match_user:
                    continue
            filtered.append(u)

        self._populate_table(filtered)

    def _populate_table(self, users: list) -> None:
        """Render rows into table widget."""
        self.table.setRowCount(len(users))

        user_can_manage = can_manage("users")
        user_can_delete = can_delete("users")  # Strictly Admin

        for row_idx, u in enumerate(users):
            # ID
            item_id = QTableWidgetItem(str(u["id"]))
            item_id.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row_idx, 0, item_id)

            # Username
            item_user = QTableWidgetItem(u["username"])
            item_user.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
            self.table.setItem(row_idx, 1, item_user)

            # Full Name
            self.table.setItem(row_idx, 2, QTableWidgetItem(u["full_name"]))

            # Role Badge
            role_str = u["role_name"].upper()
            item_role = QTableWidgetItem(role_str)
            item_role.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            if role_str == "ADMIN":
                item_role.setForeground(QColor("#7c3aed"))
            elif role_str == "MANAGER":
                item_role.setForeground(QColor("#0284c7"))
            else:
                item_role.setForeground(QColor("#16a34a"))
            self.table.setItem(row_idx, 3, item_role)

            # Status
            status_text = "Active" if u["is_active"] else "Inactive"
            item_status = QTableWidgetItem(status_text)
            item_status.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item_status.setForeground(QColor("#16a34a" if u["is_active"] else "#dc2626"))
            self.table.setItem(row_idx, 4, item_status)

            # Contact
            contact = u["email"] or u["phone"] or "—"
            self.table.setItem(row_idx, 5, QTableWidgetItem(contact))

            # Last Login
            login_str = u["last_login_at"] or "Never"
            self.table.setItem(row_idx, 6, QTableWidgetItem(login_str))

            # Actions Cell
            action_widget = QWidget()
            action_layout = QHBoxLayout(action_widget)
            action_layout.setContentsMargins(4, 2, 4, 2)
            action_layout.setSpacing(6)

            # Edit Button
            btn_edit = QPushButton("Edit")
            btn_edit.setObjectName("actionBtn")
            btn_edit.setEnabled(user_can_manage)
            btn_edit.clicked.connect(lambda _, udata=u: self._on_edit_user_clicked(udata))
            action_layout.addWidget(btn_edit)

            # Reset Password Button
            btn_pwd = QPushButton("Reset Pwd")
            btn_pwd.setObjectName("actionBtn")
            btn_pwd.setEnabled(user_can_manage)
            btn_pwd.clicked.connect(lambda _, udata=u: self._on_reset_password_clicked(udata))
            action_layout.addWidget(btn_pwd)

            # Delete Button (Admin only)
            btn_del = QPushButton("Delete")
            btn_del.setObjectName("deleteBtn")
            btn_del.setEnabled(user_can_delete)
            if not user_can_delete:
                btn_del.setToolTip("Delete operation strictly restricted to Administrators.")
            btn_del.clicked.connect(lambda _, udata=u: self._on_delete_user_clicked(udata))
            action_layout.addWidget(btn_del)

            self.table.setCellWidget(row_idx, 7, action_widget)
            self.table.setRowHeight(row_idx, 42)

    def _on_add_user_clicked(self) -> None:
        """Open dialog to create new user."""
        if not check_permission("users.manage", parent=self, action_name="create a user"):
            return
        dlg = UserDialog(self.user_service, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.load_users()

    def _on_edit_user_clicked(self, user_data: Dict[str, Any]) -> None:
        """Open dialog to edit existing user."""
        if not check_permission("users.manage", parent=self, action_name="edit user details"):
            return
        dlg = UserDialog(self.user_service, user_data=user_data, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.load_users()

    def _on_reset_password_clicked(self, user_data: Dict[str, Any]) -> None:
        """Open dialog to reset password."""
        if not check_permission("users.manage", parent=self, action_name="reset user passwords"):
            return
        dlg = PasswordResetDialog(user_data["username"], user_data["id"], self.user_service, parent=self)
        dlg.exec()

    def _on_delete_user_clicked(self, user_data: Dict[str, Any]) -> None:
        """Execute user deletion or deactivation with confirmation."""
        if not check_permission("users.delete", parent=self, action_name="delete a user account"):
            return

        reply = QMessageBox.question(
            self,
            "Confirm Delete",
            f"Are you sure you want to delete or deactivate user account <b>'{user_data['username']}'</b>?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            success, msg = self.user_service.delete_user(user_data["id"])
            if success:
                QMessageBox.information(self, "User Deleted", msg)
                self.load_users()
            else:
                QMessageBox.critical(self, "Delete Failed", msg)
