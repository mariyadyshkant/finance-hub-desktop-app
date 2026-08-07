# Porta backend dinamica (via 8000 fissa)

## Problema

Il backend FastAPI parte sempre sulla porta 8000, sia in sviluppo che nella
build pacchettizzata (`electron/main.js` passava `--port 8000` fisso, e
l'eseguibile PyInstaller aveva `port=8000` hardcoded in `main.py`). Se
sulla macchina dell'utente qualcos'altro occupa già la 8000 (un altro
backend locale, `php artisan serve`, ecc. — esattamente lo scenario che ha
causato i bug riportati in v0.1.0/v0.1.1, con pagine d'errore Laravel/
Werkzeug al posto delle risposte FastAPI), il nostro backend non riesce a
partire, e senza gestione esplicita l'app resterebbe rotta.

## Fix

1. `backend/main.py`: l'entry point PyInstaller legge la porta da
   `os.getenv("PORT", "8000")` invece di usare `8000` hardcoded.
2. `electron/main.js`: aggiunta `findFreePort()` — prova a fare il bind su
   127.0.0.1 partendo da 8000, incrementando finché non trova una porta
   libera (max 20 tentativi). Il risultato viene passato al processo
   backend sia in sviluppo (`--port` di uvicorn) sia in produzione
   (env var `PORT` per l'eseguibile PyInstaller).
3. La porta scelta viene esposta al renderer via `ipcMain.handle("get-backend-port", ...)`
   + `contextBridge` in `electron/preload.js` (`window.financedAPI.getBackendPort()`).
4. `frontend/src/lib/api.js`: la base URL non è più una costante
   `http://127.0.0.1:8000/api` ma viene risolta in modo asincrono e
   cachata alla prima chiamata, leggendo la porta da `financedAPI` (con
   fallback a 8000 se l'app gira fuori da Electron, es. `vite dev` in un
   browser normale). `Dashboard.svelte` (upload Revolut, unico altro punto
   con un `fetch` diretto invece di passare da `api.js`) aggiornato allo
   stesso pattern.

## Verifica

- Logica di ricerca porta libera testata in isolamento con Node: con la
  8000 occupata, `findFreePort` seleziona correttamente 8001.
- Eseguibile PyInstaller testato direttamente con `PORT=8123`: si avvia e
  risponde su quella porta (log uvicorn conferma `Uvicorn running on
  http://127.0.0.1:8123`).
- `npm run build:frontend` pulito, nessun errore di compilazione nei file
  toccati.
- **Non verificato in questa sessione**: rilancio end-to-end dell'app
  Electron pacchettizzata con la 8000 occupata (l'ambiente sandbox di
  questa sessione ha smesso di aprire finestre GUI persistenti a metà
  sessione — confermato non essere una regressione del fix, perché anche
  la build precedente, già verificata funzionante poco prima nella stessa
  sessione, ha mostrato lo stesso comportamento). Da verificare dall'utente
  al prossimo avvio reale dell'app, o da me in una sessione successiva con
  ambiente GUI funzionante.

- [x] Completata (2026-08-07) — verifica end-to-end GUI da confermare
