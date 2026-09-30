# Feature: verifica rischio sincronizzazione SQLite/Turso — issue-audit-4

## Obiettivo

Dall'audit del repo (30/09/2026, commit `3b56e4f`, vedi `AUDIT.md`): il
database duale (SQLite locale come fallback, Turso come cloud, selezionati
dinamicamente in `get_conn()`) funziona, ma è una superficie in più dove un
bug di sincronizzazione — dati diversi tra l'app desktop e il bot Telegram —
potrebbe comparire silenziosamente. È un'area a rischio, non un problema
confermato: va verificata.

## Dipendenze

- Nessuna.

## Stack

- Backend FastAPI, SQLite locale + Turso cloud, selezione in `get_conn()`
  (`backend/database.py` o equivalente dopo `issue-audit-2`).

## Output atteso

- Mappatura esplicita di quando `get_conn()` sceglie SQLite vs Turso (desktop
  app locale, bot Telegram, backend hosted su Fly.io) e in quali condizioni
  (env var, presenza di `TURSO_DATABASE_URL`, ecc.).
- Verifica concreta: scenario in cui l'app desktop scrive via SQLite locale
  mentre il bot Telegram scrive su Turso (o viceversa) — confermare se può
  accadere in uso normale, e se sì, se i dati restano visibilmente
  disallineati tra i due canali.
- Se il rischio è confermato: proposta minima per eliminarlo (es. forzare
  sempre Turso quando configurato, o documentare esplicitamente che
  desktop/bot devono puntare sempre alla stessa sorgente) — implementazione
  comunque minima, non un redesign del layer DB.
- Se il rischio *non* è confermato (es. desktop e bot puntano sempre alla
  stessa sorgente per costruzione): chiudere l'issue con la spiegazione e
  aggiornare l'ADR/README se il punto non era già chiaro.

## Status

[x] Completata

**Completata il:** 2026-09-30

**Cosa è stato verificato:**
- `main.py` e `telegram_bot.py` girano nello **stesso processo** FastAPI
  (`telegram_bot` è importato e montato in `main.py`), quindi sia l'app
  desktop (backend spawnato da Electron) sia il webhook del bot Telegram
  usano la stessa istanza di `database.py` / `get_conn()`.
- Il webhook Telegram deve avere un URL pubblico HTTPS (Telegram non può
  chiamare `127.0.0.1`): punta al backend hosted su Fly.io
  (`financed-backend.fly.dev`), che carica `TURSO_DATABASE_URL` da
  `fly secrets`. Il backend locale spawnato da Electron carica invece
  `backend/.env`.
- Sul setup attuale entrambi (`.env` locale e Fly secrets) hanno
  `TURSO_DATABASE_URL` impostato sulla stessa istanza Turso → **nessun
  disallineamento reale oggi**, confermato con smoke test: avviato il
  backend locale, log di startup mostra
  `[financed] DB backend: Turso (libsql://finance-hub-mariyadyshkant...)`.
- Il rischio however è reale: prima del fix, `get_conn()` sceglieva
  SQLite/Turso **senza nessun log**. Chiunque avvii il backend senza
  `TURSO_DATABASE_URL` configurato (fresh clone, build PyInstaller senza
  `.env` accanto, ecc.) finirebbe silenziosamente su `finance.db` locale,
  con dati diversi da bot/mobile e nessun modo di accorgersene.

**Fix applicato (minimo, come da spec):**
- `backend/database.py`: nuova `db_backend_label()` che descrive il backend
  attivo (Turso con URL, o percorso SQLite locale).
- `backend/main.py`: log `[financed] DB backend: ...` all'avvio
  (`on_startup`), prima di `init_db()`. Visibile sia in sviluppo sia nei log
  di Fly.io.
- Verificato con smoke test locale (`uvicorn main:app`): log corretto,
  `/health` → `200 {"status":"ok"}`.

**Deliberatamente fuori scope:**
- Nessun redesign del layer DB (es. forzare sempre Turso, bloccare
  l'avvio senza `TURSO_DATABASE_URL`): la spec chiedeva una mitigazione
  minima, non un redesign; il log basta a rendere visibile un eventuale
  disallineamento futuro senza cambiare comportamento per chi già ha
  Turso configurato correttamente.
