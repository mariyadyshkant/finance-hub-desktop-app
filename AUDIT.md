# Audit — FinanceD Desktop

Audit del repository eseguito il 30/09/2026 (commit `3b56e4f`). Copre repository/documentazione, qualità del codice, ADR, URL pubbliche e aree a rischio.

## Cosa è solido (da non toccare)

**Repository e documentazione.** Il README è accurato e allineato al codice reale — verificato riga per riga: l'architettura Electron+Svelte ↔ FastAPI locale ↔ Turso, il backend hosted su Fly.io con auth a token, tutto corrisponde esattamente a quello che `main.py`, `fly.toml` ed `electron/main.js` fanno davvero. Non è un README scritto e poi abbandonato.

**La cartella `.specs/plans/`** fa da ADR de facto: 18 documenti, uno per feature, ciascuno con problema/soluzione/verifica e checkbox di completamento. È un ottimo artefatto da mostrare in colloquio — dimostra un processo di lavoro tracciato, non solo codice. `feature-dynamic-backend-port.md` e `feature-mobile-backend-auth.md` in particolare sono scritti bene, con test concreti documentati (es. "con la 8000 occupata, trova correttamente 8001").

**Gestione porta dinamica e avvio backend** (`electron/main.js`): `findFreePort` + polling su `/health` prima di aprire la finestra è una soluzione pulita a un bug reale già affrontato in produzione (conflitti con `php artisan serve` ecc.), con commenti che spiegano il *perché*, non solo il *cosa*.

**Sicurezza base**: `.env` e `*.db` sono in `.gitignore`, l'auth a token sul backend hosted è opt-in e ben isolata (stesso pattern di `TURSO_DATABASE_URL`), verificata con test reali (200/401) documentati nello spec.

**Backend FastAPI**: file piccoli e ben separati per dominio (`routes/salary.py`, `routes/savings.py` ecc., tutti sotto 100 righe). `main.py` è leggibile, 122 righe, responsabilità chiare.

## Cosa è fragile o incompleto (da sistemare)

**File troppo lunghi lato frontend**: `Pianificazione.svelte` (925 righe), `Stipendi.svelte` (724), `Dashboard.svelte` (678), `Impostazioni.svelte` (662). Componenti Svelte monolitici che probabilmente mischiano logica, stato e markup. Non urgente per una demo, ma se qualcuno guarda il codice, questi file saltano subito all'occhio come "da rifattorizzare" — vale la pena scomporli in sotto-componenti prima di mandare il link a qualcuno.

**`backend/database.py`** (666 righe): un unico file con tutte le query per tutte le entità (transazioni, rimborsi, risparmi, turni, budget, categorie...). Funziona, ma è il classico "god file" — separarlo per dominio (come già fatto per le routes) sarebbe un miglioramento naturale.

**`backend/telegram_bot.py`** (773 righe): il file backend più grande del progetto. Vale la pena dargli un'occhiata mirata — è tipicamente dove si annidano edge case (parsing con Gemini, retry di coda, gestione errori di rete).

**Database duale non banale**: SQLite locale come fallback e Turso come cloud, selezionati dinamicamente in `get_conn()`. Funziona, ma è una superficie in più dove un bug di sincronizzazione (dati diversi tra desktop e bot Telegram) potrebbe comparire silenziosamente — area a rischio più che problema confermato.

## Cosa manca per essere "pronto per una demo"

**Le URL pubbliche rispondono.** Testato `https://financed-backend.fly.dev/health`: è live, risponde `{"status":"ok"}`. È un asset concreto da mostrare: prova che il progetto non è solo locale, ma ha un componente reale deployato e raggiungibile da internet, con autenticazione funzionante (documentata e testata anche con token sbagliato → 401).

La pagina portfolio `mariyadyshkant.com/progetti/financed` non è stata verificabile nel contenuto (SPA renderizzata via JS) — da controllare a mano nel browser per assicurarsi che la pagina di dettaglio con screenshot/video esista davvero e sia collegata dal README.

**Sulla demo pubblica dell'app in sé**: il README dichiara esplicitamente che non c'è, perché l'app gestisce dati finanziari reali dell'autrice. Scelta di design legittima e motivata, non una lacuna — in un colloquio è anzi un buon segnale (consapevolezza su privacy/dati sensibili). L'unica cosa da sistemare: assicurarsi che gli screenshot/video citati nel README siano effettivamente presenti nella pagina portfolio, dato che quel link è ora l'unico modo per chi legge il repo di vedere l'app funzionare.
