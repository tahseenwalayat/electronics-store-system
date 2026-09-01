"""
Brand Management Dialog.
Provides listing, creation, editing, and safe deletion with product orphan prevention.
"""

from typing import Optional, Dict, Any, List
from PySide6.QtWidgets import (
    QDialog,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QLabel,
    QLineEdit,
    QTextEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QMessageBox,
    QDialogButtonBox,
    QGroupBox,
    QFrame,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QColor

from business.product_service import ProductService
from business.permissions import check_permission, can_manage


class AddEditBrandDialog(QDialog):
    """
    Form dialog to create or edit a manufacturer brand.
    """

    def __init__(self, product_service: ProductService, brand_data: Optional[Dict[str, Any]] = None, parent=None):
        super().__init__(parent)
        self.product_service = product_service
        self.brand_data = brand_data
        self.is_edit = brand_data is not None

        title = f"Edit Brand: {brand_data.get('name', '')}" if self.is_edit else "Add New Brand"
        self.setWindowTitle(f"{title} — Electronics Store System")
        self.resize(460, 360)
        self.setMinimumSize(400, 300)

        self._setup_ui()
        if self.is_edit:
            self._load_data()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(14)

        group = QGroupBox("Brand Information")
        group.setStyleSheet("QGroupBox { font-weight: bold; color: #0f172a; font-size: 13px; }")
        grid = QGridLayout(group)
        grid.setSpacing(12)

        # Name
        grid.addWidget(QLabel("Brand Name *"), 0, 0)
        self.txt_name = QLineEdit()
        self.txt_name.setPlaceholderText("e.g. Sony, Apple, Samsung, ASUS")
        grid.addWidget(self.txt_name, 0, 1)

        # Website
        grid.addWidget(QLabel("Website / URL"), 1, 0)
        self.txt_website = QLineEdit()
        self.txt_website.setPlaceholderText("https://brand.com")
        grid.addWidget(self.txt_website, 1, 1)

        # Description
        grid.addWidget(QLabel("Description"), 2, 0, Qt.AlignmentFlag.AlignTop)
        self.txt_desc = QTextEdit()
        self.txt_desc.setPlaceholderText("Enter brand history, vendor profile, warranty notes...")
        self.txt_desc.setFixedHeight(85)
        grid.addWidget(self.txt_desc, 2, 1)

        layout.addWidget(group)

        # Buttons
        btn_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        btn_box.button(QDialogButtonBox.StandardButton.Save).setText("Save Brand")
        btn_box.button(QDialogButtonBox.StandardButton.Save).setStyleSheet("""
            background-color: #2563eb; color: white; padding: 6px 16px; border-radius: 4px; font-weight: bold;
        """)
        btn_box.accepted.connect(self._on_save)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)

    def _load_data(self) -> None:
        if not self.brand_data:
            return
        self.txt_name.setText(self.brand_data.get("name", ""))
        self.txt_website.setText(self.brand_data.get("website", "") or "")
        self.txt_desc.setPlainText(self.brand_data.get("description", "") or "")

    def _on_save(self) -> None:
        if not check_permission("products.manage", parent=self, action_name="manage brands"):
            return

        name = self.txt_name.text().strip()
        website = self.txt_website.text().strip() or None
        desc = self.txt_desc.toPlainText().strip() or None

        if not name:
            QMessageBox.warning(self, "Validation Error", "Brand Name is required.")
            self.txt_name.setFocus()
            return

        if not self.is_edit:
            success, new_id, msg = self.product_service.create_brand(name, desc, website)
            if not success:
                QMessageBox.critical(self, "Error Creating Brand", msg)
                return
            QMessageBox.information(self, "Success", msg)
            self.accept()
        else:
            brand_id = self.brand_data["id"]
            success, msg = self.product_service.update_brand(brand_id, name, desc, website)
            if not success:
                QMessageBox.critical(self, "Error Updating Brand", msg)
                return
            QMessageBox.information(self, "Success", msg)
            self.accept()


