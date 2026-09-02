# Feature: correzioni QoL — issue-qol-1

## Obiettivo

Quattro sistemazioni segnalate dall'utente sull'app desktop:

1. Le spese pianificate del mese devono comparire accanto al "Totale speso" ed
   essere conteggiate (non nella lista transazioni).
2. In Transazioni non si riusciva a selezionare il mese.
3. In Budget (Pianificazione) non comparivano tutte le categorie.
4. Poter aggiungere / rinominare / eliminare le categorie dall'app
   (Impostazioni).

## Dipendenze

- Nessuna. Tutte le sezioni toccate esistono già.

## Stack

- Frontend Svelte 5 + backend FastAPI, coerente con l'ADR. Nessuna dipendenza
  nuova. Nuova tabella `categories` nel DB (stesso pattern chiave/valore-free
  delle altre: `CREATE TABLE IF NOT EXISTS` + seed idempotente).

## Output atteso

- **Dashboard** e **Transazioni**: sotto/accanto al "Totale spese" del mese
  selezionato compare `+ €X pianificate → €Y con pianificate` quando ci sono
  spese pianificate (override del mese inclusi). La lista transazioni non
  cambia.
- **Transazioni**: il selettore mese si popola all'apertura della pagina
  (`GET /transactions/months` in `$effect`, prima chiamato solo dopo un
  inserimento).
- **Pianificazione → Budget**: mostra *tutte* le categorie di spesa, ordinate
  per media storica decrescente (prima solo quelle con storico o budget già
  impostato).
- **Impostazioni → Categorie**: lista con pallino colore + nome; aggiungi
  (nome + color picker), rinomina, elimina (con `select` della categoria di
  destinazione). Rinomina/elimina propagano a cascata sulle tabelle che
  referenziano la categoria per nome.

## Status

[x] Completata

**Completata il:** 2026-09-02

**Cosa è stato fatto:**
- Backend: tabella `categories` + `init_categories()` (seed dai default di
  `importers/helpers.py` se vuota) in `database.py`; helper
  `get_categories`/`add_category`/`set_category_color`/`rename_category`/
  `delete_category` + `_remap_budget_json` per le chiavi JSON di
  `monthly_budgets`. Nuovo `routes/categories.py` (`POST` / `PUT /{name}` /
  `DELETE /{name}?reassign_to=`). `main.py`: `GET /api/categories` ora legge dal
  DB (stessa forma di risposta), `init_categories()` in startup, router
  registrato. Rimosso l'import ora inutile di `CATEGORIES`/`CAT_COLORS` in
  `main.py`.
- Frontend: `Dashboard.svelte` e `Transazioni.svelte` caricano
  `/planning/planned-expenses` + `/planning/overrides/{mese}` e mostrano il
  totale pianificato accanto al totale spese. `Transazioni.svelte` carica i
  mesi all'apertura. `Pianificazione.svelte`: `budgetCatKeys` = tutte le
  categorie di spesa ordinate per media. `Impostazioni.svelte`: nuova card
  "Categorie" (CRUD completo).
- Verifica: `npm run build` frontend OK; due script di test backend su SQLite
  temporanea (CRUD + cascata rinomina/elimina su transazioni, riepiloghi,
  pianificate, `monthly_budgets` JSON; casi 404/409/400) — tutti verdi; smoke
  test `POST`/`PUT`/`DELETE` sul backend dev vivo (Turso) OK.

**Deliberatamente fuori scope:**
- Feature toggle accendi/spegni sezioni (l'utente ha scelto "solo categorie per
  ora").
- Rendere `categorize()` consapevole delle categorie rinominate/eliminate — per
  un'app mono-utente il costo non vale il beneficio; documentato in ADR.
- `plannedTotal` non entra in "Saldo" / "Senza affitto": la richiesta era solo
  sul "Totale speso".
