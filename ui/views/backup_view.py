"""
Database Backup & Disaster Recovery View.
"""

from typing import Optional, Dict, Any, List
import os
import shutil
import datetime
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QMessageBox,
    QFrame,
    QFileDialog,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QColor

from data.db import get_db
from business.permissions import check_permission


class BackupRestoreView(QWidget):
    """
    Database Backup & Restore Administration Screen.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.db = get_db()
        self._setup_ui()
        self.load_backups()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        # Header
        top_bar = QHBoxLayout()
        header_layout = QVBoxLayout()
        lbl_title = QLabel("💾 Database Backup & Restore")
        lbl_title.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        lbl_title.setStyleSheet("color: #0f172a;")
        lbl_subtitle = QLabel("Create point-in-time database snapshots and disaster recovery backups.")
        lbl_subtitle.setStyleSheet("color: #64748b; font-size: 12px;")
        header_layout.addWidget(lbl_title)
        header_layout.addWidget(lbl_subtitle)
        top_bar.addLayout(header_layout)

        top_bar.addStretch()

        self.btn_create_backup = QPushButton("+ Create Backup Now")
        self.btn_create_backup.setStyleSheet("""
            background-color: #2563eb; color: white; padding: 8px 18px; border-radius: 6px; font-weight: bold; font-size: 13px;
        """)
        self.btn_create_backup.clicked.connect(self._create_backup_now)
        top_bar.addWidget(self.btn_create_backup)

        layout.addLayout(top_bar)

        # Backups Table
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels([
            "Backup Filename", "Created At", "File Size", "Type", "Status"
        ])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self.table)

    def load_backups(self) -> None:
        """Query backup log history from DB."""
        sql = "SELECT * FROM backups ORDER BY created_at DESC LIMIT 100;"
        try:
            self.backups = [dict(r) for r in self.db.execute_query(sql)]
        except Exception:
            self.backups = []

        self.table.setRowCount(len(self.backups))
        for row_idx, b in enumerate(self.backups):
            # Filename
            f_item = QTableWidgetItem(b.get("filename", ""))
            f_item.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
            self.table.setItem(row_idx, 0, f_item)

            # Created At
            self.table.setItem(row_idx, 1, QTableWidgetItem(str(b.get("created_at", ""))))

            # Size
            size_kb = b.get("file_size_bytes", 0) / 1024.0
            size_str = f"{size_kb:.1f} KB" if size_kb < 1024 else f"{size_kb/1024:.2f} MB"
            self.table.setItem(row_idx, 2, QTableWidgetItem(size_str))

            # Type
            self.table.setItem(row_idx, 3, QTableWidgetItem(str(b.get("backup_type", "manual")).upper()))

            # Status
            stat_item = QTableWidgetItem(str(b.get("status", "completed")).upper())
            stat_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            stat_item.setForeground(QColor("#16a34a"))
            self.table.setItem(row_idx, 4, stat_item)
            self.table.setRowHeight(row_idx, 38)

    def _create_backup_now(self) -> None:
        """Create a live SQLite database backup snapshot."""
        if not check_permission("backup_restore.manage", parent=self, action_name="create database backups"):
            return

        db_path = self.db.db_path
        if not os.path.exists(db_path):
            QMessageBox.critical(self, "Error", f"Database file not found at {db_path}")
            return

        now_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_dir = os.path.join(os.path.dirname(db_path), "backups")
        os.makedirs(backup_dir, exist_ok=True)

        backup_filename = f"store_backup_{now_str}.db"
        dest_path = os.path.join(backup_dir, backup_filename)

        try:
            shutil.copy2(db_path, dest_path)
            file_size = os.path.getsize(dest_path)

            sql = """
                INSERT INTO backups (filename, file_path, file_size_bytes, backup_type, status, notes)
                VALUES (?, ?, ?, 'manual', 'completed', 'Manual snapshot initiated by user');
            """
            self.db.execute_update(sql, (backup_filename, dest_path, file_size))
            QMessageBox.information(
                self,
                "Backup Successful",
                f"Database snapshot successfully saved:\n\n{backup_filename}\nSize: {file_size/1024:.1f} KB",
            )
            self.load_backups()
        except Exception as e:
            QMessageBox.critical(self, "Backup Error", f"Failed to create backup: {e}")
