"""
Supplier Registration & Edit Dialog.
Supports fields: Supplier Name, Company/Shop Name, Phone Number, Address, Email, and Notes.
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
    QFrame,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from business.partner_service import PartnerService
from business.permissions import check_permission


class SupplierDialog(QDialog):
    """
    Dialog to register or edit a supplier/vendor profile.
    Fields: Supplier Name, Company/Shop Name, Phone Number, Address, Email.
    """

    def __init__(self, partner_service: PartnerService, supplier_data: Optional[Dict[str, Any]] = None, parent=None):
        super().__init__(parent)
        self.partner_service = partner_service
        self.supplier_data = supplier_data
        self.is_edit = supplier_data is not None

        title = f"Edit Supplier — {supplier_data.get('name', '')}" if self.is_edit else "Add New Supplier"
        self.setWindowTitle(f"{title} — Electronics Store System")
        self.resize(520, 480)
        self.setMinimumSize(460, 420)

        self._setup_ui()
        if self.is_edit:
            self._load_data()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 20, 22, 20)
        layout.setSpacing(14)

        # Header Info Card
        header_card = QFrame()
        header_card.setStyleSheet("background-color: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 10px;")
        h_lay = QVBoxLayout(header_card)
        h_lay.setContentsMargins(6, 4, 6, 4)
        h_lay.setSpacing(2)

        lbl_hdr = QLabel("🏢 " + ("Edit Supplier Profile" if self.is_edit else "Register New Supplier"))
        lbl_hdr.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        lbl_hdr.setStyleSheet("color: #0f172a;")
        h_lay.addWidget(lbl_hdr)

        lbl_sub = QLabel("Fill in wholesale supplier contacts, business company name, and shipping address.")
        lbl_sub.setStyleSheet("color: #64748b; font-size: 11px;")
        h_lay.addWidget(lbl_sub)
        layout.addWidget(header_card)

        # Form Group
        form_group = QGroupBox("Supplier Information")
        form_group.setStyleSheet("QGroupBox { font-weight: bold; color: #1e293b; font-size: 12px; }")
        grid = QGridLayout(form_group)
        grid.setContentsMargins(14, 16, 14, 14)
        grid.setHorizontalSpacing(14)
        grid.setVerticalSpacing(10)

        # 1. Company / Shop Name (Required)
        lbl_comp = QLabel("Company / Shop Name *")
        lbl_comp.setStyleSheet("font-weight: 600; color: #334155;")
        grid.addWidget(lbl_comp, 0, 0)
        self.txt_company = QLineEdit()
        self.txt_company.setPlaceholderText("e.g. Apex Electronics Wholesalers Ltd.")
        self.txt_company.setStyleSheet("padding: 6px; border: 1px solid #cbd5e1; border-radius: 5px;")
        grid.addWidget(self.txt_company, 0, 1)

        # 2. Supplier Name (Representative / Contact Person)
        lbl_rep = QLabel("Supplier Name")
        lbl_rep.setStyleSheet("font-weight: 600; color: #334155;")
        grid.addWidget(lbl_rep, 1, 0)
        self.txt_supplier_name = QLineEdit()
        self.txt_supplier_name.setPlaceholderText("e.g. John Doe / Account Manager")
        self.txt_supplier_name.setStyleSheet("padding: 6px; border: 1px solid #cbd5e1; border-radius: 5px;")
        grid.addWidget(self.txt_supplier_name, 1, 1)

        # 3. Phone Number
        lbl_phone = QLabel("Phone Number")
        lbl_phone.setStyleSheet("font-weight: 600; color: #334155;")
        grid.addWidget(lbl_phone, 2, 0)
        self.txt_phone = QLineEdit()
        self.txt_phone.setPlaceholderText("e.g. +1 (555) 234-5678")
        self.txt_phone.setStyleSheet("padding: 6px; border: 1px solid #cbd5e1; border-radius: 5px;")
        grid.addWidget(self.txt_phone, 2, 1)

        # 4. Email
        lbl_email = QLabel("Email")
        lbl_email.setStyleSheet("font-weight: 600; color: #334155;")
        grid.addWidget(lbl_email, 3, 0)
        self.txt_email = QLineEdit()
        self.txt_email.setPlaceholderText("e.g. supply@apexelectronics.com")
        self.txt_email.setStyleSheet("padding: 6px; border: 1px solid #cbd5e1; border-radius: 5px;")
        grid.addWidget(self.txt_email, 3, 1)

        # 5. Address
        lbl_addr = QLabel("Address")
        lbl_addr.setStyleSheet("font-weight: 600; color: #334155;")
        grid.addWidget(lbl_addr, 4, 0)
        self.txt_address = QLineEdit()
        self.txt_address.setPlaceholderText("e.g. 100 Logistics Park, Suite 400, Chicago, IL")
        self.txt_address.setStyleSheet("padding: 6px; border: 1px solid #cbd5e1; border-radius: 5px;")
        grid.addWidget(self.txt_address, 4, 1)

        # 6. Notes (Optional)
        lbl_notes = QLabel("Notes")
        lbl_notes.setStyleSheet("font-weight: 600; color: #334155;")
        grid.addWidget(lbl_notes, 5, 0, Qt.AlignmentFlag.AlignTop)
        self.txt_notes = QTextEdit()
        self.txt_notes.setPlaceholderText("Payment terms, distributor notes, delivery schedule...")
        self.txt_notes.setFixedHeight(60)
        self.txt_notes.setStyleSheet("border: 1px solid #cbd5e1; border-radius: 5px;")
        grid.addWidget(self.txt_notes, 5, 1)

        layout.addWidget(form_group)

        # Dialog Buttons
        btn_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        btn_save = btn_box.button(QDialogButtonBox.StandardButton.Save)
        btn_save.setText("💾 Save Supplier Profile" if self.is_edit else "➕ Add Supplier")
        btn_save.setStyleSheet("""
            QPushButton {
                background-color: #2563eb; color: white; padding: 7px 18px; font-weight: bold; border-radius: 5px; font-size: 13px;
            }
            QPushButton:hover {
                background-color: #1d4ed8;
            }
        """)

        btn_cancel = btn_box.button(QDialogButtonBox.StandardButton.Cancel)
        btn_cancel.setStyleSheet("background-color: #f1f5f9; color: #334155; padding: 7px 14px; border: 1px solid #cbd5e1; border-radius: 5px;")

        btn_box.accepted.connect(self._on_save_clicked)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)

    def _load_data(self) -> None:
        s = self.supplier_data or {}
        self.txt_company.setText(s.get("name", ""))
        self.txt_supplier_name.setText(s.get("contact_person", "") or "")
        self.txt_phone.setText(s.get("phone", "") or "")
        self.txt_email.setText(s.get("email", "") or "")
        self.txt_address.setText(s.get("address", "") or "")
        self.txt_notes.setPlainText(s.get("notes", "") or "")

    def _on_save_clicked(self) -> None:
        if not check_permission("suppliers.manage", parent=self, action_name="save supplier details"):
            return

        company_name = self.txt_company.text().strip()
        supplier_name = self.txt_supplier_name.text().strip() or None
        phone = self.txt_phone.text().strip() or None
        email = self.txt_email.text().strip() or None
        address = self.txt_address.text().strip() or None
        notes = self.txt_notes.toPlainText().strip() or None

        if not company_name:
            QMessageBox.warning(self, "Validation Error", "Company / Shop Name is required.")
            self.txt_company.setFocus()
            return

        if self.is_edit:
            supplier_id = self.supplier_data["id"]
            ok, msg = self.partner_service.update_supplier(
                supplier_id=supplier_id,
                name=company_name,
                contact_person=supplier_name,
                phone=phone,
                email=email,
                address=address,
                notes=notes,
            )
            if not ok:
                QMessageBox.critical(self, "Error Updating Supplier", msg)
                return
            QMessageBox.information(self, "Supplier Updated", f"Supplier <b>'{company_name}'</b> updated successfully!")
        else:
            ok, sid, msg = self.partner_service.create_supplier(
                name=company_name,
                contact_person=supplier_name,
                phone=phone,
                email=email,
                address=address,
                notes=notes,
            )
            if not ok:
                QMessageBox.critical(self, "Error Adding Supplier", msg)
                return
            QMessageBox.information(self, "Supplier Added", f"Supplier <b>'{company_name}'</b> added successfully!")

        self.accept()
