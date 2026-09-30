from .connection import get_conn, _close, _rows_to_dicts


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
