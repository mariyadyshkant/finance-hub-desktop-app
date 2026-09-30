import os
import sys
import sqlite3
from pathlib import Path

if getattr(sys, "frozen", False):
    # Eseguibile PyInstaller: __file__ punta dentro il bundle temporaneo
    # (_MEIPASS), non un percorso persistente — usiamo la cartella
    # dell'eseguibile stesso, dove vogliamo che finance.db viva davvero.
    _BASE_DIR = Path(sys.executable).parent
else:
    _BASE_DIR = Path(__file__).parent.parent

DB_PATH = _BASE_DIR / "finance.db"

TURSO_URL = os.getenv("TURSO_DATABASE_URL")
TURSO_TOKEN = os.getenv("TURSO_AUTH_TOKEN")


def get_conn():
    if TURSO_URL:
        from turso_client import TursoConnection
        return TursoConnection(TURSO_URL, TURSO_TOKEN)
    return sqlite3.connect(DB_PATH, check_same_thread=False)


def db_backend_label():
    """Descrizione leggibile del backend DB attivo, per il log di avvio
    (issue-audit-4: la scelta Turso/SQLite in get_conn() era silenziosa —
    se questa istanza e il bot Telegram finiscono su backend diversi, i dati
    divergono senza nessun avviso)."""
    if TURSO_URL:
        return f"Turso ({TURSO_URL})"
    return f"SQLite locale ({DB_PATH})"


def _close(conn):
    conn.close()


def _rows_to_dicts(cursor, rows):
    cols = [d[0] for d in cursor.description]
    return [dict(zip(cols, row)) for row in rows]


def _row_to_dict(cursor, row):
    if row is None:
        return None
    cols = [d[0] for d in cursor.description]
    return dict(zip(cols, row))


def init_db():
    conn = get_conn()

    for statement in (
        """
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            description TEXT NOT NULL,
            amount REAL NOT NULL,
            category TEXT NOT NULL,
            source TEXT DEFAULT 'manual',
            note TEXT DEFAULT '',
            created_at TEXT DEFAULT (datetime('now'))
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS reimbursements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            description TEXT NOT NULL,
            amount REAL NOT NULL,
            from_person TEXT NOT NULL,
            status TEXT DEFAULT 'in attesa',
            transaction_id INTEGER,
            note TEXT DEFAULT '',
            created_at TEXT DEFAULT (datetime('now'))
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS savings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            amount REAL NOT NULL,
            label TEXT DEFAULT '',
            note TEXT DEFAULT ''
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS work_shifts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            start_time TEXT,
            end_time TEXT,
            hours REAL NOT NULL,
            note TEXT DEFAULT ''
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS salary_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            month TEXT NOT NULL,
            gross REAL,
            net REAL,
            hours_worked REAL,
            note TEXT DEFAULT ''
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS budgets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT NOT NULL UNIQUE,
            monthly_limit REAL NOT NULL
        )
        """,
    ):
        conn.execute(statement)

    conn.commit()
    _close(conn)
