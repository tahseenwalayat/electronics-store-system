"""
Reports & Business Analytics View.
"""

from typing import Optional, Dict, Any
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QLabel,
    QPushButton,
    QFrame,
    QScrollArea,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QColor

from business.product_service import ProductService
from data.db import get_db


class ReportsView(QWidget):
    """
    Financial & Inventory Performance Analytics Dashboard.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.db = get_db()
        self.product_service = ProductService()

        self._setup_ui()
        self.load_analytics()

    def _setup_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 20, 24, 20)
        main_layout.setSpacing(16)

        # Header
        top_bar = QHBoxLayout()
        header_layout = QVBoxLayout()
        lbl_title = QLabel("📈 Reports & Business Analytics")
        lbl_title.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        lbl_title.setStyleSheet("color: #0f172a;")
        lbl_subtitle = QLabel("Overview of sales revenue, inventory valuation, stock health, and financial metrics.")
        lbl_subtitle.setStyleSheet("color: #64748b; font-size: 12px;")
        header_layout.addWidget(lbl_title)
        header_layout.addWidget(lbl_subtitle)
        top_bar.addLayout(header_layout)

        top_bar.addStretch()

        btn_refresh = QPushButton("↻ Refresh Analytics")
        btn_refresh.setStyleSheet("""
            background-color: #ffffff; color: #1e293b; border: 1px solid #cbd5e1; padding: 8px 16px; border-radius: 6px; font-weight: 600;
        """)
        btn_refresh.clicked.connect(self.load_analytics)
        top_bar.addWidget(btn_refresh)

        main_layout.addLayout(top_bar)

        # Scrollable Analytics Cards
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        container = QWidget()
        cards_layout = QVBoxLayout(container)
        cards_layout.setContentsMargins(0, 0, 0, 0)
        cards_layout.setSpacing(18)

        # 1. Financial Performance Grid
        fin_frame = QFrame()
        fin_frame.setStyleSheet("background-color: #ffffff; border: 1px solid #e2e8f0; border-radius: 10px; padding: 18px;")
        fin_grid = QGridLayout(fin_frame)
        fin_grid.setSpacing(14)

        lbl_fin_title = QLabel("💰 Financial Performance Overview")
        lbl_fin_title.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        lbl_fin_title.setStyleSheet("color: #0f172a; border: none;")
        fin_grid.addWidget(lbl_fin_title, 0, 0, 1, 3)

        self.card_rev = self._create_stat_card("Total Sales Revenue", "$0.00", "#16a34a", "Sum of completed invoices")
        fin_grid.addWidget(self.card_rev, 1, 0)

        self.card_tx_count = self._create_stat_card("Total Sales Transactions", "0", "#2563eb", "Count of invoice records")
        fin_grid.addWidget(self.card_tx_count, 1, 1)

        self.card_avg_ticket = self._create_stat_card("Average Ticket Size", "$0.00", "#0891b2", "Average revenue per transaction")
        fin_grid.addWidget(self.card_avg_ticket, 1, 2)

        cards_layout.addWidget(fin_frame)

        # 2. Inventory Valuation Grid
        inv_frame = QFrame()
        inv_frame.setStyleSheet("background-color: #ffffff; border: 1px solid #e2e8f0; border-radius: 10px; padding: 18px;")
        inv_grid = QGridLayout(inv_frame)
        inv_grid.setSpacing(14)

        lbl_inv_title = QLabel("📦 Inventory Valuation & Health")
        lbl_inv_title.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        lbl_inv_title.setStyleSheet("color: #0f172a; border: none;")
        inv_grid.addWidget(lbl_inv_title, 0, 0, 1, 3)

        self.card_inv_val = self._create_stat_card("Inventory Retail Value", "$0.00", "#7c3aed", "Selling price × current stock")
        inv_grid.addWidget(self.card_inv_val, 1, 0)

        self.card_inv_cost = self._create_stat_card("Inventory Total Cost", "$0.00", "#475569", "Cost price × current stock")
        inv_grid.addWidget(self.card_inv_cost, 1, 1)

        self.card_low_stock = self._create_stat_card("Low & Out of Stock Items", "0 items", "#d97706", "Items below alert thresholds")
        inv_grid.addWidget(self.card_low_stock, 1, 2)

        cards_layout.addWidget(inv_frame)

        cards_layout.addStretch()
        scroll.setWidget(container)
        main_layout.addWidget(scroll)

    def _create_stat_card(self, title: str, value: str, color: str, subtext: str) -> QFrame:
        card = QFrame()
        card.setStyleSheet("background-color: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 12px;")
        lay = QVBoxLayout(card)
        lay.setSpacing(4)

        t_lbl = QLabel(title)
        t_lbl.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        t_lbl.setStyleSheet("color: #475569; border: none;")
        lay.addWidget(t_lbl)

        v_lbl = QLabel(value)
        v_lbl.setFont(QFont("Segoe UI", 20, QFont.Weight.Bold))
        v_lbl.setStyleSheet(f"color: {color}; border: none;")
        v_lbl.setObjectName("valueLabel")
        lay.addWidget(v_lbl)

        s_lbl = QLabel(subtext)
        s_lbl.setFont(QFont("Segoe UI", 9))
        s_lbl.setStyleSheet("color: #94a3b8; border: none;")
        lay.addWidget(s_lbl)

        return card

    def load_analytics(self) -> None:
        """Query metrics from DB and refresh UI cards."""
        # 1. Sales Metrics
        sales_sql = """
            SELECT 
                COUNT(*) AS total_tx,
                COALESCE(SUM(total_amount), 0.0) AS total_rev,
                COALESCE(AVG(total_amount), 0.0) AS avg_ticket
            FROM sales
            WHERE status = 'completed';
        """
        try:
            s_row = self.db.execute_one(sales_sql)
            if s_row:
                self.card_rev.findChild(QLabel, "valueLabel").setText(f"${s_row['total_rev']:,.2f}")
                self.card_tx_count.findChild(QLabel, "valueLabel").setText(f"{s_row['total_tx']}")
                self.card_avg_ticket.findChild(QLabel, "valueLabel").setText(f"${s_row['avg_ticket']:,.2f}")
        except Exception:
            pass

        # 2. Inventory Metrics
        metrics = self.product_service.get_inventory_metrics()
        self.card_inv_val.findChild(QLabel, "valueLabel").setText(f"${metrics['total_inventory_value']:,.2f}")
        self.card_inv_cost.findChild(QLabel, "valueLabel").setText(f"${metrics['total_inventory_cost']:,.2f}")
        low_total = metrics["low_stock_count"] + metrics["out_of_stock_count"]
        self.card_low_stock.findChild(QLabel, "valueLabel").setText(f"{low_total} items")
