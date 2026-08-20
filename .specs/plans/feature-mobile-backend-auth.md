# App mobile — Parte 1: token opt-in + deploy Fly.io per il backend

Prima tappa del piano approvato per l'app mobile (React Native + Expo),
salvato in `/Users/mariyadyshkant/.claude/plans/sprightly-tumbling-lantern.md`.
Questa parte resta in questo repo (`finance-hub-desktop-app`): prepara il
backend esistente a essere raggiungibile da internet (hosted su Fly.io),
senza toccare il comportamento dell'app desktop.

## Cosa serve e perché

Il backend FastAPI oggi gira solo in locale, spawnato da Electron,
raggiungibile solo su `127.0.0.1`. Un telefono non può avviare un processo
Python sul Mac dell'utente — serve un'istanza sempre accesa e raggiungibile
da internet. Ma un backend raggiungibile da internet senza nessuna
protezione esporrebbe dati finanziari a chiunque conosca l'URL — serve
un'autenticazione minima, proporzionata a un'app mono-utente (non OAuth
completo).

## Cosa ho fatto

1. **`backend/main.py`**: middleware FastAPI che controlla l'header
   `X-API-Token` contro `os.getenv("API_ACCESS_TOKEN")`. Stesso pattern già
   usato per `TURSO_DATABASE_URL`: se la variabile non è impostata (caso
   desktop locale, invariato), il middleware non fa nulla — zero impatto
   sull'app esistente. Se è impostata (caso Fly.io), ogni richiesta senza
   l'header corretto riceve `401`, eccetto `/health` (serve ai controlli di
   Fly.io stesso, non espone dati).
2. **`backend/Dockerfile`**: `python:3.12-slim`, installa `requirements.txt`,
   espone la porta 8080 (convenzionale Fly.io, distinta dalla porta dinamica
   usata dal desktop — vedi `electron/main.js: findFreePort`).
3. **`backend/fly.toml`**: config minima (`internal_port = 8080`,
   `force_https = true`, `min_machines_running = 1` per restare sempre
   accesa).
4. **`backend/.dockerignore`**: esclude venv, `.env`, `finance.db` locale,
   build artifacts.
5. **`.env.example`**: documentata `API_ACCESS_TOKEN` (vuota per il
   desktop, da generare con `openssl rand -hex 32` solo per l'hosting).

Nessuna modifica a `database.py`/`routes/*`: già tutti compatibili, dato
che il client Turso HTTP esiste già (stesso codice usato dal desktop per
la sincronizzazione cloud).

## Verifica

Testato il middleware direttamente con `uvicorn` in locale (non serve
Docker per questo):
- **Senza** `API_ACCESS_TOKEN`: `/api/categories` risponde `200` come
  sempre (nessun impatto sul comportamento desktop).
- **Con** `API_ACCESS_TOKEN=secret123`: richiesta senza header → `401`;
  con header sbagliato → `401`; con header corretto → `200`; `/health`
  senza header → `200` (esclusa, come da design).

**Deploy Fly.io completato e verificato** (2026-08-20): l'utente ha creato
l'app `financed-backend` su Fly.io (regione `fra`), aggiunto un metodo di
pagamento (richiesto da Fly.io anche per l'uso hobby/gratuito — non
aggirabile), impostato i secret `TURSO_DATABASE_URL`/`TURSO_AUTH_TOKEN`/
`API_ACCESS_TOKEN` e deployato. Verificato con `curl` da questa parte:
- `GET /health` senza token → `200` (esente, come da design)
- `GET /api/categories` senza token → `401`
- `GET /api/transactions` con `X-API-Token` corretto → `200`, con le
  transazioni reali dell'utente — conferma che il backend hosted legge
  dallo stesso Turso del desktop, dati sincronizzati tra i due.

URL pubblico: `https://financed-backend.fly.dev`.

## Prossimi passi

- Parte 2: scaffold Expo nel nuovo repo `financed-mobile`, usando questo
  URL + il token come credenziali di connessione salvate con
  `expo-secure-store` alla prima configurazione dell'app.

- [x] Completata (2026-08-20) — inclusa la verifica end-to-end del deploy Fly.io
