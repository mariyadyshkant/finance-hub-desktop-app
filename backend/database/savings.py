from .connection import get_conn, _close, _rows_to_dicts


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
