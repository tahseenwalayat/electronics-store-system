"""
Store Settings and Configuration View.
"""

from typing import Optional, Dict, Any
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QLabel,
    QLineEdit,
    QDoubleSpinBox,
    QPushButton,
    QFrame,
    QGroupBox,
    QMessageBox,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from data.db import get_db
from business.permissions import check_permission, can_manage


class SettingsView(QWidget):
    """
    Store Settings & Global Configuration Screen.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.db = get_db()
        self._setup_ui()
        self.load_settings()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)

        # Header
        top_bar = QHBoxLayout()
        header_layout = QVBoxLayout()
        lbl_title = QLabel("⚙️ Store Settings & Configuration")
        lbl_title.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        lbl_title.setStyleSheet("color: #0f172a;")
        lbl_subtitle = QLabel("Configure store profile, default sales tax rate, currency symbol, and receipt details.")
        lbl_subtitle.setStyleSheet("color: #64748b; font-size: 12px;")
        header_layout.addWidget(lbl_title)
        header_layout.addWidget(lbl_subtitle)
        top_bar.addLayout(header_layout)

        top_bar.addStretch()

        self.btn_save = QPushButton("💾 Save Settings")
        self.btn_save.setStyleSheet("""
            background-color: #2563eb; color: white; padding: 8px 18px; border-radius: 6px; font-weight: bold; font-size: 13px;
        """)
        self.btn_save.clicked.connect(self._save_settings)
        top_bar.addWidget(self.btn_save)

        layout.addLayout(top_bar)

        # Form Card
        group = QGroupBox("Store Profile & Financial Settings")
        group.setStyleSheet("QGroupBox { font-weight: bold; color: #0f172a; font-size: 13px; }")
        grid = QGridLayout(group)
        grid.setSpacing(12)

        # Store Name
        grid.addWidget(QLabel("Store / Business Name *"), 0, 0)
        self.txt_store_name = QLineEdit()
        grid.addWidget(self.txt_store_name, 0, 1)

        # Physical Address
        grid.addWidget(QLabel("Store Physical Address"), 1, 0)
        self.txt_address = QLineEdit()
        grid.addWidget(self.txt_address, 1, 1)

        # Phone Number
        grid.addWidget(QLabel("Contact Phone"), 2, 0)
        self.txt_phone = QLineEdit()
        grid.addWidget(self.txt_phone, 2, 1)

        # Email
        grid.addWidget(QLabel("Contact Email"), 3, 0)
        self.txt_email = QLineEdit()
        grid.addWidget(self.txt_email, 3, 1)

        # Default Sales Tax Rate (%)
        grid.addWidget(QLabel("Sales Tax Rate (%) *"), 4, 0)
        self.spn_tax = QDoubleSpinBox()
        self.spn_tax.setRange(0.0, 100.0)
        self.spn_tax.setDecimals(2)
        self.spn_tax.setSuffix(" %")
        grid.addWidget(self.spn_tax, 4, 1)

        # Currency Symbol
        grid.addWidget(QLabel("Currency Symbol"), 5, 0)
        self.txt_currency = QLineEdit()
        self.txt_currency.setPlaceholderText("$")
        grid.addWidget(self.txt_currency, 5, 1)

        layout.addWidget(group)

        # Catalog & Brand Group
        cat_group = QGroupBox("Product Catalog & Taxonomy")
        cat_group.setStyleSheet("QGroupBox { font-weight: bold; color: #0f172a; font-size: 13px; }")
        cat_layout = QHBoxLayout(cat_group)
        cat_layout.setSpacing(12)

        lbl_cat_desc = QLabel("Configure product categories, classifications, and manufacturer brand profiles:")
        lbl_cat_desc.setStyleSheet("color: #475569; font-weight: normal; font-size: 12px;")
        cat_layout.addWidget(lbl_cat_desc)

        cat_layout.addStretch()

        btn_manage_cat = QPushButton("🏷️ Manage Categories")
        btn_manage_cat.setStyleSheet("""
            background-color: #f1f5f9; color: #0f172a; border: 1px solid #cbd5e1; padding: 7px 14px; border-radius: 6px; font-weight: 600;
        """)
        btn_manage_cat.clicked.connect(self._open_category_management)
        cat_layout.addWidget(btn_manage_cat)

        btn_manage_brand = QPushButton("🏢 Manage Brands")
        btn_manage_brand.setStyleSheet("""
            background-color: #f1f5f9; color: #0f172a; border: 1px solid #cbd5e1; padding: 7px 14px; border-radius: 6px; font-weight: 600;
        """)
        btn_manage_brand.clicked.connect(self._open_brand_management)
        cat_layout.addWidget(btn_manage_brand)

        layout.addWidget(cat_group)
        layout.addStretch()

    def _open_category_management(self) -> None:
        from ui.dialogs.category_dialog import CategoryManagementDialog
        dlg = CategoryManagementDialog(parent=self)
        dlg.exec()

    def _open_brand_management(self) -> None:
        from ui.dialogs.brand_dialog import BrandManagementDialog
        dlg = BrandManagementDialog(parent=self)
        dlg.exec()

    def load_settings(self) -> None:
        """Load settings from DB."""
        sql = "SELECT setting_key, setting_value FROM store_settings;"
        try:
            rows = self.db.execute_query(sql)
            settings_map = {r["setting_key"]: r["setting_value"] for r in rows}
            self.txt_store_name.setText(settings_map.get("store_name", "ElectraStore Pro"))
            self.txt_address.setText(settings_map.get("store_address", ""))
            self.txt_phone.setText(settings_map.get("store_phone", ""))
            self.txt_email.setText(settings_map.get("store_email", ""))
            self.spn_tax.setValue(float(settings_map.get("tax_rate", 8.5)))
            self.txt_currency.setText(settings_map.get("currency_symbol", "$"))
        except Exception:
            pass

    def _save_settings(self) -> None:
        """Persist settings to DB."""
        if not check_permission("settings.manage", parent=self, action_name="update store settings"):
            return

        settings_to_save = [
            ("store_name", self.txt_store_name.text().strip()),
            ("store_address", self.txt_address.text().strip()),
            ("store_phone", self.txt_phone.text().strip()),
            ("store_email", self.txt_email.text().strip()),
            ("tax_rate", str(self.spn_tax.value())),
            ("currency_symbol", self.txt_currency.text().strip() or "$"),
        ]

        try:
            for k, v in settings_to_save:
                sql = """
                    INSERT INTO store_settings (setting_key, setting_value)
                    VALUES (?, ?)
                    ON CONFLICT(setting_key) DO UPDATE SET setting_value = excluded.setting_value;
                """
                self.db.execute_update(sql, (k, v))
            QMessageBox.information(self, "Settings Saved", "Store settings updated successfully.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save settings: {e}")
