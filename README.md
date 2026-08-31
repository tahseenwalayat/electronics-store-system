# ⚡ Electronics Store System

A desktop application for managing electronics retail operations, inventory, and point of sale, built with **Python**, **PySide6 (Qt for Python)**, and **SQLite**.

---

## 🏗️ Architecture Overview

The project adheres to a clean, layered architectural pattern:

```text
electronics-store-system/
├── assets/             # Static files (images, icons, fonts)
├── business/           # Business logic, services, and domain rules
├── data/               # SQLite connection wrapper, migrations, and database file
│   ├── migrations/     # Versioned SQL migration scripts
│   ├── db.py           # Database connection & migration manager
│   └── store.db        # SQLite database file (auto-generated)
├── models/             # Data models, DTOs, and entity definitions
├── resources/          # Qt resource files (.qrc), QSS stylesheets, and templates
├── ui/                 # PySide6 UI views, windows, custom widgets, and dialogs
│   ├── __init__.py
│   └── main_window.py  # Application main window
├── .gitignore          # Git ignore rules for Python, SQLite, build files
├── main.py             # Application entry point
├── requirements.txt    # Project dependencies
└── README.md           # Documentation & setup guide
```

### Layer Responsibilities

- **`/ui`**: User interface components constructed with PySide6 (Windows, Dialogs, Custom Widgets).
- **`/business`**: Business logic, workflow processing, validation, and domain services.
- **`/data`**: Database access layer managing the SQLite connection pool, query execution, transactions, and automated schema migrations (`./data/store.db`).
- **`/models`**: Data classes, entities, and data structures used across the application.
- **`/assets`**: Raw assets such as branding logos, product sample images, and icons.
- **`/resources`**: Compiled Qt resources, QSS theme stylesheets, and document templates.

---

## 🚀 Getting Started

### Prerequisites

- **Python 3.10+** installed on your system.

### 1. Clone or Open the Repository

```bash
cd electronics-store-system
```

### 2. Create a Virtual Environment

**Windows (PowerShell / Command Prompt):**
```powershell
python -m venv venv
```

**macOS / Linux:**
```bash
python3 -m venv venv
```

### 3. Activate the Virtual Environment

**Windows (PowerShell):**
```powershell
.\venv\Scripts\Activate.ps1
```

**Windows (Command Prompt):**
```cmd
.\venv\Scripts\activate.bat
```

**macOS / Linux:**
```bash
source venv/bin/activate
```

### 4. Install Dependencies

```bash
pip install -r requirements.txt
```

Dependencies installed:
- `PySide6`: Modern Qt-based GUI framework.
- `openpyxl`: Excel spreadsheet generation and data export/import.
- `reportlab`: PDF document and invoice receipt generator.
- `bcrypt`: Secure password hashing for user authentication.

### 5. Run the Application

```bash
python main.py
```

The database (`./data/store.db`) will be automatically initialized and migrations in `./data/migrations/` will be applied on first launch.

---

## 💾 Database & Migrations

- The database file is located at `./data/store.db`.
- Database schema changes are tracked in `./data/migrations/` using timestamped or numbered SQL scripts (e.g., `001_initial_schema.sql`).
- Executed migrations are tracked in the `schema_migrations` table to prevent duplicate execution.
