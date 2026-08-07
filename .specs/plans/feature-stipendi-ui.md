# Feature: Sezione Stipendi & Ore lavorate

## Obiettivo

Sostituire il placeholder di `Stipendi.svelte` con la UI reale, a parità di funzionalità con `finance-hub/pages/5_📅_Stipendi.py`: 3 tab (Ore & Turni, Stipendi, Previsione).

## Dipendenze

- Backend `routes/shifts.py` (GET/POST/DELETE turni, parse testo Note Apple, import bulk) e `routes/salary.py` (GET/POST/DELETE stipendi) già pronti, nessuna modifica prevista.
- `Chart.svelte`/`chartTheme.js` già costruiti per la Dashboard, riusati qui.

## Stack

- Solo frontend, nessuna dipendenza nuova.

## Output atteso

- **Ore & Turni**: import da testo Note Apple (con anteprima), aggiunta turno manuale, riepilogo ore/mese con grafico, tabella turni con elimina.
- **Stipendi**: aggiunta stipendio (mese/netto/lordo/ore), statistiche (media/max/min), grafico netto per mese, tabella con elimina.
- **Previsione**: tariffa oraria media pesata (mesi recenti pesano di più), grafico andamento tariffa con riferimento alla media, previsione per mesi con turni ma senza stipendio registrato, calcolatore previsione personalizzato.

## Status

[x] Completata

**Completata il:** 2026-07-31

**Cosa è stato fatto:** `Stipendi.svelte` con 3 tab. Ore & Turni: import testo Note Apple con anteprima prima di confermare, aggiunta manuale (calcolo ore da orari testo libero, stessa logica flessibile dell'originale), selettore mese, KPI (ore totali/turni/media), grafico ore/giorno, elenco con elimina. Stipendi: aggiunta (mese/netto/lordo opz./ore opz.), statistiche media/max/min, grafico netto/mese, storico con elimina. Previsione: tariffa oraria media pesata (pesi 1..N in ordine cronologico), grafico andamento con riferimento alla media (linea tratteggiata come secondo dataset, nessun plugin aggiuntivo), mesi con turni ma senza stipendio registrato con previsione, calcolatore personalizzato. Nessuna build di verifica lanciata su richiesta dell'utente.
