from .connection import get_conn, _close, _rows_to_dicts


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
