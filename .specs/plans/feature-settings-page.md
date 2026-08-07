# Feature: Pagina Impostazioni (portabilità, no dati hardcoded)

## Obiettivo

Rendere l'app davvero portabile a chiunque la scarichi: nessun nome utente hardcoded nel codice, nessuna chiave API/servizio esterno configurabile solo editando file a mano. In particolare Splitwise, che finora richiedeva di modificare `backend/.env`.

## Dipendenze

- Nessuna sezione dipende da questa — è trasversale (Sidebar, Splitwise).

## Stack

- Solo frontend + un piccolo store di configurazione lato backend (tabella `app_settings`, chiave/valore) — nessuna dipendenza nuova.

## Output atteso

- Nuova sezione "Impostazioni" in sidebar: nome visualizzato (sostituisce "Mariya" hardcoded) + chiave API Splitwise (salvabile/rimovibile dall'app, mai più richiesto di editare `.env`).
- `Sidebar.svelte` mostra il nome configurato invece di un nome fisso nel codice.
- `Splitwise.svelte` rimanda alla pagina Impostazioni invece che a `backend/.env`.
- Il backend continua a leggere `SPLITWISE_API_KEY` da `.env` come fallback per compatibilità, ma la fonte primaria è ora il DB.

## Status

[x] Completata

**Completata il:** 2026-08-07

**Cosa è stato fatto:**
- Backend: tabella `app_settings` (chiave/valore) + `get_setting`/`set_setting` in `database.py`; nuova route `routes/settings.py` (`GET /api/settings`, `POST /api/settings/profile`, `POST`/`DELETE /api/settings/splitwise`). Testato round-trip completo via curl.
- `routes/splitwise.py`: la chiave API ora si legge prima dal DB (`app_settings`), poi come fallback da `.env` (retrocompatibilità con chi l'aveva già configurata così).
- Frontend: nuova pagina `Impostazioni.svelte` (nome visualizzato + collega/disconnetti Splitwise), aggiunta come ultima voce di navigazione. `Sidebar.svelte` non mostra più "Mariya" hardcoded — legge `display_name` da `/api/settings` (fallback "Il tuo profilo" se non impostato); il footer è ora cliccabile e porta a Impostazioni.
- `Splitwise.svelte`: le istruzioni di setup rimandano alla pagina Impostazioni invece che a `backend/.env`.
- Verificato con grep che non restano riferimenti hardcoded al nome "Mariya" o a chiavi/token nel codice sorgente committato.

**Deliberatamente fuori scope:** credenziali Turso restano solo in `.env` (vedi nota sopra).

**Deliberatamente fuori scope:** le credenziali Turso (`TURSO_DATABASE_URL`/`TURSO_AUTH_TOKEN`) restano configurabili solo via `.env` — sono più infrastruttura ("dove vivono i dati") che una preferenza personale come Splitwise, e cambiarle da app viva è più delicato (richiederebbe riavviare la connessione al DB). Non richiesto esplicitamente dall'utente in questo giro.
