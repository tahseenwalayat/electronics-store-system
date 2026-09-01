"""
Customer Management / Add Customer Dialog.
"""

from typing import Optional, Dict, Any
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QGridLayout,
    QLabel,
    QLineEdit,
    QDoubleSpinBox,
    QTextEdit,
    QDialogButtonBox,
    QMessageBox,
    QGroupBox,
)
from business.partner_service import PartnerService
from business.permissions import check_permission


class CustomerDialog(QDialog):
    """
    Dialog to register or edit a customer.
    """

    def __init__(self, partner_service: PartnerService, customer_data: Optional[Dict[str, Any]] = None, parent=None):
        super().__init__(parent)
        self.partner_service = partner_service
        self.customer_data = customer_data
        self.is_edit = customer_data is not None

        title = f"Edit Customer: {customer_data.get('name', '')}" if self.is_edit else "Add New Customer"
        self.setWindowTitle(f"{title} — Electronics Store System")
        self.resize(460, 440)

        self._setup_ui()
        if self.is_edit:
            self._load_data()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(12)

        group = QGroupBox("Customer Details")
        group.setStyleSheet("QGroupBox { font-weight: bold; color: #0f172a; }")
        grid = QGridLayout(group)
        grid.setSpacing(10)

        # Name
        grid.addWidget(QLabel("Full Name *"), 0, 0)
        self.txt_name = QLineEdit()
        self.txt_name.setPlaceholderText("e.g. Michael Chang")
        grid.addWidget(self.txt_name, 0, 1)

        # Phone
        grid.addWidget(QLabel("Phone Number"), 1, 0)
        self.txt_phone = QLineEdit()
        self.txt_phone.setPlaceholderText("+1 555-0123")
        grid.addWidget(self.txt_phone, 1, 1)

        # Email
        grid.addWidget(QLabel("Email Address"), 2, 0)
        self.txt_email = QLineEdit()
        self.txt_email.setPlaceholderText("michael.c@example.com")
        grid.addWidget(self.txt_email, 2, 1)

        # Credit Limit
        grid.addWidget(QLabel("Credit Limit ($)"), 3, 0)
        self.spn_limit = QDoubleSpinBox()
        self.spn_limit.setRange(0, 999999)
        self.spn_limit.setPrefix("$ ")
        self.spn_limit.setValue(1000.0)
        grid.addWidget(self.spn_limit, 3, 1)

        # Address
        grid.addWidget(QLabel("Address"), 4, 0)
        self.txt_address = QLineEdit()
        self.txt_address.setPlaceholderText("Street, City, State, ZIP")
        grid.addWidget(self.txt_address, 4, 1)

        # Notes
        grid.addWidget(QLabel("Notes"), 5, 0)
        self.txt_notes = QTextEdit()
        self.txt_notes.setPlaceholderText("Customer preferences, loyalty notes...")
        self.txt_notes.setFixedHeight(60)
        grid.addWidget(self.txt_notes, 5, 1)

        layout.addWidget(group)

        # Buttons
        btn_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        btn_box.button(QDialogButtonBox.StandardButton.Save).setText("Save Customer")
        btn_box.button(QDialogButtonBox.StandardButton.Save).setStyleSheet("background-color: #2563eb; color: white; padding: 6px 14px; font-weight: bold; border-radius: 4px;")
        btn_box.accepted.connect(self._on_save_clicked)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)

    def _load_data(self) -> None:
        c = self.customer_data
        self.txt_name.setText(c.get("name", ""))
        self.txt_phone.setText(c.get("phone", "") or "")
        self.txt_email.setText(c.get("email", "") or "")
        self.txt_address.setText(c.get("address", "") or "")
        self.spn_limit.setValue(float(c.get("credit_limit", 0.0)))
        self.txt_notes.setPlainText(c.get("notes", "") or "")

    def _on_save_clicked(self) -> None:
        if not check_permission("customers.manage", parent=self, action_name="save customer profiles"):
            return

        name = self.txt_name.text().strip()
        if not name:
            QMessageBox.warning(self, "Validation Error", "Customer Name is required.")
            self.txt_name.setFocus()
            return

        success, cid, msg = self.partner_service.create_customer(
            name=name,
            phone=self.txt_phone.text().strip() or None,
            email=self.txt_email.text().strip() or None,
            address=self.txt_address.text().strip() or None,
            credit_limit=self.spn_limit.value(),
            notes=self.txt_notes.toPlainText().strip() or None,
        )

        if not success:
            QMessageBox.critical(self, "Error", msg)
            return

        QMessageBox.information(self, "Success", f"Customer <b>'{name}'</b> saved successfully!")
        self.accept()
