from .connection import get_conn, _close, _rows_to_dicts


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
