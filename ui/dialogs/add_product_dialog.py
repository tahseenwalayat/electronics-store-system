"""
Dialog for Adding or Editing Products.
Fields: Product Name, Brand (dropdown), Model, Category (dropdown),
Minimum Stock Level, Warranty Duration (months), Current Stock (read-only, system-managed).
Excludes: SKU, barcode, product code, default purchase/sale price fields.
"""

from typing import Optional, Dict, Any
from PySide6.QtWidgets import (
    QDialog,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QLabel,
    QLineEdit,
    QSpinBox,
    QComboBox,
    QDialogButtonBox,
    QMessageBox,
    QGroupBox,
    QFrame,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QColor

from business.product_service import ProductService
from business.permissions import check_permission


class AddProductDialog(QDialog):
    """
    Dialog to add a new product or edit an existing one with strict field compliance.
    """

    def __init__(self, product_service: ProductService, product_data: Optional[Dict[str, Any]] = None, parent=None):
        super().__init__(parent)
        self.product_service = product_service
        self.product_data = product_data
        self.is_edit_mode = product_data is not None

        title = f"Edit Product: {product_data.get('name', '')}" if self.is_edit_mode else "Add New Product"
        self.setWindowTitle(f"{title} — Electronics Store System")
        self.resize(520, 460)
        self.setMinimumSize(460, 400)

        self._setup_ui()
        self._load_categories_and_brands()
        if self.is_edit_mode:
            self._load_product_data()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 20, 22, 20)
        layout.setSpacing(16)

        # Form Group
        group = QGroupBox("Product Details")
        group.setStyleSheet("QGroupBox { font-weight: bold; color: #0f172a; font-size: 13px; }")
        grid = QGridLayout(group)
        grid.setSpacing(12)
        grid.setContentsMargins(14, 16, 14, 16)

        # 1. Product Name (Required)
        grid.addWidget(QLabel("Product Name *"), 0, 0)
        self.txt_name = QLineEdit()
        self.txt_name.setPlaceholderText("e.g. Samsung Galaxy Smartphone, Apple MacBook Air")
        grid.addWidget(self.txt_name, 0, 1)

        # 2. Brand (Dropdown)
        grid.addWidget(QLabel("Brand"), 1, 0)
        self.cmb_brand = QComboBox()
        self.cmb_brand.addItem("— None / Generic —", None)
        grid.addWidget(self.cmb_brand, 1, 1)

        # 3. Model
        grid.addWidget(QLabel("Model"), 2, 0)
        self.txt_model = QLineEdit()
        self.txt_model.setPlaceholderText("e.g. S24 Ultra 256GB, M3 15-inch, WH-1000XM5")
        grid.addWidget(self.txt_model, 2, 1)

        # 4. Category (Dropdown)
        grid.addWidget(QLabel("Category"), 3, 0)
        self.cmb_category = QComboBox()
        self.cmb_category.addItem("— None / General —", None)
        grid.addWidget(self.cmb_category, 3, 1)

        # 5. Minimum Stock Level
        grid.addWidget(QLabel("Minimum Stock Level *"), 4, 0)
        self.spn_min_stock = QSpinBox()
        self.spn_min_stock.setRange(0, 99999)
        self.spn_min_stock.setValue(5)
        self.spn_min_stock.setSuffix(" units")
        grid.addWidget(self.spn_min_stock, 4, 1)

        # 6. Warranty Duration (months)
        grid.addWidget(QLabel("Warranty Duration *"), 5, 0)
        self.spn_warranty = QSpinBox()
        self.spn_warranty.setRange(0, 120)
        self.spn_warranty.setValue(12)
        self.spn_warranty.setSuffix(" months")
        grid.addWidget(self.spn_warranty, 5, 1)

        # 7. Current Stock (Read-Only, System-Managed)
        grid.addWidget(QLabel("Current Stock"), 6, 0)
        stock_container = QWidget()
        stock_layout = QVBoxLayout(stock_container)
        stock_layout.setContentsMargins(0, 0, 0, 0)
        stock_layout.setSpacing(2)

        self.txt_current_stock = QLineEdit()
        self.txt_current_stock.setReadOnly(True)
        self.txt_current_stock.setEnabled(False)
        self.txt_current_stock.setText("0 units (New Product)")
        self.txt_current_stock.setStyleSheet("""
            QLineEdit {
                background-color: #f1f5f9;
                color: #475569;
                font-weight: bold;
                border: 1px solid #cbd5e1;
                border-radius: 4px;
                padding: 4px 8px;
            }
        """)
        stock_layout.addWidget(self.txt_current_stock)

        lbl_stock_hint = QLabel("🔒 Read-only (System-managed: updated via Purchases and Sales)")
        lbl_stock_hint.setStyleSheet("color: #64748b; font-size: 11px; font-style: italic;")
        stock_layout.addWidget(lbl_stock_hint)

        grid.addWidget(stock_container, 6, 1)

        layout.addWidget(group)

        # Dialog Buttons
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        btn_save = button_box.button(QDialogButtonBox.StandardButton.Save)
        btn_save.setText("Save Product")
        btn_save.setStyleSheet("""
            background-color: #2563eb; color: white; padding: 6px 18px; border-radius: 4px; font-weight: bold;
        """)
        button_box.accepted.connect(self._on_save_clicked)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def _load_categories_and_brands(self) -> None:
        """Populate category and brand dropdowns from database."""
        categories = self.product_service.get_all_categories()
        for cat in categories:
            self.cmb_category.addItem(cat["name"], cat["id"])

        brands = self.product_service.get_all_brands()
        for b in brands:
            self.cmb_brand.addItem(b["name"], b["id"])

    def _load_product_data(self) -> None:
        """Populate form fields with existing product data in Edit mode."""
        if not self.product_data:
            return
        p = self.product_data
        self.txt_name.setText(p.get("name", ""))
        self.txt_model.setText(p.get("model", "") or "")
        self.spn_min_stock.setValue(int(p.get("min_stock_alert", 5)))
        self.spn_warranty.setValue(int(p.get("warranty_period_months", 0)))

        # Current stock display
        stock = int(p.get("current_stock", 0))
        self.txt_current_stock.setText(f"{stock} units in stock")

        cat_id = p.get("category_id")
        if cat_id:
            idx = self.cmb_category.findData(cat_id)
            if idx >= 0:
                self.cmb_category.setCurrentIndex(idx)

        brand_id = p.get("brand_id")
        if brand_id:
            idx = self.cmb_brand.findData(brand_id)
            if idx >= 0:
                self.cmb_brand.setCurrentIndex(idx)

    def _on_save_clicked(self) -> None:
        """Validate and submit product."""
        if not check_permission("products.manage", parent=self, action_name="save products"):
            return

        name = self.txt_name.text().strip()
        brand_id = self.cmb_brand.currentData()
        model = self.txt_model.text().strip() or None
        category_id = self.cmb_category.currentData()
        min_stock = self.spn_min_stock.value()
        warranty_months = self.spn_warranty.value()

        if not name:
            QMessageBox.warning(self, "Validation Error", "Product Name is required.")
            self.txt_name.setFocus()
            return

        if not self.is_edit_mode:
            success, new_id, msg = self.product_service.create_product(
                name=name,
                brand_id=brand_id,
                model=model,
                category_id=category_id,
                min_stock_alert=min_stock,
                warranty_period_months=warranty_months,
            )
            if not success:
                QMessageBox.critical(self, "Error Creating Product", msg)
                return
            QMessageBox.information(self, "Success", msg)
            self.accept()
        else:
            product_id = self.product_data["id"]
            success, msg = self.product_service.update_product(
                product_id=product_id,
                name=name,
                brand_id=brand_id,
                model=model,
                category_id=category_id,
                min_stock_alert=min_stock,
                warranty_period_months=warranty_months,
            )
            if not success:
                QMessageBox.critical(self, "Error Updating Product", msg)
                return
            QMessageBox.information(self, "Success", msg)
            self.accept()
