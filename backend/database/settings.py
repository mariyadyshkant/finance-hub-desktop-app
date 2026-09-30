from .connection import get_conn, _close, _row_to_dict

# ─── Impostazioni app (nome visualizzato, chiave Splitwise, ecc.) ─────────────
# Chiave/valore invece di una colonna per impostazione: evita una migrazione
# di schema ogni volta che si aggiunge un'impostazione configurabile.

def init_settings():
    conn = get_conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS app_settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)
    conn.commit()
    _close(conn)

def get_setting(key, default=None):
    conn = get_conn()
    cur = conn.execute("SELECT value FROM app_settings WHERE key=?", (key,))
    row = _row_to_dict(cur, cur.fetchone())
    _close(conn)
    return row["value"] if row else default

def set_setting(key, value):
    conn = get_conn()
    conn.execute(
        "INSERT OR REPLACE INTO app_settings (key, value) VALUES (?,?)",
        (key, value)
    )
    conn.commit()
    _close(conn)
