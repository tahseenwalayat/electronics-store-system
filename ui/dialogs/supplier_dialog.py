"""
Supplier Management / Add Supplier Dialog.
"""

from typing import Optional, Dict, Any
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QGridLayout,
    QLabel,
    QLineEdit,
    QTextEdit,
    QDialogButtonBox,
    QMessageBox,
    QGroupBox,
)
from business.partner_service import PartnerService
from business.permissions import check_permission


class SupplierDialog(QDialog):
    """
    Dialog to register or edit a supplier/vendor profile.
    """

    def __init__(self, partner_service: PartnerService, supplier_data: Optional[Dict[str, Any]] = None, parent=None):
        super().__init__(parent)
        self.partner_service = partner_service
        self.supplier_data = supplier_data
        self.is_edit = supplier_data is not None

        title = f"Edit Supplier: {supplier_data.get('name', '')}" if self.is_edit else "Add New Supplier"
        self.setWindowTitle(f"{title} — Electronics Store System")
        self.resize(480, 460)

        self._setup_ui()
        if self.is_edit:
            self._load_data()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(12)

        group = QGroupBox("Supplier / Vendor Details")
        group.setStyleSheet("QGroupBox { font-weight: bold; color: #0f172a; }")
        grid = QGridLayout(group)
        grid.setSpacing(10)

        # Company Name
        grid.addWidget(QLabel("Supplier / Company Name *"), 0, 0)
        self.txt_name = QLineEdit()
        self.txt_name.setPlaceholderText("e.g. Silicon Logistics Direct")
        grid.addWidget(self.txt_name, 0, 1)

        # Contact Person
        grid.addWidget(QLabel("Contact Person"), 1, 0)
        self.txt_contact = QLineEdit()
        self.txt_contact.setPlaceholderText("e.g. Anita Patel")
        grid.addWidget(self.txt_contact, 1, 1)

        # Phone
        grid.addWidget(QLabel("Phone Number"), 2, 0)
        self.txt_phone = QLineEdit()
        self.txt_phone.setPlaceholderText("+1 800-555-0302")
        grid.addWidget(self.txt_phone, 2, 1)

        # Email
        grid.addWidget(QLabel("Email Address"), 3, 0)
        self.txt_email = QLineEdit()
        self.txt_email.setPlaceholderText("orders@siliconlogistics.com")
        grid.addWidget(self.txt_email, 3, 1)

        # Tax Number
        grid.addWidget(QLabel("Tax / VAT Number"), 4, 0)
        self.txt_tax = QLineEdit()
        self.txt_tax.setPlaceholderText("e.g. US-TAX-665544")
        grid.addWidget(self.txt_tax, 4, 1)

        # Address
        grid.addWidget(QLabel("Address"), 5, 0)
        self.txt_address = QLineEdit()
        self.txt_address.setPlaceholderText("e.g. 55 Supply Chain Blvd, Dallas, TX")
        grid.addWidget(self.txt_address, 5, 1)

        # Notes
        grid.addWidget(QLabel("Notes"), 6, 0)
        self.txt_notes = QTextEdit()
        self.txt_notes.setPlaceholderText("Delivery terms, lead times...")
        self.txt_notes.setFixedHeight(50)
        grid.addWidget(self.txt_notes, 6, 1)

        layout.addWidget(group)

        # Buttons
        btn_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        btn_box.button(QDialogButtonBox.StandardButton.Save).setText("Save Supplier")
        btn_box.button(QDialogButtonBox.StandardButton.Save).setStyleSheet("background-color: #2563eb; color: white; padding: 6px 14px; font-weight: bold; border-radius: 4px;")
        btn_box.accepted.connect(self._on_save_clicked)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)

    def _load_data(self) -> None:
        s = self.supplier_data
        self.txt_name.setText(s.get("name", ""))
        self.txt_contact.setText(s.get("contact_person", "") or "")
        self.txt_phone.setText(s.get("phone", "") or "")
        self.txt_email.setText(s.get("email", "") or "")
        self.txt_tax.setText(s.get("tax_number", "") or "")
        self.txt_address.setText(s.get("address", "") or "")
        self.txt_notes.setPlainText(s.get("notes", "") or "")

    def _on_save_clicked(self) -> None:
        if not check_permission("suppliers.manage", parent=self, action_name="save supplier details"):
            return

        name = self.txt_name.text().strip()
        if not name:
            QMessageBox.warning(self, "Validation Error", "Supplier Name is required.")
            self.txt_name.setFocus()
            return

        success, sid, msg = self.partner_service.create_supplier(
            name=name,
            contact_person=self.txt_contact.text().strip() or None,
            phone=self.txt_phone.text().strip() or None,
            email=self.txt_email.text().strip() or None,
            address=self.txt_address.text().strip() or None,
            tax_number=self.txt_tax.text().strip() or None,
            notes=self.txt_notes.toPlainText().strip() or None,
        )

        if not success:
            QMessageBox.critical(self, "Error", msg)
            return

        QMessageBox.information(self, "Success", f"Supplier <b>'{name}'</b> saved successfully!")
        self.accept()
