from .connection import get_conn, _close, _rows_to_dicts


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
