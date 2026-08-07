# Feature: Sezione Rimborsi

## Obiettivo

Sostituire il placeholder di `Rimborsi.svelte` con la UI reale, a parità di funzionalità con `finance-hub/pages/3_🔄_Rimborsi.py`: lista crediti in attesa/ricevuti, aggiunta manuale, segna come ricevuto, KPI.

## Dipendenze

- Backend `routes/reimbursements.py` già pronto (GET con filtro status, POST, PUT, DELETE), nessuna modifica prevista.
- Design system e componenti condivisi (Icon, pattern page-header/metric-card/pill-group) già stabiliti da Transazioni/Dashboard.

## Stack

- Solo frontend, nessuna dipendenza nuova.

## Output atteso

- KPI: totale in attesa, totale ricevuto.
- Filtro per stato (Tutti/In attesa/Ricevuti).
- Form aggiunta manuale.
- Lista con azione "segna come ricevuto" (PUT status) ed elimina.

## Status

[x] Completata

**Completata il:** 2026-07-31

**Cosa è stato fatto:** `Rimborsi.svelte` — KPI (in attesa/ricevuto), filtro stato a pillole, form aggiunta, lista con azioni segna-come-ricevuto (PUT status) ed elimina. Aggiunte le icone `check`/`clock` (mancanti) a `icons.js`. Nessuna build di verifica lanciata su richiesta dell'utente (la farà lei con `npm run dev`).
