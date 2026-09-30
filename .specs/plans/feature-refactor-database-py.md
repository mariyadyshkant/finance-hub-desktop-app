# Feature: separazione di database.py per dominio — issue-audit-2

## Obiettivo

Dall'audit del repo (30/09/2026, commit `3b56e4f`, vedi `AUDIT.md`):
`backend/database.py` (666 righe) è un "god file" con tutte le query per tutte
le entità (transazioni, rimborsi, risparmi, turni, budget, categorie...).
Funziona, ma il resto del backend è già ben separato per dominio (es.
`routes/salary.py`, `routes/savings.py`, tutti sotto 100 righe) — separare
anche `database.py` sullo stesso modello sarebbe un miglioramento naturale e
coerente con il resto dell'architettura.

## Dipendenze

- Nessuna. Nessun cambio di schema o comportamento previsto, solo
  riorganizzazione del codice.

## Stack

- Backend FastAPI + SQLite/Turso, coerente con l'ADR. Nessuna dipendenza
  nuova.

## Output atteso

- `database.py` diviso in moduli per dominio (es. `db/transactions.py`,
  `db/refunds.py`, `db/savings.py`, `db/shifts.py`, `db/budgets.py`,
  `db/categories.py`), specchiando la separazione già esistente in
  `routes/`.
- `get_conn()` e la logica di selezione SQLite/Turso restano centralizzate
  (es. in `db/connection.py`), usate da tutti i moduli di dominio.
- Tutte le route continuano a funzionare senza modifiche di comportamento;
  aggiornati solo gli import.
- Verifica: suite di test backend esistente (se presente) verde; altrimenti
  smoke test manuale delle route principali (transazioni, rimborsi, risparmi,
  turni, budget, categorie) su SQLite locale.

## Status

[x] Completata

**Completata il:** 2026-09-30

**Cosa è stato fatto:**
- `backend/database.py` (677 righe) sostituito da un package
  `backend/database/` con un modulo per dominio: `connection.py` (`get_conn`,
  `db_backend_label`, `init_db` — tabelle core: transactions, reimbursements,
  savings, work_shifts, salary_records, budgets), `transactions.py`,
  `reimbursements.py`, `savings.py`, `shifts.py`, `salary.py`, `budgets.py`
  (tabella `budgets` semplice per categoria — risultata già inutilizzata da
  nessuna route, spostata com'è senza pulizie fuori scope), `summaries.py`
  (riepiloghi mensili da Notion), `planning.py` (budget mensile JSON + spese
  pianificate/override), `settings.py`, `categories.py`.
- `__init__.py` del package riesporta tutti i nomi pubblici usati altrove
  (`DB_PATH`, `TURSO_URL`, `get_conn`, tutte le `get_*`/`add_*`/`update_*`/
  `delete_*`/`init_*`) — **nessuna modifica agli import in `main.py`,
  `telegram_bot.py`, `routes/*.py` o `check_db.py`**: `import database as db`
  e `from database import (...)` continuano a funzionare identici, perché
  Python tratta un package con `__init__.py` come il modulo stesso.
- `get_conn()` resta l'unico punto di selezione Turso/SQLite, ora in
  `connection.py`, usato da tutti i moduli di dominio.
- PyInstaller (`financed-backend.spec`): nessuna modifica necessaria —
  `Analysis` segue gli import a partire da `main.py` e rileva il package
  `database/` allo stesso modo di un modulo singolo.

**Verifica:**
- `check_db.py` (smoke test già presente nel repo) eseguito contro il
  backend reale (Turso): tabelle create/verificate, lettura transazioni OK
  (324 trovate).
- Backend avviato con `uvicorn main:app`: log di startup pulito
  (`[financed] DB backend: Turso (...)`), nessun errore di import.
- Smoke test manuale di tutte le route principali contro il backend reale:
  `/health`, `/api/categories`, `/api/transactions`, `/api/reimbursements`,
  `/api/savings`, `/api/shifts`, `/api/salary`, `/api/summaries`,
  `/api/planning/planned-expenses`, `/api/settings` — tutte 200 OK con dati
  nella forma attesa.
- Verificato per grep che ogni `db.<nome>` usato in `routes/*.py`,
  `telegram_bot.py`, `main.py`, `check_db.py` sia effettivamente esportato
  dal nuovo `__init__.py` — nessun nome mancante.

**Deliberatamente fuori scope:**
- Non ho eliminato `get_budgets`/`set_budget` (tabella `budgets` per
  categoria) pur risultando non referenziate da nessuna route — sono state
  spostate così com'erano in `budgets.py`: questo task è una riorganizzazione,
  non una pulizia di codice morto, e cambiarne il comportamento non era
  richiesto.
