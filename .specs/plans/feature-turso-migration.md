# Feature: Migrazione database a Turso

## Obiettivo

Sostituire SQLite locale con Turso (SQLite cloud) come storage condiviso tra app desktop e futuro bot Telegram, così i dati restano sincronizzati anche a Mac spento.

## Dipendenze

- Scaffolding base Electron + Svelte + FastAPI (completato, branch `dev`).
- Account Turso dell'utente + `turso` CLI installata e autenticata (azione manuale, non automatizzabile da qui).

## Stack

- `libsql_experimental` (Python) lato backend, in sostituzione condizionale di `sqlite3` — vedi ADR.md sezione "Architettura cloud (opzione scelta)".
- Nessuna nuova dipendenza frontend.

## Output atteso

- `backend/database.py` si connette a Turso quando `TURSO_DATABASE_URL`/`TURSO_AUTH_TOKEN` sono presenti in `.env`, altrimenti fallback trasparente su SQLite locale.
- `backend/check_db.py` conferma la connessione (locale o Turso) senza dover avviare l'intero server.
- Utente in possesso di un database Turso reale, popolato o pronto per essere popolato.

## Status

[~] In corso

**Fatto (branch `feature/turso-migration`, commit `11c4b5a`):**
- Migrazione di `database.py` (executescript → CREATE TABLE singole, executemany posizionale invece di parametri nominati, wrapper `_close`/`_rows_to_dicts` per compatibilità tra i due driver).
- `requirements.txt` e `.env.example` aggiornati.
- `check_db.py` aggiunto e verificato in locale (fallback SQLite).

**Bloccato su azione utente:**
- Creazione del database Turso reale (`turso auth login` + `turso db create`) — richiede l'account dell'utente, non eseguibile da un agente non interattivo.
- Verifica che `pip install libsql-experimental` builda correttamente sulla macchina reale dell'utente (nel sandbox di sviluppo la build da sorgente è fallita per assenza di un toolchain Rust funzionante — vedi nota in `requirements.txt`).

**Prossimo passo:** utente fornisce URL/token Turso in `backend/.env`, esegue `pip install -r requirements.txt` e `python3 check_db.py`; poi si conferma il merge in `dev`.
