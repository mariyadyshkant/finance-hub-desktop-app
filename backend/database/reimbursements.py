from .connection import get_conn, _close, _rows_to_dicts


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
