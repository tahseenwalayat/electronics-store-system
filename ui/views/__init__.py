"""
Module views package.
"""

from ui.views.products_view import ProductsCatalogView
from ui.views.sales_view import SalesView
from ui.views.purchases_view import PurchasesView
from ui.views.customers_view import CustomersView
from ui.views.suppliers_view import SuppliersView
from ui.views.returns_view import ReturnsView
from ui.views.warranty_view import WarrantyView
from ui.views.reports_view import ReportsView
from ui.views.backup_view import BackupRestoreView
from ui.views.settings_view import SettingsView

__all__ = [
    "ProductsCatalogView",
    "SalesView",
    "PurchasesView",
    "CustomersView",
    "SuppliersView",
    "ReturnsView",
    "WarrantyView",
    "ReportsView",
    "BackupRestoreView",
    "SettingsView",
]
