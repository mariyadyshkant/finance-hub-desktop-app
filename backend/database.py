import json
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
    _BASE_DIR = Path(__file__).parent

DB_PATH = _BASE_DIR / "finance.db"

TURSO_URL = os.getenv("TURSO_DATABASE_URL")
TURSO_TOKEN = os.getenv("TURSO_AUTH_TOKEN")


def get_conn():
    if TURSO_URL:
        from turso_client import TursoConnection
        return TursoConnection(TURSO_URL, TURSO_TOKEN)
    return sqlite3.connect(DB_PATH, check_same_thread=False)


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

# ─── Transactions ────────────────────────────────────────────────────────────

def get_transactions(month=None):
    conn = get_conn()
    if month:
        cur = conn.execute(
            "SELECT * FROM transactions WHERE strftime('%Y-%m', date) = ? ORDER BY date DESC",
            (month,)
        )
    else:
        cur = conn.execute("SELECT * FROM transactions ORDER BY date DESC")
    rows = _rows_to_dicts(cur, cur.fetchall())
    _close(conn)
    return rows

def add_transaction(date, description, amount, category, source="manual", note=""):
    conn = get_conn()
    conn.execute(
        "INSERT INTO transactions (date, description, amount, category, source, note) VALUES (?,?,?,?,?,?)",
        (date, description, amount, category, source, note)
    )
    conn.commit()
    _close(conn)

def update_transaction(tx_id, **kwargs):
    conn = get_conn()
    fields = ", ".join(f"{k}=?" for k in kwargs)
    values = list(kwargs.values()) + [tx_id]
    conn.execute(f"UPDATE transactions SET {fields} WHERE id=?", values)
    conn.commit()
    _close(conn)

def delete_transaction(tx_id):
    conn = get_conn()
    conn.execute("DELETE FROM transactions WHERE id=?", (tx_id,))
    conn.commit()
    _close(conn)

def import_transactions_bulk(records):
    """records: list of dicts with keys date, description, amount, category, source"""
    conn = get_conn()
    tuples = [
        (r["date"], r["description"], r["amount"], r["category"], r.get("source", "manual"))
        for r in records
    ]
    conn.executemany(
        "INSERT INTO transactions (date, description, amount, category, source) VALUES (?,?,?,?,?)",
        tuples
    )
    conn.commit()
    _close(conn)
    return len(records)

def get_available_months():
    conn = get_conn()
    cur = conn.execute(
        "SELECT DISTINCT strftime('%Y-%m', date) as m FROM transactions ORDER BY m DESC"
    )
    rows = _rows_to_dicts(cur, cur.fetchall())
    _close(conn)
    return [r["m"] for r in rows]

# ─── Reimbursements ──────────────────────────────────────────────────────────

def get_reimbursements(status=None):
    conn = get_conn()
    if status:
        cur = conn.execute(
            "SELECT * FROM reimbursements WHERE status=? ORDER BY date DESC", (status,)
        )
    else:
        cur = conn.execute("SELECT * FROM reimbursements ORDER BY date DESC")
    rows = _rows_to_dicts(cur, cur.fetchall())
    _close(conn)
    return rows

def add_reimbursement(date, description, amount, from_person, note="", transaction_id=None):
    conn = get_conn()
    conn.execute(
        "INSERT INTO reimbursements (date, description, amount, from_person, note, transaction_id) VALUES (?,?,?,?,?,?)",
        (date, description, amount, from_person, note, transaction_id)
    )
    conn.commit()
    _close(conn)

def update_reimbursement(r_id, **kwargs):
    conn = get_conn()
    fields = ", ".join(f"{k}=?" for k in kwargs)
    values = list(kwargs.values()) + [r_id]
    conn.execute(f"UPDATE reimbursements SET {fields} WHERE id=?", values)
    conn.commit()
    _close(conn)

def delete_reimbursement(r_id):
    conn = get_conn()
    conn.execute("DELETE FROM reimbursements WHERE id=?", (r_id,))
    conn.commit()
    _close(conn)

# ─── Savings ─────────────────────────────────────────────────────────────────

def get_savings():
    conn = get_conn()
    cur = conn.execute("SELECT * FROM savings ORDER BY date DESC")
    rows = _rows_to_dicts(cur, cur.fetchall())
    _close(conn)
    return rows

