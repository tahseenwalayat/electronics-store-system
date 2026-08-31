"""
Electronics Store System
Main Application Entry Point & Flow Coordinator
"""

import sys
import logging
from PySide6.QtWidgets import QApplication
from data.db import DatabaseManager
from business.auth_service import AuthService
from business.session import AppSession, get_session
from ui.login_window import LoginWindow
from ui.setup_wizard import SetupWizardDialog
from ui.main_window import MainWindow


class AppController:
    """
    Coordinates application screens, lifecycle, authentication, and session state.
    """

    def __init__(self, app: QApplication):
        self.app = app
        self.logger = logging.getLogger("AppController")

        # Core services
        self.db_manager = DatabaseManager.get_instance()
        self.auth_service = AuthService(self.db_manager)
        self.session = get_session()

        # UI instances
        self.login_window: LoginWindow = None
        self.main_window: MainWindow = None

    def start(self) -> None:
        """Start application flow depending on initialization state."""
        # 1. Initialize Database & Run Migrations
        try:
            self.db_manager.init_database()
            self.logger.info("Database initialized.")
        except Exception as e:
            self.logger.error(f"Database initialization error: {e}", exc_info=True)

        # 2. Check if first-time setup is needed (no users in DB)
        if not self.auth_service.has_users():
            self.logger.info("No users found in database. Launching First-Time Setup Wizard.")
            self._show_setup_wizard()
        else:
            self.logger.info("User accounts exist. Launching Login screen.")
            self._show_login_window()

    def _show_setup_wizard(self) -> None:
        """Display the First-Time Setup Wizard dialog."""
        wizard = SetupWizardDialog(self.auth_service)
        wizard.setup_completed.connect(self._on_setup_completed)
        # If user cancels wizard without completing and no users exist, exit cleanly
        if wizard.exec() != SetupWizardDialog.DialogCode.Accepted:
            if not self.auth_service.has_users():
                self.logger.info("Setup wizard cancelled before completion. Exiting.")
                self.app.quit()

    def _on_setup_completed(self, user) -> None:
        """Handle setup completion."""
        self.logger.info(f"First-time setup completed for user '{user.username}'. Transitioning to Main Screen.")
        self._show_main_window()

    def _show_login_window(self) -> None:
        """Display the Login Window."""
        if not self.login_window:
            self.login_window = LoginWindow(self.auth_service)
            self.login_window.login_successful.connect(self._on_login_successful)

        self.login_window.clear_inputs()
        self.login_window.show()

    def _on_login_successful(self, user) -> None:
        """Handle successful user login."""
        self.logger.info(f"User '{user.username}' logged in. Opening Main Screen.")
        self._show_main_window()

    def _show_main_window(self) -> None:
        """Instantiate and show the Main Window."""
        if not self.main_window:
            self.main_window = MainWindow(db_manager=self.db_manager)
            self.main_window.logout_requested.connect(self._on_logout_requested)

        self.main_window.refresh_user_display()
        self.main_window.show()

    def _on_logout_requested(self) -> None:
        """Handle user sign out and return to login screen."""
        self.logger.info("User logged out. Returning to Login screen.")
        self._show_login_window()


def setup_logging() -> None:
    """Configure application logging."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def main() -> int:
    """Main application lifecycle."""
    setup_logging()
    logger = logging.getLogger("main")
    logger.info("Starting Electronics Store System...")

    app = QApplication(sys.argv)
    app.setApplicationName("Electronics Store System")
    app.setApplicationDisplayName("Electronics Store System")
    app.setOrganizationName("ElectronicsStore")

    controller = AppController(app)
    controller.start()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
