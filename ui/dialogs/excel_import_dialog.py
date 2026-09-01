"""
Excel Product Import Dialog with Live Validation & Preview Screen.
Allows user to select an .xlsx file, inspects valid vs error rows,
and confirms bulk-insert with auto-creation of missing Categories and Brands.
"""

import os
from typing import Optional, Dict, Any, List
from PySide6.QtWidgets import (
    QDialog,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QFileDialog,
    QMessageBox,
    QFrame,
    QComboBox,
    QProgressBar,
    QTabWidget,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QColor

from business.excel_import_service import ExcelImportService
from business.permissions import check_permission


class ExcelProductImportDialog(QDialog):
    """
    Dialog for selecting, validating, and committing bulk product imports from Excel (.xlsx).
    """

    import_completed = Signal(int)  # Emitted with imported count on success

    def __init__(self, parent=None):
        super().__init__(parent)
        self.import_service = ExcelImportService()
        self.parsed_data: Optional[Dict[str, Any]] = None

        self.setWindowTitle("📥 Import Products from Excel — Electronics Store System")
        self.resize(960, 640)
        self.setMinimumSize(850, 520)

        self._setup_ui()

    def _setup_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(22, 20, 22, 20)
        main_layout.setSpacing(14)

        # ---------------------------------------------------------------------
        # 1. FILE SELECTION BAR
        # ---------------------------------------------------------------------
        top_frame = QFrame()
        top_frame.setStyleSheet("""
            QFrame {
                background-color: #f8fafc;
                border: 1px solid #e2e8f0;
                border-radius: 8px;
                padding: 10px;
            }
        """)
        top_layout = QHBoxLayout(top_frame)
        top_layout.setContentsMargins(8, 4, 8, 4)
        top_layout.setSpacing(10)

        top_layout.addWidget(QLabel("<b>Excel File:</b>"))

        self.txt_filepath = QLineEdit()
        self.txt_filepath.setReadOnly(True)
        self.txt_filepath.setPlaceholderText("Select an .xlsx file containing product catalog...")
        self.txt_filepath.setStyleSheet("background-color: #ffffff; padding: 6px; border: 1px solid #cbd5e1; border-radius: 5px;")
        top_layout.addWidget(self.txt_filepath, stretch=1)

        self.btn_browse = QPushButton("📁 Browse File...")
        self.btn_browse.setStyleSheet("""
            background-color: #2563eb; color: white; padding: 7px 14px; border-radius: 5px; font-weight: 600;
        """)
        self.btn_browse.clicked.connect(self._on_browse_clicked)
        top_layout.addWidget(self.btn_browse)

        self.btn_template = QPushButton("📄 Template")
        self.btn_template.setToolTip("Download a blank Excel template formatted for product import")
        self.btn_template.setStyleSheet("""
            background-color: #ffffff; color: #1e293b; border: 1px solid #cbd5e1; padding: 7px 12px; border-radius: 5px; font-weight: 500;
        """)
        self.btn_template.clicked.connect(self._on_download_template_clicked)
        top_layout.addWidget(self.btn_template)

        main_layout.addWidget(top_frame)

        # ---------------------------------------------------------------------
        # 2. KPI METRIC SUMMARY CHIPS
        # ---------------------------------------------------------------------
        kpi_bar = QHBoxLayout()
        kpi_bar.setSpacing(12)

        # Total Rows
        self.card_total = self._create_kpi_card("📄 Total Rows", "0", "#0f172a")
        kpi_bar.addWidget(self.card_total)

        # Valid Rows
        self.card_valid = self._create_kpi_card("🟢 Ready to Import", "0", "#15803d")
        kpi_bar.addWidget(self.card_valid)

        # Error Rows
        self.card_errors = self._create_kpi_card("🔴 Rows with Errors", "0", "#b91c1c")
        kpi_bar.addWidget(self.card_errors)

        # New Categories
        self.card_cats = self._create_kpi_card("🏷️ New Categories", "0", "#4338ca")
        kpi_bar.addWidget(self.card_cats)

        # New Brands
        self.card_brands = self._create_kpi_card("🏢 New Brands", "0", "#0369a1")
        kpi_bar.addWidget(self.card_brands)

        main_layout.addLayout(kpi_bar)

        # ---------------------------------------------------------------------
        # 3. TABBED PREVIEW TABLES (Valid Rows vs. Error Rows)
        # ---------------------------------------------------------------------
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #e2e8f0;
                border-radius: 6px;
                background-color: #ffffff;
            }
            QTabBar::tab {
                background: #f1f5f9;
                color: #475569;
                font-weight: 600;
                padding: 8px 18px;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                margin-right: 4px;
            }
            QTabBar::tab:selected {
                background: #ffffff;
                color: #2563eb;
                border-bottom: 2px solid #2563eb;
            }
        """)

        # Tab 1: Valid Rows Table
        self.table_valid = QTableWidget()
        self.table_valid.setColumnCount(7)
        self.table_valid.setHorizontalHeaderLabels([
            "Excel Row", "Product Name", "Brand", "Model", "Category", "Min Stock", "Warranty"
        ])
        self.table_valid.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table_valid.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table_valid.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table_valid.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table_valid.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.table_valid.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        self.table_valid.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)
        self.table_valid.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table_valid.verticalHeader().setVisible(False)
        self.tabs.addTab(self.table_valid, "🟢 Valid Rows (0)")

        # Tab 2: Error Rows Table
        self.table_errors = QTableWidget()
        self.table_errors.setColumnCount(3)
        self.table_errors.setHorizontalHeaderLabels(["Excel Row", "Product Name", "Validation Error Reason"])
        self.table_errors.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table_errors.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table_errors.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table_errors.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table_errors.verticalHeader().setVisible(False)
        self.tabs.addTab(self.table_errors, "🔴 Rows with Errors (0)")

        main_layout.addWidget(self.tabs, stretch=1)

        # ---------------------------------------------------------------------
        # 4. BOTTOM ACTION BAR
        # ---------------------------------------------------------------------
        bottom_bar = QHBoxLayout()
        bottom_bar.setSpacing(12)

        self.lbl_info = QLabel("Please select an Excel (.xlsx) file to preview and validate products.")
        self.lbl_info.setStyleSheet("color: #64748b; font-size: 12px;")
        bottom_bar.addWidget(self.lbl_info, stretch=1)

        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.setStyleSheet("""
            background-color: #f1f5f9; color: #334155; border: 1px solid #cbd5e1; padding: 8px 18px; border-radius: 6px; font-weight: 600;
        """)
        self.btn_cancel.clicked.connect(self.reject)
        bottom_bar.addWidget(self.btn_cancel)

        self.btn_import = QPushButton("📥 Import Products")
        self.btn_import.setEnabled(False)
        self.btn_import.setStyleSheet("""
            QPushButton {
                background-color: #16a34a;
                color: #ffffff;
                border: none;
                padding: 8px 22px;
                border-radius: 6px;
                font-weight: bold;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #15803d;
            }
            QPushButton:disabled {
                background-color: #94a3b8;
                color: #f1f5f9;
            }
        """)
        self.btn_import.clicked.connect(self._on_import_clicked)
        bottom_bar.addWidget(self.btn_import)

        main_layout.addLayout(bottom_bar)

    def _create_kpi_card(self, title: str, initial_val: str, color_hex: str) -> QFrame:
        """Create a summary metric card."""
        card = QFrame()
        card.setStyleSheet("""
            QFrame {
                background-color: #ffffff;
                border: 1px solid #e2e8f0;
                border-radius: 8px;
                padding: 6px 12px;
            }
        """)
        lay = QVBoxLayout(card)
        lay.setContentsMargins(6, 4, 6, 4)
        lay.setSpacing(2)

        lbl_t = QLabel(title)
        lbl_t.setStyleSheet("color: #64748b; font-size: 11px; font-weight: 500;")
        lay.addWidget(lbl_t)

        lbl_v = QLabel(initial_val)
        lbl_v.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        lbl_v.setStyleSheet(f"color: {color_hex};")
        lay.addWidget(lbl_v)

        card.lbl_val = lbl_v  # store reference
        return card

    # -------------------------------------------------------------------------
    # ACTIONS & HANDLERS
    # -------------------------------------------------------------------------

    def _on_browse_clicked(self) -> None:
        """Prompt user for .xlsx file and execute parsing."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Product Excel File",
            "",
            "Excel Workbooks (*.xlsx);;All Files (*.*)",
        )
        if not file_path:
            return

        self.txt_filepath.setText(file_path)
        self._load_and_validate_file(file_path)

    def _load_and_validate_file(self, file_path: str) -> None:
        """Parse Excel file and update UI preview tables."""
        res = self.import_service.parse_excel(file_path)
        self.parsed_data = res

        if not res.get("success"):
            QMessageBox.critical(self, "Excel Parse Error", res.get("error", "Failed to parse file."))
            self._reset_preview()
            return

        total = res["total_rows"]
        val_count = res["valid_count"]
        err_count = res["error_count"]
        new_cats = res["new_categories"]
        new_brands = res["new_brands"]

        # Update KPI Cards
        self.card_total.lbl_val.setText(str(total))
        self.card_valid.lbl_val.setText(str(val_count))
        self.card_errors.lbl_val.setText(str(err_count))
        self.card_cats.lbl_val.setText(str(len(new_cats)))
        self.card_brands.lbl_val.setText(str(len(new_brands)))

        # Update Tabs Title
        self.tabs.setTabText(0, f"🟢 Valid Rows ({val_count})")
        self.tabs.setTabText(1, f"🔴 Rows with Errors ({err_count})")

        # Populate Valid Rows Table
        self._populate_valid_table(res["valid_rows"])

        # Populate Error Rows Table
        self._populate_error_table(res["error_rows"])

        # Update Import button
        if val_count > 0:
            self.btn_import.setEnabled(True)
            self.btn_import.setText(f"📥 Import {val_count} Valid Product(s)")
            self.lbl_info.setText(
                f"✅ Ready: <b>{val_count}</b> valid row(s) to import. "
                f"Auto-creating <b>{len(new_cats)}</b> new categories and <b>{len(new_brands)}</b> new brands."
            )
            # Switch to errors tab if there are errors and no valid rows
            if val_count == 0 and err_count > 0:
                self.tabs.setCurrentIndex(1)
            else:
                self.tabs.setCurrentIndex(0)
        else:
            self.btn_import.setEnabled(False)
            self.btn_import.setText("📥 Import Products")
            self.lbl_info.setText("❌ No valid rows found in the selected file.")
            self.tabs.setCurrentIndex(1 if err_count > 0 else 0)

    def _populate_valid_table(self, valid_rows: List[Dict[str, Any]]) -> None:
        """Render valid preview rows."""
        self.table_valid.setRowCount(len(valid_rows))
        for row_idx, r in enumerate(valid_rows):
            # Row number
            c0 = QTableWidgetItem(f"Row {r['row_number']}")
            c0.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            c0.setForeground(QColor("#64748b"))
            self.table_valid.setItem(row_idx, 0, c0)

            # Name
            c1 = QTableWidgetItem(r["name"])
            c1.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
            self.table_valid.setItem(row_idx, 1, c1)

            # Brand
            b_txt = r.get("brand_name") or "—"
            if r.get("is_new_brand"):
                b_txt += " ✨ [New]"
            c2 = QTableWidgetItem(b_txt)
            if r.get("is_new_brand"):
                c2.setForeground(QColor("#0369a1"))
            self.table_valid.setItem(row_idx, 2, c2)

            # Model
            c3 = QTableWidgetItem(r.get("model") or "—")
            c3.setForeground(QColor("#475569"))
            self.table_valid.setItem(row_idx, 3, c3)

            # Category
            cat_txt = r.get("category_name") or "—"
            if r.get("is_new_category"):
                cat_txt += " ✨ [New]"
            c4 = QTableWidgetItem(cat_txt)
            if r.get("is_new_category"):
                c4.setForeground(QColor("#4338ca"))
            self.table_valid.setItem(row_idx, 4, c4)

            # Min Stock
            c5 = QTableWidgetItem(f"{r.get('min_stock_alert', 5)} units")
            c5.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.table_valid.setItem(row_idx, 5, c5)

            # Warranty
            w_val = r.get("warranty_period_months", 0)
            c6 = QTableWidgetItem(f"{w_val} mos" if w_val > 0 else "None")
            c6.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table_valid.setItem(row_idx, 6, c6)

            self.table_valid.setRowHeight(row_idx, 32)

    def _populate_error_table(self, error_rows: List[Dict[str, Any]]) -> None:
        """Render error preview rows."""
        self.table_errors.setRowCount(len(error_rows))
        for row_idx, r in enumerate(error_rows):
            c0 = QTableWidgetItem(f"Row {r['row_number']}")
            c0.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            c0.setForeground(QColor("#b91c1c"))
            c0.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
            self.table_errors.setItem(row_idx, 0, c0)

            c1 = QTableWidgetItem(r.get("name") or "(Empty Name)")
            self.table_errors.setItem(row_idx, 1, c1)

            c2 = QTableWidgetItem(r.get("error_reason", "Validation failed"))
            c2.setForeground(QColor("#b91c1c"))
            self.table_errors.setItem(row_idx, 2, c2)

            self.table_errors.setRowHeight(row_idx, 32)

    def _reset_preview(self) -> None:
        """Reset state and tables."""
        self.card_total.lbl_val.setText("0")
        self.card_valid.lbl_val.setText("0")
        self.card_errors.lbl_val.setText("0")
        self.card_cats.lbl_val.setText("0")
        self.card_brands.lbl_val.setText("0")
        self.table_valid.setRowCount(0)
        self.table_errors.setRowCount(0)
        self.btn_import.setEnabled(False)
        self.btn_import.setText("📥 Import Products")
        self.lbl_info.setText("Please select an Excel (.xlsx) file.")

    def _on_download_template_clicked(self) -> None:
        """Generate and save Excel template."""
        save_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Product Import Template",
            "Product_Import_Template.xlsx",
            "Excel Workbooks (*.xlsx)",
        )
        if not save_path:
            return

        ok = self.import_service.generate_template(save_path)
        if ok:
            QMessageBox.information(
                self,
                "Template Saved",
                f"Product import template saved successfully to:\n\n{save_path}",
            )
        else:
            QMessageBox.critical(self, "Error", "Failed to generate Excel template.")

    def _on_import_clicked(self) -> None:
        """Confirm and commit bulk product import."""
        if not check_permission("products.manage", parent=self, action_name="import products"):
            return

        if not self.parsed_data or not self.parsed_data.get("valid_rows"):
            return

        val_rows = self.parsed_data["valid_rows"]
        err_count = self.parsed_data.get("error_count", 0)
        new_cats = self.parsed_data.get("new_categories", [])
        new_brands = self.parsed_data.get("new_brands", [])

        confirm_msg = f"Import <b>{len(val_rows)}</b> valid product(s) into catalog?"
        if new_cats or new_brands:
            confirm_msg += (
                f"\n\n• <b>{len(new_cats)}</b> new categories and "
                f"<b>{len(new_brands)}</b> new brands will be auto-created."
            )
        if err_count > 0:
            confirm_msg += f"\n\n⚠️ <b>{err_count}</b> row(s) with errors will be skipped."

        confirm_msg += "\n\n(Note: Current stock for all imported products starts at 0. Stock is added via Purchases.)"

        reply = QMessageBox.question(
            self,
            "Confirm Excel Product Import",
            confirm_msg,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        ok, imported_count, new_c_cnt, new_b_cnt, msg = self.import_service.commit_import(val_rows)
        if not ok:
            QMessageBox.critical(self, "Import Failed", msg)
            return

        QMessageBox.information(
            self,
            "Import Successful",
            f"🎉 <b>Bulk Import Completed Successfully!</b>\n\n"
            f"• <b>{imported_count}</b> Products imported.\n"
            f"• <b>{new_c_cnt}</b> Categories auto-created.\n"
            f"• <b>{new_b_cnt}</b> Brands auto-created.\n"
            f"• Initial stock set to 0 (system-managed).",
        )
        self.import_completed.emit(imported_count)
        self.accept()