def add_savings_entry(date, amount, label="", note=""):
    conn = get_conn()
    conn.execute(
        "INSERT INTO savings (date, amount, label, note) VALUES (?,?,?,?)",
        (date, amount, label, note)
    )
    conn.commit()
    _close(conn)

def delete_savings_entry(s_id):
    conn = get_conn()
    conn.execute("DELETE FROM savings WHERE id=?", (s_id,))
    conn.commit()
    _close(conn)

# ─── Work shifts ─────────────────────────────────────────────────────────────

def get_shifts(month=None):
    conn = get_conn()
    if month:
        cur = conn.execute(
            "SELECT * FROM work_shifts WHERE strftime('%Y-%m', date) = ? ORDER BY date",
            (month,)
        )
    else:
        cur = conn.execute("SELECT * FROM work_shifts ORDER BY date DESC")
    rows = _rows_to_dicts(cur, cur.fetchall())
    _close(conn)
    return rows

def add_shift(date, hours, start_time="", end_time="", note=""):
    conn = get_conn()
    conn.execute(
        "INSERT INTO work_shifts (date, hours, start_time, end_time, note) VALUES (?,?,?,?,?)",
        (date, hours, start_time, end_time, note)
    )
    conn.commit()
    _close(conn)

def delete_shift(shift_id):
    conn = get_conn()
    conn.execute("DELETE FROM work_shifts WHERE id=?", (shift_id,))
    conn.commit()
    _close(conn)

def add_shifts_bulk(shifts):
    conn = get_conn()
    tuples = [
        (s["date"], s["hours"], s.get("start_time", ""), s.get("end_time", ""), s.get("note", ""))
        for s in shifts
    ]
    conn.executemany(
        "INSERT INTO work_shifts (date, hours, start_time, end_time, note) VALUES (?,?,?,?,?)",
        tuples
    )
    conn.commit()
    _close(conn)

# ─── Salary ──────────────────────────────────────────────────────────────────

def get_salary_records():
    conn = get_conn()
    cur = conn.execute("SELECT * FROM salary_records ORDER BY month DESC")
    rows = _rows_to_dicts(cur, cur.fetchall())
    _close(conn)
    return rows

def add_salary_record(month, net, gross=None, hours_worked=None, note=""):
    conn = get_conn()
    conn.execute(
        "INSERT OR REPLACE INTO salary_records (month, net, gross, hours_worked, note) VALUES (?,?,?,?,?)",
        (month, net, gross, hours_worked, note)
    )
    conn.commit()
    _close(conn)

def delete_salary_record(s_id):
    conn = get_conn()
    conn.execute("DELETE FROM salary_records WHERE id=?", (s_id,))
    conn.commit()
    _close(conn)

# ─── Budgets ─────────────────────────────────────────────────────────────────

def get_budgets():
    conn = get_conn()
    cur = conn.execute("SELECT * FROM budgets")
    rows = _rows_to_dicts(cur, cur.fetchall())
    _close(conn)
    return {r["category"]: r["monthly_limit"] for r in rows}

def set_budget(category, limit):
    conn = get_conn()
    conn.execute(
        "INSERT OR REPLACE INTO budgets (category, monthly_limit) VALUES (?,?)",
        (category, limit)
    )
    conn.commit()
    _close(conn)

# ─── Monthly summaries (Notion import) ───────────────────────────────────────

