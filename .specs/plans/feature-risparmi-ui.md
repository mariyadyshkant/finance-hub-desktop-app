# Feature: Sezione Risparmi

## Obiettivo

Sostituire il placeholder di `Risparmi.svelte` con la UI reale, a parità di funzionalità con `finance-hub/pages/6_🐷_Risparmi.py`: saldo cumulativo con grafico area, aggiunta entrata/uscita con etichetta, storico movimenti.

## Dipendenze

- Backend `routes/savings.py` già pronto (GET/POST/DELETE), nessuna modifica prevista.
- `Chart.svelte`/`chartTheme.js` riusati dalla Dashboard.

## Stack

- Solo frontend, nessuna dipendenza nuova.

## Output atteso

- Saldo cumulativo attuale (KPI).
- Grafico area/linea del saldo cumulativo nel tempo.
- Form aggiunta movimento (data, importo con segno, etichetta, note).
- Storico movimenti con elimina.

## Status

[x] Completata

**Completata il:** 2026-07-31

**Cosa è stato fatto:** `Risparmi.svelte` — KPI saldo attuale, grafico area del saldo cumulativo (somma progressiva ordinata per data), form aggiunta movimento (importo con segno, etichetta, note), storico con elimina. Nessuna build di verifica lanciata su richiesta dell'utente.
