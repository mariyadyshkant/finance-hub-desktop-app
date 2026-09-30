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

[x] Completata

**Completata il:** 2026-09-30

**Cosa è stato fatto:**
- `Pianificazione.svelte` (925 → 244 righe): estratti 3 sotto-componenti per
  tab in `lib/components/planning/` — `SpesePianificate.svelte`,
  `Budget.svelte`, `Consuntivo.svelte`. Il parent resta proprietario del
  caricamento dati e dei derived condivisi tra tab (`unifiedRows`,
  `catAverages`, `monthRows`, ecc.).
- `Stipendi.svelte` (724 → 92 righe): estratti 3 sotto-componenti per tab in
  `lib/components/salary/` — `OreTurni.svelte`, `StoricoStipendi.svelte`,
  `Previsione.svelte`.
- `Dashboard.svelte` (678 → 266 righe): estratti 7 sotto-componenti (un
  grafico/riepilogo ciascuno) in `lib/components/dashboard/` —
  `ImportRevolut`, `KpiRow`, `CategoryBreakdownChart`, `DailyTrendChart`,
  `ConfrontoMensileChart`, `AndamentoCategoriaChart`, `MediaMensileChart`.
- `Impostazioni.svelte` (662 → 63 righe): estratte 3 card in
  `lib/components/settings/` — `ProfileCard`, `SplitwiseCard`,
  `CategorieCard` (quest'ultima la più grossa, CRUD categorie + icon picker).
  Per i due campi con binding a due vie (`displayName`,
  `splitwiseConfigured`) introdotto `$bindable()` — primo uso nel progetto,
  scelto invece di far ricaricare i dati al genitore dopo ogni salvataggio.
- Pattern comune: i parent restano responsabili del data loading (`api.get`)
  e passano dati + callback (`onchange`, `onerror`) ai figli; i figli con
  CRUD locale (form aggiungi/modifica/elimina) chiamano l'API direttamente e
  invocano il callback per far ricaricare il genitore — stesso pattern già
  in uso in `TransactionRow.svelte`.
- Verifica: `npm run build` pulito dopo ogni file scomposto (4 build
  separate). Assente un browser automation tool in questo ambiente per un
  test visivo diretto — verificato invece che ogni nuovo componente
  compili senza errori lato dev server Vite (richiesta diretta ai moduli
  `.svelte`, tutti 200 OK, nessun errore nei log) e che tutti gli endpoint
  backend consumati rispondano con la forma dati attesa, testato contro il
  backend reale (Turso) in esecuzione locale.

**Deliberatamente fuori scope:**
- Nessun cambio di logica o UI: solo riorganizzazione in componenti più
  piccoli, stile CSS scoped duplicato dove necessario (comportamento normale
  di Svelte, non un'astrazione CSS condivisa introdotta ad hoc).
- Nessun test automatico in browser reale: non disponibile un tool di
  automazione browser in questo ambiente. Verifica manuale nel browser
  dell'app consigliata prima di considerare la UI definitivamente testata.
