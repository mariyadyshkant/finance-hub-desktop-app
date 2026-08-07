# Feature: Backend portabile (PyInstaller)

## Obiettivo

Far funzionare la build di produzione su un Mac/Windows qualunque, non solo sulla macchina che l'ha compilata — il backend Python bundlato finora dipendeva da un venv, che non è mai portabile (si appoggia sempre all'installazione Python della macchina su cui è stato creato).

## Contesto — il bug

Un collega ha scaricato la release v0.1.0 e ha ricevuto "Backend non raggiungibile: 404" con un corpo HTML che era in realtà la pagina 404 di **Laravel** (`php artisan serve`, che di default gira sulla porta 8000 — la stessa usata dal nostro backend). Causa reale: `backend/venv/bin/python3` nel pacchetto è un simlink a `/Library/Frameworks/Python.framework/.../python3.14` — un percorso specifico della macchina di sviluppo, inesistente su qualunque altro Mac. Il backend non partiva mai; la finestra si apriva comunque (per design, vedi fix precedente) e le richieste del frontend verso `127.0.0.1:8000` finivano per colpire un altro servizio già in ascolto su quella porta sul Mac del collega.

## Dipendenze

- Build di produzione esistente (`feature/production-build`, `issue-build-1`).

## Stack

- **PyInstaller** (tool di build, non dipendenza runtime — installato solo nel workflow CI, non in `requirements.txt`) — congela `backend/main.py` in un eseguibile standalone per piattaforma, che non richiede Python installato sulla macchina di destinazione.

## Output atteso

- `backend/database.py` e `backend/main.py` non dipendono più da `__file__` per percorsi persistenti (rotto sotto PyInstaller onefile, che estrae in una cartella temporanea) — usano invece la cartella dell'eseguibile quando "frozen".
- `electron/main.js`: in sviluppo (`app.isPackaged === false`) continua a usare il venv locale come prima (nessun bisogno di ricompilare a ogni modifica); in produzione spawna l'eseguibile PyInstaller da `Resources/backend-dist/`.
- `package.json`: `extraResources` copia `backend/dist/` (output di PyInstaller) in `Resources/backend-dist/`; `files` non include più `backend/**/*` (niente più venv/sorgenti Python nel pacchetto).
- `.github/workflows/release.yml`: ogni job (mac/windows) compila il proprio eseguibile con PyInstaller prima di `electron-builder`.

## Status

[x] Completata

**Completata il:** 2026-08-07

**Cosa è stato fatto:**
- Rimosso l'uso di `__file__` per `DB_PATH` (database.py) e per la ricerca di `.env` (main.py) — sostituito con la cartella dell'eseguibile quando `sys.frozen` è vero (PyInstaller), altrimenti comportamento invariato.
- Aggiunto un entry point `if __name__ == "__main__": uvicorn.run(app, ...)` in `main.py` per l'eseguibile standalone (lo sviluppo continua a usare `python -m uvicorn main:app`, che non passa da lì).
- Testato **davvero** l'eseguibile prodotto da PyInstaller: copiato in una cartella isolata (`/tmp`, nessun venv/progetto attorno) e verificato che risponde su `/health`, `/api/categories`, e regge un round-trip completo di transazioni — crea `finance.db` nella cartella giusta (accanto all'eseguibile).
- `electron/main.js`: `startBackend()` ora si ramifica su `app.isPackaged` — sviluppo invariato (venv), produzione spawna l'eseguibile da `process.resourcesPath/backend-dist/`.
- `package.json`: `files` non include più `backend/**/*`; aggiunto `extraResources` per copiare `backend/dist/` (output PyInstaller) in `Resources/backend-dist/`.
- `.github/workflows/release.yml`: aggiunto lo step di build PyInstaller (con gli hidden-import necessari per uvicorn, individuati testando in locale) prima di `electron-builder`, su entrambi i job.
- `.gitignore`: aggiunti `backend/build/` e `*.spec` (artefatti PyInstaller).

**Nota per l'utente:** con questo fix, per usare Turso invece di SQLite locale nella build di produzione, `.env` va copiato dentro `Contents/Resources/backend-dist/.env` (non più `Contents/Resources/app/backend/.env` come nella nota precedente — il percorso è cambiato con la nuova struttura del pacchetto).

**Non ancora fatto:** nessun nuovo tag di release pushato in questa sessione — il fix è su `dev`, pronto per il prossimo tag quando l'utente vorrà pubblicarlo. La build Windows non è stata testata da me direttamente (nessun ambiente Windows disponibile) — solo verificata in principio; sarà la CI a validarla davvero al primo tag.
