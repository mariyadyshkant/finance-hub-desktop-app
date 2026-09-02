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

- **Dashboard**: il "Totale spese" del mese *è* transazioni + spese pianificate
  del mese (override inclusi), con sotto `€X transazioni + €Y pianificate`. Quel
  totale combinato alimenta tutti i calcoli e i grafici del mese selezionato
  (Saldo, Senza affitto, "Spese per categoria", "Confronto ultimi mesi",
  "Andamento per categoria", "Media mensile per categoria") — **tranne**
  l'andamento giornaliero (le pianificate non hanno una data). Le pianificate
  entrano solo nel mese selezionato, non retroattivamente negli altri mesi dei
  grafici di confronto. Rimosso `AFFITTO = 280`: "Senza affitto" = totale
  combinato meno tutto ciò che è in categoria "Affitto" quel mese (transazioni
  + pianificate), mostrato con `−` davanti. La lista transazioni non cambia.
- **Transazioni**: accanto al "Totale spese" del mese compare
  `+ €X pianificate → €Y con pianificate` (il totale in cima resta la somma
  delle sole transazioni filtrate).
- **Transazioni**: il selettore mese si popola all'apertura della pagina
  (`GET /transactions/months` in `$effect`, prima chiamato solo dopo un
  inserimento).
- **Pianificazione → Budget**: mostra *tutte* le categorie di spesa, ordinate
  per media storica decrescente (prima solo quelle con storico o budget già
  impostato).
- **Impostazioni → Categorie**: lista con icona + pallino colore + nome;
  aggiungi (nome + color picker + icon picker), rinomina, cambia colore, cambia
  icona, elimina (con `select` della categoria di destinazione). Rinomina/elimina
  propagano a cascata sulle tabelle che referenziano la categoria per nome.
- **Icona per categoria**: nuova colonna `categories.icon` (nome icona di
  `frontend/src/lib/icons.js`, default `repeat`, seed da `CAT_ICONS` in
  `importers/helpers.py`). `GET /api/categories` restituisce anche `icons`.
  `TransactionRow.svelte` usa la mappa `icons` dal backend invece della vecchia
  `CATEGORY_ICONS` hardcoded.

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
- Frontend: `Dashboard.svelte` inietta le spese pianificate del mese in
  `rowsWithPlanned` (righe unificate + pianificate), da cui derivano `totSpese`,
  `saldo`, `senzaAffitto`, `categoryBreakdown`, `monthlyTotals`,
  `trendChartData`, `avgVsMonth` — l'andamento giornaliero resta su `allTx`.
  Rimosso `AFFITTO = 280`, `senzaAffitto = totSpese − somma categoria Affitto`.
  `Transazioni.svelte` carica `/planning/planned-expenses` +
  `/planning/overrides/{mese}` e mostra il totale pianificato accanto (senza
  fonderlo nel totale in cima), e carica i mesi all'apertura.
  `Pianificazione.svelte`: `budgetCatKeys` = tutte le categorie di spesa
  ordinate per media. `Impostazioni.svelte`: nuova card "Categorie" (CRUD
  completo).
- Verifica: `npm run build` frontend OK; due script di test backend su SQLite
  temporanea (CRUD + cascata rinomina/elimina su transazioni, riepiloghi,
  pianificate, `monthly_budgets` JSON; casi 404/409/400) — tutti verdi; smoke
  test `POST`/`PUT`/`DELETE` sul backend dev vivo (Turso) OK.

**Deliberatamente fuori scope:**
- Feature toggle accendi/spegni sezioni (l'utente ha scelto "solo categorie per
  ora").
- Rendere `categorize()` consapevole delle categorie rinominate/eliminate — per
  un'app mono-utente il costo non vale il beneficio; documentato in ADR.
- (revisione 2026-09-02, stessa sessione) su richiesta dell'utente il totale
  combinato entra ovunque nella Dashboard tranne l'andamento giornaliero, e
  "Senza affitto" ora sottrae la categoria "Affitto" reale invece del vecchio
  valore fisso di 280.
