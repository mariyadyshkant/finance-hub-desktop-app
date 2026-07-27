"""Smoke test rapido per verificare la connessione al database (locale o Turso).

Uso:
    cd backend && python3 check_db.py
"""
from dotenv import load_dotenv

load_dotenv()

import database as db

if __name__ == "__main__":
    backend = "Turso" if db.TURSO_URL else f"SQLite locale ({db.DB_PATH})"
    print(f"Backend: {backend}")

    db.init_db()
    db.init_monthly_summaries()
    db.init_planned_expenses()
    print("✅ Tabelle create/verificate con successo.")

    tx_count = len(db.get_transactions())
    print(f"✅ Lettura riuscita — {tx_count} transazioni trovate.")
