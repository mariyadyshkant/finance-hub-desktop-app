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

[ ] Da fare
