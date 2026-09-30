from .connection import get_conn, _close, _rows_to_dicts


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
