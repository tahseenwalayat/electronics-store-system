"""
Login Window (PySide6).
Modern authentication screen for cashier, manager, and administrative users.
"""

from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QFrame,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QIcon, QAction
from business.auth_service import AuthService


class LoginWindow(QMainWindow):
    """
    Application Login Window.
    """

    login_successful = Signal(object)  # Emits authenticated User object

    def __init__(self, auth_service: AuthService, parent=None):
        super().__init__(parent)
        self.auth_service = auth_service
        self.setWindowTitle("Sign In — Electronics Store System")
        self.setFixedSize(440, 520)

        self._setup_styles()
        self._setup_ui()

    def _setup_styles(self) -> None:
        """Set modern application stylesheet."""
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f1f5f9;
                font-family: 'Segoe UI', sans-serif;
            }
            QFrame#card {
                background-color: #ffffff;
                border: 1px solid #e2e8f0;
                border-radius: 12px;
                padding: 24px;
            }
            QLabel#logoIcon {
                font-size: 32px;
            }
            QLabel#titleLabel {
                font-size: 20px;
                font-weight: 700;
                color: #0f172a;
            }
            QLabel#subtitleLabel {
                font-size: 13px;
                color: #64748b;
            }
            QLabel#fieldLabel {
                font-size: 12px;
                font-weight: 600;
                color: #475569;
                margin-top: 4px;
            }
            QLineEdit {
                background-color: #f8fafc;
                border: 1.5px solid #cbd5e1;
                border-radius: 6px;
                padding: 10px 12px;
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
                padding: 10px 12px;
                font-size: 12px;
                font-weight: 500;
            }
            QPushButton#loginButton {
                background-color: #2563eb;
                color: #ffffff;
                border: none;
                border-radius: 6px;
                padding: 12px 20px;
                font-size: 14px;
                font-weight: 600;
                margin-top: 8px;
            }
            QPushButton#loginButton:hover {
                background-color: #1d4ed8;
            }
            QPushButton#loginButton:pressed {
                background-color: #1e40af;
            }
            QPushButton#loginButton:disabled {
                background-color: #94a3b8;
            }
            QLabel#footerLabel {
                font-size: 11px;
                color: #94a3b8;
            }
        """)

    def _setup_ui(self) -> None:
        """Construct login window layout."""
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(32, 28, 32, 28)
        main_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Card container
        card = QFrame()
        card.setObjectName("card")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(20, 20, 20, 20)
        card_layout.setSpacing(12)

        # Header with Logo & Title
        header_layout = QVBoxLayout()
        header_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_layout.setSpacing(4)

        logo_label = QLabel("⚡")
        logo_label.setObjectName("logoIcon")
        logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        title_label = QLabel("Electronics Store Pro")
        title_label.setObjectName("titleLabel")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        subtitle_label = QLabel("Enter your credentials to access the system")
        subtitle_label.setObjectName("subtitleLabel")
        subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        header_layout.addWidget(logo_label)
        header_layout.addWidget(title_label)
        header_layout.addWidget(subtitle_label)
        card_layout.addLayout(header_layout)

        # Error Banner (Hidden by default)
        self.error_banner = QLabel("")
        self.error_banner.setObjectName("errorBanner")
        self.error_banner.setWordWrap(True)
        self.error_banner.hide()
        card_layout.addWidget(self.error_banner)

        # Username Field
        lbl_user = QLabel("Username")
        lbl_user.setObjectName("fieldLabel")
        self.txt_username = QLineEdit()
        self.txt_username.setPlaceholderText("Enter your username")
        self.txt_username.textChanged.connect(self._clear_error)
        self.txt_username.returnPressed.connect(self._on_login_clicked)
        card_layout.addWidget(lbl_user)
        card_layout.addWidget(self.txt_username)

        # Password Field
        lbl_pass = QLabel("Password")
        lbl_pass.setObjectName("fieldLabel")
        self.txt_password = QLineEdit()
        self.txt_password.setEchoMode(QLineEdit.EchoMode.Password)
        self.txt_password.setPlaceholderText("••••••••")
        self.txt_password.textChanged.connect(self._clear_error)
        self.txt_password.returnPressed.connect(self._on_login_clicked)

        # Toggle password visibility action
        self.toggle_pass_action = QAction("👁", self)
        self.toggle_pass_action.setToolTip("Show / Hide Password")
        self.toggle_pass_action.triggered.connect(self._toggle_password_visibility)
        self.txt_password.addAction(self.toggle_pass_action, QLineEdit.ActionPosition.TrailingPosition)

        card_layout.addWidget(lbl_pass)
        card_layout.addWidget(self.txt_password)

        # Sign In Button
        self.btn_login = QPushButton("Sign In")
        self.btn_login.setObjectName("loginButton")
        self.btn_login.clicked.connect(self._on_login_clicked)
        card_layout.addWidget(self.btn_login)

        main_layout.addWidget(card)

        # Footer
        footer_label = QLabel("Electronics Store Management System v0.1")
        footer_label.setObjectName("footerLabel")
        footer_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(footer_label)

    def _toggle_password_visibility(self) -> None:
        """Toggle between password and plain text echo mode."""
        if self.txt_password.echoMode() == QLineEdit.EchoMode.Password:
            self.txt_password.setEchoMode(QLineEdit.EchoMode.Normal)
            self.toggle_pass_action.setText("🔒")
        else:
            self.txt_password.setEchoMode(QLineEdit.EchoMode.Password)
            self.toggle_pass_action.setText("👁")

    def _show_error(self, message: str) -> None:
        """Display error banner."""
        self.error_banner.setText(f"⚠️ {message}")
        self.error_banner.show()

    def _clear_error(self) -> None:
        """Hide error banner."""
        if self.error_banner.isVisible():
            self.error_banner.setText("")
            self.error_banner.hide()

    def _on_login_clicked(self) -> None:
        """Handle login submission."""
        self._clear_error()
        username = self.txt_username.text().strip()
        password = self.txt_password.text()

        if not username and not password:
            self._show_error("Please enter your username and password.")
            self.txt_username.setFocus()
            return
        if not username:
            self._show_error("Please enter your username.")
            self.txt_username.setFocus()
            return
        if not password:
            self._show_error("Please enter your password.")
            self.txt_password.setFocus()
            return

        self.btn_login.setEnabled(False)
        self.btn_login.setText("Signing in...")

        success, user, message = self.auth_service.authenticate(username, password)

        self.btn_login.setEnabled(True)
        self.btn_login.setText("Sign In")

        if not success or user is None:
            self._show_error(message)
            self.txt_password.selectAll()
            self.txt_password.setFocus()
            return

        # Login successful
        self.login_successful.emit(user)
        self.close()

    def clear_inputs(self) -> None:
        """Reset inputs for clean re-login."""
        self.txt_username.clear()
        self.txt_password.clear()
        self._clear_error()
        self.txt_username.setFocus()
