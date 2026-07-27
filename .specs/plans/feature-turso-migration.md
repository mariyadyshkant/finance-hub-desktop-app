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

[x] Completata

**Completata il:** 2026-07-28

**Cosa è stato fatto:**
- Migrazione di `database.py` per supportare Turso oltre a SQLite locale (invariato di default).
- Tentativo iniziale con `libsql_experimental` (driver nativo) — bloccato: build Rust fallisce su macOS senza GNU coreutils (`build.rs` di `libsql-ffi` usa `cp` in stile GNU).
- Deviazione dal piano originale: sostituito con `backend/turso_client.py`, client scritto in-house sull'API HTTP di Turso (Hrana su `/v2/pipeline`, via `requests`), stessa interfaccia sqlite3-like usata dal resto di `database.py`. Zero dipendenze nuove.
- `backend/check_db.py` per smoke test rapido.
- Verificato con round-trip completo (insert, update, bulk insert, query per mese, delete) contro il database Turso reale dell'utente — nessun dato di test residuo.
- `.gitignore` esteso per coprire `*.db`/`*.db-wal`/`*.db-shm` a qualunque livello.
- `ADR.md` annotato con la deviazione (sezione "Turso — database cloud").

**Note:** la parte di setup account (`turso auth login`, `turso db create`, URL/token) è stata fatta dall'utente, non automatizzabile da un agente non interattivo.
