# FinanceD

App desktop personale per la gestione delle finanze: importa automaticamente gli estratti conto Revolut, categorizza le spese, pianifica un budget mensile e traccia stipendi e ore lavorate.

Sviluppata con l'assistenza di [Claude Code](https://claude.com/claude-code) per l'implementazione — decisioni architetturali, ricerche e scelte di prodotto sono dell'autrice. I commit co-autorati sono visibili nella cronologia Git.

## Funzionalità

- **Import automatico Revolut** — carica l'estratto conto e le transazioni vengono categorizzate automaticamente
- **Pianificazione budget** — budget totale e per categoria, spese ricorrenti pianificate, modificabili mese per mese
- **Stipendi e turni** — registrazione ore lavorate e stipendi netti/lordi, con **previsione dello stipendio futuro**: una media pesata della tariffa oraria sui mesi passati (più peso ai mesi recenti) applicata alle ore già registrate
- **Bot Telegram** — registra una spesa scrivendo un messaggio in linguaggio naturale, interpretato da Gemini
- **Integrazione Splitwise** — amici, gruppi e spese condivise recuperati direttamente in app tramite le API di Splitwise
- **Rimborsi e risparmi** — tracciamento separato di rimborsi attesi e obiettivi di risparmio

## Architettura

```
┌─────────────┐         locale (127.0.0.1)        ┌──────────────┐
│  Electron   │ ───────────────────────────────── │   FastAPI    │
│  + Svelte   │      porta dinamica (findFreePort)  │  (Python)    │
└─────────────┘                                     └──────┬───────┘
                                                             │
                                                      Turso (libSQL)
                                                             │
┌─────────────┐         https + X-API-Token        ┌────────┴─────┐
│  App mobile │ ─────────────────────────────────── │   FastAPI    │
│ (in corso)  │                                      │  su Fly.io   │
└─────────────┘                                      └──────────────┘
```

L'app desktop lancia il backend in locale su una porta libera scelta dinamicamente (`electron/main.js`); nessuna autenticazione necessaria, il backend non è raggiungibile da fuori la macchina.

Per la futura versione mobile, lo stesso backend gira containerizzato su Fly.io (scelto perché non va mai in sleep) ed è protetto da un token condiviso: ogni richiesta deve portare l'header `X-API-Token` con un valore che corrisponde a una variabile d'ambiente lato server. Se la variabile non è impostata (caso desktop locale), il controllo è disattivato — stesso pattern usato per `TURSO_DATABASE_URL`.

Il database usa **Turso** (libSQL) invece di Postgres perché il progetto nasce dalla migrazione di una precedente app web in SQLite: restare nella stessa sintassi SQL evitava di riscrivere le query, ottenendo comunque accesso al database da internet.

## Stack

**Desktop:** Electron, Svelte, Vite
**Backend:** Python, FastAPI, Uvicorn
**Database:** Turso (libSQL / SQLite)
**Deploy backend hosted:** Docker, Fly.io
**CI/CD:** GitHub Actions — build firmate per macOS, supporto Linux

## Sviluppo locale

```bash
# Installa le dipendenze
npm install
pip install -r backend/requirements.txt

# Avvia frontend + Electron in parallelo
npm run dev
```

Il backend viene lanciato automaticamente da Electron in `dev`. Per lanciarlo separatamente:

```bash
cd backend
uvicorn main:app --reload
```

Variabili d'ambiente necessarie (vedi `backend/.env.example`):

- `TURSO_DATABASE_URL` / `TURSO_AUTH_TOKEN` — se assenti, l'app usa un database SQLite locale
- `GEMINI_API_KEY` — per il bot Telegram
- `SPLITWISE_API_KEY` — configurabile anche da Impostazioni dentro l'app
- `API_ACCESS_TOKEN` — solo per il deploy hosted (Fly.io); lasciare vuoto in locale

## Build e release

```bash
npm run build
```

Le release per macOS e Linux sono automatizzate tramite GitHub Actions (`.github/workflows/release.yml`), con build firmate. L'app è stata testata da compagni di corso su macchine reali prima del rilascio, individuando e correggendo diversi problemi di packaging.

## Nota sulla demo

Non c'è una demo pubblica: l'app gestisce dati finanziari reali dell'autrice. Screenshot e video del funzionamento sono disponibili nella pagina di dettaglio del portfolio, linkata qui sotto.

## Autrice

**Mariya Dyshkant**
[Portfolio](https://mariyadyshkant.com/progetti/financed) · [LinkedIn](https://www.linkedin.com/in/mariyadyshkant/)
