# Feature: Sezione Dashboard

## Obiettivo

Sostituire il placeholder di `Dashboard.svelte` con la UI reale, a parità di funzionalità con `finance-hub/pages/1_📊_Dashboard.py` (Streamlit): KPI mensili, import Revolut, grafici di spesa per categoria/mese/andamento.

## Dipendenze

- Sezione Transazioni e design system già completati.
- Backend: `GET /api/transactions`, `GET /api/summaries`, `GET /api/summaries/months`, `GET /api/planning/budget/{month}` — tutti già esposti, nessuna modifica prevista.

## Stack

- **Chart.js** aggiunto come dipendenza frontend (prima libreria di terze parti nel frontend) — necessario per grafici a barre/linee multi-serie, troppo lavoro/fragile da rifare a mano in SVG. Wrapper riusabile `lib/components/Chart.svelte`.
- Seguite le linee guida della skill `dataviz`: niente torta per 18 categorie (soglia "~7 classi" superata) → barra orizzontale ordinata con etichette dirette; coppie a 2 serie (budget/reale, media/mese, Revolut/Notion) con colori fissi invece di generare tinte nuove.

## Output atteso

- Selettore mese (unione mesi Revolut + Notion), import Revolut (PDF/CSV).
- KPI: totale spese, entrate, saldo, spese senza affitto.
- Spese per categoria: barra orizzontale ordinata (colori categoria esistenti, etichette dirette — non torta).
- Andamento giornaliero (solo mesi Revolut).
- Confronto ultimi mesi (colorato per fonte Revolut/Notion).
- Andamento per categoria (selezione utente, max ~6 per leggibilità).
- Media mensile per categoria e budget vs reale (barre a 2 serie).

## Status

[x] Completata

**Completata il:** 2026-07-31

**Cosa è stato fatto:**
- `frontend/src/lib/components/Chart.svelte`: wrapper riusabile su Chart.js (crea/distrugge l'istanza in un `$effect`, responsive).
- `frontend/src/lib/chartTheme.js`: token colore condivisi per i grafici (Chart.js non legge le custom property CSS).
- `Dashboard.svelte`: selettore mese, import Revolut (PDF/CSV) con anteprima prima di confermare, 4 KPI, spese per categoria (barra orizzontale invece di torta — 18 categorie superano la soglia "~7 classi" della skill dataviz), andamento giornaliero (solo mesi Revolut), confronto ultimi mesi (colorato per fonte), andamento per categoria (selezione utente, max 6), media mensile per categoria (colore su stato: rosso se sopra media, verde se sotto).
- Palette "fonte dati" (Revolut/Notion) validata con lo script della skill dataviz (`validate_palette.js`) — l'accento generale dell'app da solo falliva la soglia minima di saturazione (troppo desaturato per fare identità in un grafico), sostituito con un blu più saturo solo nel contesto grafici, interfaccia generale invariata.
- **Deliberatamente non incluso qui**: "Budget vs spese reali" — ora coperto dal tab Consuntivo della sezione Pianificazione (completata in questa stessa sessione), che usa il sistema di budget mensile più recente invece della vecchia tabella flat `budgets` di Streamlit.

**Non ancora fatto:** test con dati reali/build di verifica — l'utente ha chiesto di non lanciare `npm run build` automaticamente dopo ogni modifica, lo farà lei con `npm run dev` quando vorrà (stessa nota per tutte le sezioni completate in questa sessione).
