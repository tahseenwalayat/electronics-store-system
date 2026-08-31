"""
First-Time Setup Wizard (PySide6).
Guides the user through initial store configuration and administrator account creation.
"""

from PySide6.QtWidgets import (
    QDialog,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QStackedWidget,
    QFrame,
    QMessageBox,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QIcon
from business.auth_service import AuthService


class SetupWizardDialog(QDialog):
    """
    Setup Wizard shown on first-ever launch when no user accounts exist.
    """

    setup_completed = Signal(object)  # Emits User object upon success

    def __init__(self, auth_service: AuthService, parent=None):
        super().__init__(parent)
        self.auth_service = auth_service
        self.setWindowTitle("First-Time Setup Wizard — Electronics Store System")
        self.setFixedSize(560, 620)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)

        self._setup_styles()
        self._setup_ui()

    def _setup_styles(self) -> None:
        """Apply modern, clean stylesheet."""
        self.setStyleSheet("""
            QDialog {
                background-color: #f8fafc;
                font-family: 'Segoe UI', sans-serif;
            }
            QFrame#card {
                background-color: #ffffff;
                border: 1px solid #e2e8f0;
                border-radius: 12px;
                padding: 24px;
            }
            QLabel#headerTitle {
                font-size: 20px;
                font-weight: 700;
                color: #0f172a;
            }
            QLabel#headerSubtitle {
                font-size: 13px;
                color: #64748b;
            }
            QLabel#sectionHeader {
                font-size: 14px;
                font-weight: 600;
                color: #334155;
                margin-top: 6px;
            }
            QLabel#fieldLabel {
                font-size: 12px;
                font-weight: 600;
                color: #475569;
            }
            QLineEdit {
                background-color: #f8fafc;
                border: 1.5px solid #cbd5e1;
                border-radius: 6px;
                padding: 8px 12px;
                font-size: 13px;
                color: #0f172a;
            }
            QLineEdit:focus {
                border-color: #2563eb;
                background-color: #ffffff;
            }
            QLabel#errorBanner {
                background-color: #fef2f2;
                border: 1px solid #fecaca;
                border-radius: 6px;
                color: #b91c1c;
                padding: 10px;
                font-size: 12px;
                font-weight: 500;
            }
            QPushButton#primaryBtn {
                background-color: #2563eb;
                color: #ffffff;
                border: none;
                border-radius: 6px;
                padding: 10px 20px;
                font-size: 13px;
                font-weight: 600;
                min-height: 20px;
            }
            QPushButton#primaryBtn:hover {
                background-color: #1d4ed8;
            }
            QPushButton#primaryBtn:pressed {
                background-color: #1e40af;
            }
            QPushButton#secondaryBtn {
                background-color: #f1f5f9;
                color: #475569;
                border: 1px solid #cbd5e1;
                border-radius: 6px;
                padding: 10px 18px;
                font-size: 13px;
                font-weight: 600;
            }
            QPushButton#secondaryBtn:hover {
                background-color: #e2e8f0;
                color: #1e293b;
            }
        """)

    def _setup_ui(self) -> None:
        """Construct wizard UI layout."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 24, 24, 24)
        main_layout.setSpacing(16)

        # Card Container
        card = QFrame()
        card.setObjectName("card")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(20, 16, 20, 16)
        card_layout.setSpacing(14)

        # Header
        header_layout = QVBoxLayout()
        header_layout.setSpacing(4)
        title_label = QLabel("⚡ First-Time System Setup")
        title_label.setObjectName("headerTitle")
        subtitle_label = QLabel(
            "Welcome! Configure your store information and set up your initial administrator account."
        )
        subtitle_label.setObjectName("headerSubtitle")
        subtitle_label.setWordWrap(True)
        header_layout.addWidget(title_label)
        header_layout.addWidget(subtitle_label)
        card_layout.addLayout(header_layout)

        # Error Banner (Hidden by default)
        self.error_banner = QLabel("")
        self.error_banner.setObjectName("errorBanner")
        self.error_banner.setWordWrap(True)
        self.error_banner.hide()
        card_layout.addWidget(self.error_banner)

        # Stacked Pages
        self.stack = QStackedWidget()

        # Step 1: Store Information
        self.page_store = QWidget()
        store_layout = QVBoxLayout(self.page_store)
        store_layout.setContentsMargins(0, 0, 0, 0)
        store_layout.setSpacing(10)

        sec1_label = QLabel("🏪 1. Store Information")
        sec1_label.setObjectName("sectionHeader")
        store_layout.addWidget(sec1_label)

        lbl_name = QLabel("Store Name *")
        lbl_name.setObjectName("fieldLabel")
        self.txt_store_name = QLineEdit()
        self.txt_store_name.setPlaceholderText("e.g. Apex Electronics & Tech")
        store_layout.addWidget(lbl_name)
        store_layout.addWidget(self.txt_store_name)

        lbl_address = QLabel("Store Address *")
        lbl_address.setObjectName("fieldLabel")
        self.txt_address = QLineEdit()
        self.txt_address.setPlaceholderText("e.g. 100 Innovation Way, Suite 4B")
        store_layout.addWidget(lbl_address)
        store_layout.addWidget(self.txt_address)

        lbl_phone = QLabel("Phone Number *")
        lbl_phone.setObjectName("fieldLabel")
        self.txt_phone = QLineEdit()
        self.txt_phone.setPlaceholderText("e.g. +1 (555) 019-2834")
        store_layout.addWidget(lbl_phone)
        store_layout.addWidget(self.txt_phone)

        store_layout.addStretch()
        self.stack.addWidget(self.page_store)

        # Step 2: Admin Account
        self.page_admin = QWidget()
        admin_layout = QVBoxLayout(self.page_admin)
        admin_layout.setContentsMargins(0, 0, 0, 0)
        admin_layout.setSpacing(10)

        sec2_label = QLabel("👤 2. Administrator Account")
        sec2_label.setObjectName("sectionHeader")
        admin_layout.addWidget(sec2_label)

        lbl_user = QLabel("Admin Username *")
        lbl_user.setObjectName("fieldLabel")
        self.txt_username = QLineEdit()
        self.txt_username.setPlaceholderText("e.g. admin")
        admin_layout.addWidget(lbl_user)
        admin_layout.addWidget(self.txt_username)

        lbl_pass = QLabel("Admin Password (min. 6 chars) *")
        lbl_pass.setObjectName("fieldLabel")
        self.txt_password = QLineEdit()
        self.txt_password.setEchoMode(QLineEdit.EchoMode.Password)
        self.txt_password.setPlaceholderText("••••••••")
        admin_layout.addWidget(lbl_pass)
        admin_layout.addWidget(self.txt_password)

        lbl_confirm = QLabel("Confirm Password *")
        lbl_confirm.setObjectName("fieldLabel")
        self.txt_confirm_pass = QLineEdit()
        self.txt_confirm_pass.setEchoMode(QLineEdit.EchoMode.Password)
        self.txt_confirm_pass.setPlaceholderText("••••••••")
        admin_layout.addWidget(lbl_confirm)
        admin_layout.addWidget(self.txt_confirm_pass)

        admin_layout.addStretch()
        self.stack.addWidget(self.page_admin)

        card_layout.addWidget(self.stack)

        # Bottom Action Bar
        btn_layout = QHBoxLayout()
        self.btn_back = QPushButton("← Back")
        self.btn_back.setObjectName("secondaryBtn")
        self.btn_back.clicked.connect(self._on_back_clicked)
        self.btn_back.hide()  # Hidden on first step

        self.btn_next = QPushButton("Next →")
        self.btn_next.setObjectName("primaryBtn")
        self.btn_next.clicked.connect(self._on_next_clicked)

        btn_layout.addWidget(self.btn_back)
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_next)
        card_layout.addLayout(btn_layout)

        main_layout.addWidget(card)

        # Enter key triggers next/finish
        self.txt_store_name.returnPressed.connect(self._on_next_clicked)
        self.txt_address.returnPressed.connect(self._on_next_clicked)
        self.txt_phone.returnPressed.connect(self._on_next_clicked)
        self.txt_username.returnPressed.connect(self._on_next_clicked)
        self.txt_password.returnPressed.connect(self._on_next_clicked)
        self.txt_confirm_pass.returnPressed.connect(self._on_next_clicked)

    def _show_error(self, message: str) -> None:
        """Display error banner with descriptive text."""
        self.error_banner.setText(f"⚠️ {message}")
        self.error_banner.show()

    def _clear_error(self) -> None:
        """Hide error banner."""
        self.error_banner.setText("")
        self.error_banner.hide()

    def _on_back_clicked(self) -> None:
        """Navigate to previous step."""
        self._clear_error()
        current_index = self.stack.currentIndex()
        if current_index > 0:
            self.stack.setCurrentIndex(current_index - 1)
            self.btn_back.hide()
            self.btn_next.setText("Next →")

    def _on_next_clicked(self) -> None:
        """Navigate to next step or submit form on final step."""
        self._clear_error()
        current_index = self.stack.currentIndex()

        if current_index == 0:
            # Validate Step 1 (Store Information)
            store_name = self.txt_store_name.text().strip()
            address = self.txt_address.text().strip()
            phone = self.txt_phone.text().strip()

            if not store_name:
                self._show_error("Please enter your Store Name.")
                self.txt_store_name.setFocus()
                return
            if not address:
                self._show_error("Please enter the Store Address.")
                self.txt_address.setFocus()
                return
            if not phone:
                self._show_error("Please enter a Contact Phone Number.")
                self.txt_phone.setFocus()
                return

            # Advance to Step 2
            self.stack.setCurrentIndex(1)
            self.btn_back.show()
            self.btn_next.setText("Finish Setup ✓")
            self.txt_username.setFocus()

        elif current_index == 1:
            # Validate Step 2 (Admin Account)
            username = self.txt_username.text().strip()
            password = self.txt_password.text()
            confirm = self.txt_confirm_pass.text()

            if not username:
                self._show_error("Please enter an Admin Username.")
                self.txt_username.setFocus()
                return
            if len(username) < 3:
                self._show_error("Admin Username must be at least 3 characters.")
                self.txt_username.setFocus()
                return
            if not password:
                self._show_error("Please enter an Admin Password.")
                self.txt_password.setFocus()
                return
            if len(password) < 6:
                self._show_error("Admin Password must be at least 6 characters.")
                self.txt_password.setFocus()
                return
            if password != confirm:
                self._show_error("Passwords do not match. Please re-enter.")
                self.txt_confirm_pass.setFocus()
                return

            # Execute setup via AuthService
            self.btn_next.setEnabled(False)
            self.btn_next.setText("Configuring...")

            success, user, message = self.auth_service.complete_first_time_setup(
                store_name=self.txt_store_name.text().strip(),
                store_address=self.txt_address.text().strip(),
                store_phone=self.txt_phone.text().strip(),
                admin_username=username,
                admin_password=password,
                confirm_password=confirm,
            )

            self.btn_next.setEnabled(True)
            self.btn_next.setText("Finish Setup ✓")

            if not success or user is None:
                self._show_error(message)
                return

            # Success
            self.setup_completed.emit(user)
            self.accept()
