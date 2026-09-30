import json

from .connection import get_conn, _close, _rows_to_dicts

# ─── Categorie personalizzabili ──────────────────────────────────────────────
# Le 18 categorie di default vivevano solo in importers/helpers.py (CATEGORIES
# + CAT_COLORS). Ora sono righe di tabella, così si possono aggiungere,
# rinominare ed eliminare dall'app. Il categorizzatore automatico dei nuovi
# import continua a usare i nomi di default: se rinomini/elimini una di quelle
# (es. "Spesa"), i prossimi import Revolut la ricreeranno.

def init_categories():
    conn = get_conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            color TEXT NOT NULL DEFAULT '#0e7490',
            icon TEXT NOT NULL DEFAULT 'repeat',
            position INTEGER NOT NULL DEFAULT 0,
            is_default INTEGER NOT NULL DEFAULT 0
        )
    """)
    conn.commit()
    # Migrazione per i DB creati prima dell'aggiunta della colonna `icon`.
    try:
        conn.execute("ALTER TABLE categories ADD COLUMN icon TEXT NOT NULL DEFAULT 'repeat'")
        conn.commit()
    except Exception:
        pass  # colonna già presente

    from importers.helpers import CATEGORIES, CAT_COLORS, CAT_ICONS
    cur = conn.execute("SELECT COUNT(*) FROM categories")
    if cur.fetchone()[0] == 0:
        for i, name in enumerate(CATEGORIES):
            conn.execute(
                "INSERT INTO categories (name, color, icon, position, is_default) VALUES (?,?,?,?,1)",
                (name, CAT_COLORS.get(name, "#0e7490"), CAT_ICONS.get(name, "repeat"), i),
            )
        conn.commit()
    else:
        # DB migrato: assegna le icone di default a quelle categorie di default
        # ancora sul valore iniziale 'repeat' (non tocca quelle personalizzate).
        for name, ic in CAT_ICONS.items():
            conn.execute(
                "UPDATE categories SET icon=? WHERE name=? AND is_default=1 AND icon='repeat'",
                (ic, name),
            )
        conn.commit()
    _close(conn)

def get_categories():
    conn = get_conn()
    cur = conn.execute(
        "SELECT name, color, icon, is_default FROM categories ORDER BY position, id"
    )
    rows = _rows_to_dicts(cur, cur.fetchall())
    _close(conn)
    return rows

def add_category(name, color, icon="repeat"):
    conn = get_conn()
    cur = conn.execute("SELECT COALESCE(MAX(position), 0) + 1 FROM categories")
    pos = cur.fetchone()[0]
    conn.execute(
        "INSERT INTO categories (name, color, icon, position, is_default) VALUES (?,?,?,?,0)",
        (name, color, icon, pos),
    )
    conn.commit()
    _close(conn)

def set_category_color(name, color):
    conn = get_conn()
    conn.execute("UPDATE categories SET color=? WHERE name=?", (color, name))
    conn.commit()
    _close(conn)

def set_category_icon(name, icon):
    conn = get_conn()
    conn.execute("UPDATE categories SET icon=? WHERE name=?", (icon, name))
    conn.commit()
    _close(conn)

# Tabelle che referenziano una categoria per nome (stringa, nessuna FK).
_CATEGORY_REF_TABLES = (
    "transactions",
    "monthly_summaries",
    "planned_expenses",
    "planned_expense_overrides",
)

def _remap_budget_json(conn, old_name, new_name):
    """Sposta l'eventuale voce `old_name` in `monthly_budgets.cat_budgets`
    (JSON per mese) sotto `new_name`, sommandola se già presente."""
    # monthly_budgets è creata pigramente da get/upsert_monthly_budget: se
    # nessun budget è mai stato salvato la tabella non esiste ancora.
    try:
        cur = conn.execute("SELECT month, cat_budgets FROM monthly_budgets")
    except Exception:
        return
    for month, raw in cur.fetchall():
        try:
            data = json.loads(raw or "{}")
        except (ValueError, TypeError):
            continue
        if old_name in data:
            data[new_name] = round(data.get(new_name, 0) + data.pop(old_name), 2)
            conn.execute(
                "UPDATE monthly_budgets SET cat_budgets=? WHERE month=?",
                (json.dumps(data), month),
            )
    conn.commit()

def rename_category(old_name, new_name):
    """Rinomina la categoria e riallinea ogni riga che la referenzia per nome."""
    conn = get_conn()
    conn.execute("UPDATE categories SET name=? WHERE name=?", (new_name, old_name))
    for table in _CATEGORY_REF_TABLES:
        conn.execute(f"UPDATE {table} SET category=? WHERE category=?", (new_name, old_name))
    conn.execute("DELETE FROM budgets WHERE category=?", (new_name,))
    conn.execute("UPDATE budgets SET category=? WHERE category=?", (new_name, old_name))
    conn.commit()
    _remap_budget_json(conn, old_name, new_name)
    _close(conn)

def delete_category(name, reassign_to):
    """Elimina la categoria e riassegna a `reassign_to` tutte le righe che la
    usavano (transazioni, riepiloghi, spese pianificate, override, budget)."""
    conn = get_conn()
    conn.execute("DELETE FROM categories WHERE name=?", (name,))
    for table in _CATEGORY_REF_TABLES:
        conn.execute(f"UPDATE {table} SET category=? WHERE category=?", (reassign_to, name))
    conn.execute("DELETE FROM budgets WHERE category=?", (name,))
    conn.commit()
    _remap_budget_json(conn, name, reassign_to)
    _close(conn)