def init_monthly_summaries():
    conn = get_conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS monthly_summaries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            month TEXT NOT NULL,
            category TEXT NOT NULL,
            amount REAL NOT NULL,
            source TEXT DEFAULT 'notion',
            UNIQUE(month, category)
        )
    """)
    conn.commit()
    _close(conn)

def upsert_monthly_summary(month, category, amount, source="notion"):
    conn = get_conn()
    conn.execute(
        "INSERT OR REPLACE INTO monthly_summaries (month, category, amount, source) VALUES (?,?,?,?)",
        (month, category, amount, source)
    )
    conn.commit()
    _close(conn)

def get_monthly_summaries(month=None):
    conn = get_conn()
    if month:
        cur = conn.execute(
            "SELECT * FROM monthly_summaries WHERE month=? ORDER BY amount DESC", (month,)
        )
    else:
        cur = conn.execute(
            "SELECT * FROM monthly_summaries ORDER BY month DESC, amount DESC"
        )
    rows = _rows_to_dicts(cur, cur.fetchall())
    _close(conn)
    return rows

def get_summary_months():
    conn = get_conn()
    cur = conn.execute(
        "SELECT DISTINCT month FROM monthly_summaries ORDER BY month DESC"
    )
    rows = _rows_to_dicts(cur, cur.fetchall())
    _close(conn)
    return [r["month"] for r in rows]

def delete_monthly_summary_month(month):
    conn = get_conn()
    conn.execute("DELETE FROM monthly_summaries WHERE month=?", (month,))
    conn.commit()
    _close(conn)

# ─── Budget ───────────────────────────────────────────────────────────────────

def get_monthly_budget(month):
    conn = get_conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS monthly_budgets (
            month TEXT PRIMARY KEY,
            total REAL,
            cat_budgets TEXT,
            note TEXT DEFAULT ''
        )
    """)
    conn.commit()
    cur = conn.execute(
        "SELECT * FROM monthly_budgets WHERE month=?", (month,)
    )
    row = _row_to_dict(cur, cur.fetchone())
    _close(conn)
    return row

def upsert_monthly_budget(month, total, cat_budgets: dict, note=""):
    conn = get_conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS monthly_budgets (
            month TEXT PRIMARY KEY,
            total REAL,
            cat_budgets TEXT,
            note TEXT DEFAULT ''
        )
    """)
    conn.execute(
        "INSERT OR REPLACE INTO monthly_budgets (month, total, cat_budgets, note) VALUES (?,?,?,?)",
        (month, total, json.dumps(cat_budgets), note)
    )
    conn.commit()
    _close(conn)

# ─── Planned expenses ────────────────────────────────────────────────────────

def init_planned_expenses():
    conn = get_conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS planned_expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            description TEXT NOT NULL,
            amount REAL NOT NULL,
            category TEXT NOT NULL,
            is_recurring INTEGER DEFAULT 1,
            active INTEGER DEFAULT 1
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS planned_expense_overrides (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            month TEXT NOT NULL,
            planned_id INTEGER,
            description TEXT,
            amount REAL,
            category TEXT,
            is_exceptional INTEGER DEFAULT 0,
            note TEXT DEFAULT '',
            UNIQUE(month, planned_id)
        )
    """)
    conn.commit()
    _close(conn)

def get_planned_expenses():
    conn = get_conn()
    cur = conn.execute(
        "SELECT * FROM planned_expenses WHERE active=1 ORDER BY amount DESC"
    )
    rows = _rows_to_dicts(cur, cur.fetchall())
    _close(conn)
    return rows

def add_planned_expense(description, amount, category, is_recurring=1):
    conn = get_conn()
    conn.execute(
        "INSERT INTO planned_expenses (description, amount, category, is_recurring) VALUES (?,?,?,?)",
        (description, amount, category, is_recurring)
    )
    conn.commit()
    _close(conn)

def update_planned_expense(pid, **kwargs):
    conn = get_conn()
    fields = ", ".join(f"{k}=?" for k in kwargs)
    conn.execute(f"UPDATE planned_expenses SET {fields} WHERE id=?", list(kwargs.values())+[pid])
    conn.commit()
    _close(conn)

def delete_planned_expense(pid):
    conn = get_conn()
    conn.execute("UPDATE planned_expenses SET active=0 WHERE id=?", (pid,))
    conn.commit()
    _close(conn)

def get_overrides(month):
    conn = get_conn()
    cur = conn.execute(
        "SELECT * FROM planned_expense_overrides WHERE month=?", (month,)
    )
    rows = _rows_to_dicts(cur, cur.fetchall())
    _close(conn)
    return {r["planned_id"]: r for r in rows}

def upsert_override(month, planned_id, amount, is_exceptional=0, note=""):
    conn = get_conn()
    conn.execute("""
        INSERT OR REPLACE INTO planned_expense_overrides
        (month, planned_id, amount, is_exceptional, note)
        VALUES (?,?,?,?,?)
    """, (month, planned_id, amount, is_exceptional, note))
    conn.commit()
    _close(conn)

def delete_override(month, planned_id):
    conn = get_conn()
    conn.execute(
        "DELETE FROM planned_expense_overrides WHERE month=? AND planned_id=?",
        (month, planned_id)
    )
    conn.commit()
    _close(conn)
