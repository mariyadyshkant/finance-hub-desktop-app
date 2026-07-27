# Feature: Sezione Transazioni (UI completa)

## Obiettivo

Sostituire il placeholder di `Transazioni.svelte` con la UI reale, a parità di funzionalità con `finance-hub/pages/2_💳_Transazioni.py` (Streamlit): lista filtrabile, aggiunta manuale, modifica, spesa condivisa (con rimborso automatico), rimborso diretto, eliminazione.

## Dipendenze

- Backend `routes/transactions.py` e `routes/reimbursements.py` (già scritti nello scaffolding, nessuna modifica prevista).
- `GET /api/categories` per lista categorie + colori (già esposto).

## Stack

- Solo frontend: Svelte 5 (runes), nessuna nuova dipendenza.
- Split in due componenti: `routes/Transazioni.svelte` (filtri, form aggiunta, lista) e `lib/components/TransactionRow.svelte` (riga singola + azioni inline: modifica / spesa condivisa / rimborso / elimina) — la logica per riga è abbastanza densa da giustificare l'estrazione.

## Output atteso

- Selettore mese (Tutti i mesi + mesi disponibili).
- Form "aggiungi spesa/entrata manuale".
- Filtri: ricerca testo, categoria (multi), tipo (tutto/solo spese/solo entrate).
- Lista transazioni con badge categoria colorato, importo colorato (rosso spesa/verde entrata).
- Azioni per riga: modifica campi, marca come "spesa condivisa" (calcola quota, aggiorna importo transazione alla quota, crea rimborso automatico per la differenza — stessa logica di `database.py`/Streamlit), crea rimborso diretto, elimina con conferma.

## Status

[x] Completata

**Completata il:** 2026-07-28

**Cosa è stato fatto:**
- `Transazioni.svelte`: selettore mese, form aggiunta manuale, filtri (ricerca, categoria a chip multi-select, tipo), riepilogo totale spese, lista.
- `lib/components/TransactionRow.svelte`: riga con azioni inline (modifica, spesa condivisa con calcolo quota/rimborso automatico, rimborso diretto, elimina con conferma).
- Categorie e colori presi da `GET /api/categories` invece di essere hardcoded lato frontend.
- Verificato con round-trip reale contro Turso: add → edit → spesa condivisa (aggiorna importo transazione + crea rimborso collegato via `transaction_id`) → delete, nessun residuo.

**Deviazione dal comportamento originale (bug fix):** nella pagina Streamlit originale, il badge 🔀 per le spese condivise cercava la stringa `"quota:"` nella nota, ma la nota generata dal flusso stesso è `"condivisa: pagato €X, mia quota €Y"` — non contiene mai quel pattern, quindi il badge non scattava mai (bug preesistente, invisibile). Nella versione Svelte il controllo usa `note.startsWith("condivisa")`, che effettivamente matcha.
