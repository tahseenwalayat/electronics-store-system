"""
Product Detail & Quick View Dialog.
"""

from typing import Dict, Any
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QLabel,
    QPushButton,
    QFrame,
    QGroupBox,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QColor


class ProductDetailDialog(QDialog):
    """
    Shows product overview: Name, Brand, Model, Category, Current Stock, Min Stock Level, and Warranty.
    """

    def __init__(self, product: Dict[str, Any], parent=None):
        super().__init__(parent)
        self.product = product
        self.setWindowTitle(f"Product Details: {product.get('name', 'Product')}")
        self.resize(480, 380)
        self.setMinimumSize(420, 320)
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        # Header Card
        header = QFrame()
        header.setStyleSheet("background-color: #f1f5f9; border-radius: 8px; padding: 14px;")
        h_layout = QVBoxLayout(header)
        h_layout.setSpacing(4)

        lbl_name = QLabel(self.product.get("name", ""))
        lbl_name.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        lbl_name.setStyleSheet("color: #0f172a;")
        lbl_name.setWordWrap(True)
        h_layout.addWidget(lbl_name)

        model_text = self.product.get("model") or "—"
        lbl_sub = QLabel(f"Model: <b>{model_text}</b> &bull; Brand: <b>{self.product.get('brand_name', '—')}</b>")
        lbl_sub.setStyleSheet("color: #475569; font-size: 12px;")
        h_layout.addWidget(lbl_sub)

        layout.addWidget(header)

        # Grid Details
        group = QGroupBox("Catalog & Stock Specifications")
        group.setStyleSheet("QGroupBox { font-weight: bold; color: #0f172a; font-size: 13px; }")
        grid = QGridLayout(group)
        grid.setSpacing(12)
        grid.setContentsMargins(14, 16, 14, 16)

        # Brand
        grid.addWidget(QLabel("Brand:"), 0, 0)
        lbl_brand = QLabel(f"<b>{self.product.get('brand_name', '—')}</b>")
        grid.addWidget(lbl_brand, 0, 1)

        # Category
        grid.addWidget(QLabel("Category:"), 0, 2)
        lbl_cat = QLabel(f"<b>{self.product.get('category_name', '—')}</b>")
        grid.addWidget(lbl_cat, 0, 3)

        # Model
        grid.addWidget(QLabel("Model:"), 1, 0)
        lbl_model = QLabel(f"<b>{model_text}</b>")
        grid.addWidget(lbl_model, 1, 1)

        # Warranty Duration
        warranty = int(self.product.get("warranty_period_months", 0))
        grid.addWidget(QLabel("Warranty:"), 1, 2)
        lbl_war = QLabel(f"🛡️ {warranty} Months" if warranty > 0 else "No Warranty")
        grid.addWidget(lbl_war, 1, 3)

        # Current Stock
        stock = int(self.product.get("current_stock", 0))
        min_alert = int(self.product.get("min_stock_alert", 5))

        grid.addWidget(QLabel("Current Stock:"), 2, 0)
        lbl_stk = QLabel(f"<b style='font-size: 13px;'>{stock} units</b>")
        grid.addWidget(lbl_stk, 2, 1)

        # Min Stock Level
        grid.addWidget(QLabel("Min Stock Level:"), 2, 2)
        lbl_alert = QLabel(f"{min_alert} units")
        lbl_alert.setStyleSheet("color: #64748b;")
        grid.addWidget(lbl_alert, 2, 3)

        # Visual Stock Status
        grid.addWidget(QLabel("Stock Status:"), 3, 0)
        status_lbl = self.product.get("status_label", "In Stock")
        lbl_stat = QLabel(f"<b>{status_lbl}</b>")
        if status_lbl == "In Stock":
            lbl_stat.setStyleSheet("color: #16a34a;")
        elif status_lbl == "Low Stock":
            lbl_stat.setStyleSheet("color: #d97706; font-weight: bold;")
        else:
            lbl_stat.setStyleSheet("color: #dc2626; font-weight: bold;")
        grid.addWidget(lbl_stat, 3, 1, 1, 3)

        layout.addWidget(group)
        layout.addStretch()

        # Close
        btn_close = QPushButton("Close")
        btn_close.setFixedHeight(34)
        btn_close.setStyleSheet("padding: 4px 18px;")
        btn_close.clicked.connect(self.accept)
        layout.addWidget(btn_close, alignment=Qt.AlignmentFlag.AlignRight)
