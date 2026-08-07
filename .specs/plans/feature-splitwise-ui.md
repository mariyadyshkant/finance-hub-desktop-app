# Feature: Sezione Splitwise

## Obiettivo

Sostituire il placeholder di `Splitwise.svelte` con la UI reale, a parità di funzionalità con `finance-hub/pages/4_🏦_Splitwise.py`: saldo per amico, saldi per gruppo, ultime spese condivise.

## Dipendenze

- Backend `routes/splitwise.py` già pronto (legge `SPLITWISE_API_KEY` da `backend/.env` lato server — a differenza della versione Streamlit non c'è più un campo per incollare la chiave nel frontend, per non farla transitare/salvare lato client).

## Stack

- Solo frontend, nessuna dipendenza nuova.

## Output atteso

- Se `SPLITWISE_API_KEY` non configurata: istruzioni su come impostarla in `backend/.env`.
- Se configurata: utente connesso, saldo complessivo (mi devono/devo io), saldi per gruppo, ultime spese condivise.

## Status

[x] Completata

**Completata il:** 2026-07-31

**Cosa è stato fatto:** `Splitwise.svelte` — rileva se `SPLITWISE_API_KEY` non è configurata (risposta 400 da `/api/splitwise/user`) e mostra istruzioni di setup; se connessa: saldo complessivo (mi devono/devo io) aggregato dai saldi amici, dettaglio per amico, saldi per gruppo (dal membro corrispondente all'utente corrente), ultime spese condivise con quota netta personale. Nessuna build di verifica lanciata su richiesta dell'utente.
