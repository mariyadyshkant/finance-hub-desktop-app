# Feature: Sezione Storico Notion

## Obiettivo

Sostituire il placeholder di `StoricoNotion.svelte` con la UI reale, a parità di funzionalità con `finance-hub/pages/7_📓_Storico_Notion.py`: import file .md esportato da Notion (con mapping categorie già gestito lato backend), inserimento manuale mese per mese.

## Dipendenze

- Backend `routes/summaries.py` già pronto (GET, GET months, POST parse, POST upsert, DELETE month), nessuna modifica prevista.

## Stack

- Solo frontend, nessuna dipendenza nuova.

## Output atteso

- Import: incolla testo esportato da Notion → anteprima mese + categorie riconosciute (modificabili prima di confermare) → import.
- Inserimento manuale: seleziona/scrivi un mese, inserisci importo per categoria, salva.
- Elenco mesi importati con totale e possibilità di eliminare l'intero mese.

## Status

[x] Completata

**Completata il:** 2026-07-31

**Cosa è stato fatto:** `StoricoNotion.svelte` — import: incolla testo export → analizza (POST `/summaries/parse`) → anteprima mese+categorie con importi modificabili prima di confermare → import (upsert per categoria). Inserimento manuale: selettore mese + griglia di importi per categoria (precompilata se il mese ha già dati), salvataggio upsert. Elenco mesi con totale ed elimina. Categorie non-spesa (Entrata/Rimborso ricevuto/Altro) escluse dalla griglia manuale, coerente con Transazioni/Dashboard.

**Nota:** aggiunte le icone `upload`/`download`/`filter`/`info`/`piggy-bank` a `icons.js` in previsione delle sezioni ancora da fare (Risparmi già usa solo icone esistenti). Nessuna build di verifica lanciata su richiesta dell'utente.