class BrandManagementDialog(QDialog):
    """
    Full Brand Management Modal Screen with Live List and CRUD controls.
    """

    brands_changed = Signal()

    def __init__(self, product_service: Optional[ProductService] = None, parent=None):
        super().__init__(parent)
        self.product_service = product_service or ProductService()

        self.setWindowTitle("Brand Management — Electronics Store System")
        self.resize(800, 520)
        self.setMinimumSize(680, 420)

        self._setup_ui()
        self.load_brands()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(14)

        # Header
        top_bar = QHBoxLayout()
        header_layout = QVBoxLayout()
        lbl_title = QLabel("🏢 Brand & Manufacturer Management")
        lbl_title.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        lbl_title.setStyleSheet("color: #0f172a;")
        lbl_subtitle = QLabel("Manage hardware manufacturers, official partner brands, and official websites.")
        lbl_subtitle.setStyleSheet("color: #64748b; font-size: 12px;")
        header_layout.addWidget(lbl_title)
        header_layout.addWidget(lbl_subtitle)
        top_bar.addLayout(header_layout)

        top_bar.addStretch()

        self.btn_add = QPushButton("+ Add Brand")
        self.btn_add.setStyleSheet("""
            background-color: #2563eb; color: white; padding: 8px 16px; border-radius: 6px; font-weight: bold; font-size: 13px;
        """)
        self.btn_add.clicked.connect(self._open_add_brand)
        top_bar.addWidget(self.btn_add)

        layout.addLayout(top_bar)

        # Search Bar
        search_bar = QHBoxLayout()
        self.txt_search = QLineEdit()
        self.txt_search.setPlaceholderText("🔍 Search brands by name, website, description...")
        self.txt_search.setFixedHeight(34)
        self.txt_search.textChanged.connect(self._filter_brands)
        search_bar.addWidget(self.txt_search, stretch=3)

        self.btn_refresh = QPushButton("↻ Refresh")
        self.btn_refresh.setFixedHeight(34)
        self.btn_refresh.clicked.connect(self.load_brands)
        search_bar.addWidget(self.btn_refresh)

        layout.addLayout(search_bar)

        # Brands Table
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["Brand Name", "Website", "Description", "Products Assigned", "Actions"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(4, 140)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self.table)

        # Close button at bottom
        bottom_bar = QHBoxLayout()
        self.lbl_count = QLabel("0 brands")
        self.lbl_count.setStyleSheet("color: #64748b; font-size: 12px;")
        bottom_bar.addWidget(self.lbl_count)

        bottom_bar.addStretch()

        btn_close = QPushButton("Close")
        btn_close.setFixedHeight(32)
        btn_close.clicked.connect(self.accept)
        bottom_bar.addWidget(btn_close)

        layout.addLayout(bottom_bar)

    def load_brands(self) -> None:
        """Fetch brands with product counts."""
        self.raw_brands = self.product_service.get_all_brands_with_counts()
        self._filter_brands()

    def _filter_brands(self) -> None:
        query = self.txt_search.text().strip().lower()
        filtered = []
        for b in getattr(self, "raw_brands", []):
            if query:
                name_m = query in (b.get("name") or "").lower()
                web_m = query in (b.get("website") or "").lower()
                desc_m = query in (b.get("description") or "").lower()
                if not (name_m or web_m or desc_m):
                    continue
            filtered.append(b)

        self.table.setRowCount(len(filtered))
        self.lbl_count.setText(f"{len(filtered)} brands")

        can_edit = can_manage("products")

        for row_idx, b in enumerate(filtered):
            # Name
            name_item = QTableWidgetItem(b.get("name", ""))
            name_item.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
            self.table.setItem(row_idx, 0, name_item)

            # Website
            web_text = b.get("website") or "—"
            web_item = QTableWidgetItem(web_text)
            web_item.setForeground(QColor("#0284c7" if b.get("website") else "#94a3b8"))
            self.table.setItem(row_idx, 1, web_item)

            # Description
            desc_text = b.get("description") or "—"
            desc_item = QTableWidgetItem(desc_text)
            desc_item.setForeground(QColor("#475569"))
            self.table.setItem(row_idx, 2, desc_item)

            # Assigned Products Count
            p_count = b.get("product_count", 0)
            cnt_item = QTableWidgetItem(f"📦 {p_count} product(s)")
            cnt_item.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
            cnt_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            cnt_item.setForeground(QColor("#0284c7" if p_count > 0 else "#94a3b8"))
            self.table.setItem(row_idx, 3, cnt_item)

            # Actions widget
            action_widget = QWidget()
            action_layout = QHBoxLayout(action_widget)
            action_layout.setContentsMargins(4, 2, 4, 2)
            action_layout.setSpacing(6)

            # Edit Button
            btn_edit = QPushButton("Edit")
            btn_edit.setStyleSheet("background-color: #eff6ff; color: #1d4ed8; border: 1px solid #bfdbfe; border-radius: 4px; padding: 3px 8px; font-size: 11px;")
            btn_edit.setEnabled(can_edit)
            btn_edit.clicked.connect(lambda _, b_data=b: self._open_edit_brand(b_data))
            action_layout.addWidget(btn_edit)

            # Delete Button
            btn_del = QPushButton("Delete")
            btn_del.setStyleSheet("background-color: #fef2f2; color: #dc2626; border: 1px solid #fecaca; border-radius: 4px; padding: 3px 8px; font-size: 11px;")
            btn_del.setEnabled(can_edit)
            btn_del.clicked.connect(lambda _, b_data=b: self._handle_delete_brand(b_data))
            action_layout.addWidget(btn_del)

            self.table.setCellWidget(row_idx, 4, action_widget)
            self.table.setRowHeight(row_idx, 38)

    def _open_add_brand(self) -> None:
        if not check_permission("products.manage", parent=self, action_name="add brands"):
            return
        dlg = AddEditBrandDialog(self.product_service, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.load_brands()
            self.brands_changed.emit()

    def _open_edit_brand(self, brand_data: Dict[str, Any]) -> None:
        if not check_permission("products.manage", parent=self, action_name="edit brands"):
            return
        dlg = AddEditBrandDialog(self.product_service, brand_data=brand_data, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.load_brands()
            self.brands_changed.emit()

    def _handle_delete_brand(self, brand_data: Dict[str, Any]) -> None:
        """
        Attempt to delete a brand.
        If brand is assigned to products, deleting is blocked with a clear warning dialog.
        """
        if not check_permission("products.manage", parent=self, action_name="delete brands"):
            return

        brand_id = brand_data["id"]
        brand_name = brand_data["name"]

        reply = QMessageBox.question(
            self,
            "Confirm Delete",
            f"Are you sure you want to delete brand '<b>{brand_name}</b>'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        success, msg = self.product_service.delete_brand(brand_id)
        if not success:
            # Blocked with clear message
            QMessageBox.warning(self, "Brand In Use — Cannot Delete", msg)
        else:
            QMessageBox.information(self, "Brand Deleted", msg)
            self.load_brands()
            self.brands_changed.emit()
