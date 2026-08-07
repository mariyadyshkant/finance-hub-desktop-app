# Feature: Sezione Pianificazione

## Obiettivo

Sostituire il placeholder di `Pianificazione.svelte` con la UI reale, a parità di funzionalità con `finance-hub/pages/8_🎯_Pianificazione.py`: 3 tab (Spese pianificate, Budget, Consuntivo).

## Dipendenze

- Backend `routes/planning.py` già pronto (planned-expenses CRUD, budget GET/POST, overrides GET/POST/DELETE), nessuna modifica prevista.
- `Chart.svelte`/`chartTheme.js` riusati dalla Dashboard.
- Logica di "dati unificati" (transazioni Revolut + riepiloghi Notion) duplicata da `Dashboard.svelte` — non estratta in uno store condiviso in questa passata (nessuna prova ancora che serva altrove oltre queste due sezioni).

## Stack

- Solo frontend, nessuna dipendenza nuova.

## Output atteso

- **Spese pianificate**: gestione lista base ricorrente (aggiungi/modifica/elimina), vista per mese con override (importo, flag eccezionale, nota) salvabili inline.
- **Budget**: suggerimento da media storica (+10% per categoria, +5% totale), form con validazione (somma categorie vs totale), riepilogo con barra orizzontale per categoria (non torta, coerente con Dashboard).
- **Consuntivo**: budget vs speso (KPI, barra di avanzamento colorata, dettaglio per categoria a barre), spese eccezionali in evidenza, media mensile storica con grafico.

## Status

[x] Completata

**Completata il:** 2026-07-31

**Cosa è stato fatto:** `Pianificazione.svelte`, 3 tab. Spese pianificate: gestione lista base (aggiungi/modifica/elimina), vista mese con override editabili inline (importo, flag eccezionale, nota) salvati via upsert, KPI (pianificato/eccezionali/ordinarie). Budget: suggerimento da media storica (categorie: +10%, totale: +5%), validazione live somma-categorie-vs-totale, riepilogo con barra orizzontale per categoria (non torta, coerente con la sezione Dashboard). Consuntivo: KPI budget/speso/pianificato/rimanente, barra di avanzamento colorata per soglia, dettaglio per categoria (barre a 2 serie + tabella stato sforato/ok), spese eccezionali in evidenza, media mensile storica con grafico.

**Nota tecnica:** trovato e corretto durante la scrittura un pattern rischioso in Svelte 5 — una funzione che mutava lo state (`rowEdits`) dentro il markup durante il render (`{@const edit = initRowEdit(row)}`). Sostituito con un `$effect` che ricostruisce l'intero oggetto quando `monthRows` cambia, senza mutazioni durante il render.

**Deviazione:** la logica di "dati unificati" (Revolut + Notion) è duplicata da `Dashboard.svelte` invece di essere estratta in uno store condiviso — solo due punti d'uso finora, prematuro astrarre. Nessuna build di verifica lanciata su richiesta dell'utente (né qui né nelle altre sezioni di questa sessione) — da testare con `npm run dev` quando l'utente vorrà.
