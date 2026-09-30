# Feature: scomposizione componenti Svelte monolitici — issue-audit-1

## Obiettivo

Dall'audit del repo (30/09/2026, commit `3b56e4f`, vedi `AUDIT.md`): quattro
componenti frontend sono cresciuti troppo e mischiano logica, stato e markup
nello stesso file:

- `Pianificazione.svelte` — 925 righe
- `Stipendi.svelte` — 724 righe
- `Dashboard.svelte` — 678 righe
- `Impostazioni.svelte` — 662 righe

Non blocca una demo, ma sono i primi file su cui cade l'occhio di chi legge il
codice come "da rifattorizzare". Vale la pena scomporli prima di condividere
il link del repo.

## Dipendenze

- Nessuna. Nessuna modifica di comportamento prevista, solo riorganizzazione.

## Stack

- Frontend Svelte 5, coerente con l'ADR. Nessuna dipendenza nuova.

## Output atteso

- Per ciascuno dei 4 file: estrarre sotto-componenti coesi (es. per
  `Dashboard.svelte` separare i singoli grafici/riepiloghi; per
  `Pianificazione.svelte` separare Budget da Consuntivo; per
  `Impostazioni.svelte` separare le singole card/sezioni; per
  `Stipendi.svelte` separare form di inserimento da storico/riepiloghi).
- Stato condiviso tra sotto-componenti via props/eventi o store dedicato dove
  serve, mantenendo lo stile già in uso nel resto del progetto.
- Nessuna regressione funzionale: comportamento identico prima/dopo, verificato
  a mano pagina per pagina.
- `npm run build` pulito.

## Status

[ ] Da fare
