import json

from .connection import get_conn, _close, _rows_to_dicts, _row_to_dict


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
