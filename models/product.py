"""
Product, Category, and Brand Domain Models.
"""

from dataclasses import dataclass
from typing import Optional
from datetime import datetime


@dataclass
class Category:
    id: int
    name: str
    description: Optional[str] = None
    parent_id: Optional[int] = None
    is_active: bool = True


@dataclass
class Brand:
    id: int
    name: str
    description: Optional[str] = None
    website: Optional[str] = None
    is_active: bool = True


@dataclass
class Product:
    """
    Product Domain Model.
    Fields: Product Name, Brand, Model, Category, Minimum Stock Level, Warranty Duration, Current Stock.
    """
    id: int
    name: str
    brand_id: Optional[int] = None
    brand_name: Optional[str] = None
    model: Optional[str] = None
    category_id: Optional[int] = None
    category_name: Optional[str] = None
    min_stock_alert: int = 5
    warranty_period_months: int = 0
    current_stock: int = 0
    is_active: bool = True
    is_deleted: bool = False
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @property
    def is_low_stock(self) -> bool:
        """Visual low stock trigger: current_stock <= minimum_stock and > 0."""
        return 0 < self.current_stock <= self.min_stock_alert

    @property
    def is_out_of_stock(self) -> bool:
        """Out of stock trigger: current_stock <= 0."""
        return self.current_stock <= 0

    @property
    def stock_status_label(self) -> str:
        """Human-readable stock status indicator."""
        if self.current_stock <= 0:
            return "Out of Stock"
        elif self.current_stock <= self.min_stock_alert:
            return "Low Stock"
        return "In Stock"
