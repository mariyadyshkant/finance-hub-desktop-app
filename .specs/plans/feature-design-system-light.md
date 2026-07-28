# Feature: Design system chiaro (allineato a wireframe di riferimento)

## Obiettivo

Definire un'estetica condivisa (variabili CSS: colori, spaziature, radius, font, icone) prima di costruire altre sezioni, così i componenti futuri la usano fin da subito invece di essere riallineati dopo.

## Dipendenze

- Sezione Transazioni già costruita (va riallineata al nuovo sistema, unico pezzo di UI reale esistente).
- `backend/importers/helpers.py` — `CAT_COLORS` è la fonte unica dei colori categoria, già esposta via `GET /api/categories` e consumata dal frontend.
- Wireframe di riferimento fornito dall'utente: `frontend/design-system/TransactionsCompactLayout.png` + `wireframe-details.html` (contiene i token esatti: colori, font Inter/Geist, spaziature, radius, set di icone SVG).

## Stack

- Solo CSS (variabili custom in `frontend/src/app.css`) + un piccolo set di icone SVG scritte a mano (`frontend/src/lib/icons.js` + `Icon.svelte`), nessuna libreria di icone come dipendenza.
- Font Inter + Geist via Google Fonts (`frontend/index.html`), con fallback su system font se offline.

## Output atteso

- `app.css` con token allineati al wireframe: sfondo `#f8f9fa`, superfici bianche, testo `#271d6b`, accento indaco `#6966a0`, radius 4/8/12px, niente ombre (solo bordi 1px).
- Nuova palette `CAT_COLORS` (18 colori, stile "badge pastello + testo saturo") aggiornata in `backend/importers/helpers.py`.
- Icone lineari SVG al posto delle emoji in sidebar, righe transazioni, azioni.
- `Sidebar.svelte`, `App.svelte`, `Transazioni.svelte`, `TransactionRow.svelte` e i placeholder delle altre 6 sezioni riallineati ai nuovi token.
- Tabella Transazioni con intestazione e colonne perfettamente allineate ai dati sottostanti.

## Status

[x] Completata

**Completata il:** 2026-07-28

**Cosa è stato fatto:**
- Prima iterazione: tema scuro "moody" (gradiente di sfondo, bordo laterale colorato per categoria, tipografia più marcata) — costruito, verificato con screenshot reali (Playwright/Chromium headless contro il dev server Vite), poi **scartato**: l'utente ha fornito un wireframe di riferimento in tema chiaro, opposto alla direzione presa.
- Riscrittura completa in tema chiaro seguendo esattamente i token del wireframe (colori, font Inter/Geist, spaziature, radius 4/8/12px, nessuna ombra).
- Creato un set minimale di icone SVG (`icons.js` + `Icon.svelte`) in stile Lucide, per sostituire le emoji senza aggiungere una libreria come dipendenza.
- Palette `CAT_COLORS` (18 colori) riscritta in stile "badge pastello + testo saturo" (Tailwind-ish, tonalità -700), estendendo coerentemente i 6-7 esempi del wireframe a tutte le categorie dell'app.
- Sidebar, header Transazioni (ricerca/selettore mese/aggiungi), stat card, filtri a pillole (tipo separato da categorie, vedi sotto), tabella con intestazione — tutti ricostruiti seguendo la struttura del wireframe.
- Diverse iterazioni di rifinitura guidate dall'utente via editing diretto dei file + richieste puntuali: classe `.status-pill-group` separata da `.pill-group` (categorie) per poter avere onclick/stile indipendenti; barra di stato attiva più corta e centrata (`::after` con `scaleX`) invece del `border-bottom` a piena larghezza; rimossi dai filtri categoria "Entrata"/"Rimborso ricevuto"/"Altro" (restano nel form aggiungi/modifica); box di ricerca ristretto (140px, con `min-width:0` sugli input per evitare overflow orizzontale in finestra stretta); colonne Categoria/Data/Importo portate alla stessa larghezza (150px) e centrate, sia in intestazione che nelle righe.
- Bug di allineamento intestazione tabella: causato da un `margin-left` che l'utente ha aggiunto alla classe globale `.eyebrow` (per le stat card) e che si propagava anche alle intestazioni della tabella — risolto con un override mirato `.table-header .eyebrow { margin-left: 0; }` senza toccare la classe globale.

**Nota importante:** i file di riferimento del wireframe erano stati messi in `frontend/dist/assets/` (cartella di build, rigenerata e ripulita ad ogni `npm run build`) — sono stati cancellati da una delle mie build di verifica. Il contenuto era già stato letto per intero prima che succedesse, quindi nessuna informazione persa per il lavoro; l'utente ha poi rimesso le copie in `frontend/design-system/` (fuori dalla cartella di build).
