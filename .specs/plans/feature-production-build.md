# Feature: Build di produzione (Electron)

## Obiettivo

Far funzionare `npm run build` (electron-builder) producendo un `.app`/`.dmg` utilizzabile su questo Mac, non solo `npm run dev`.

## Dipendenze

- Scaffolding Electron/backend esistente. Nessuna nuova dipendenza.

## Stack

- `electron-builder` (già presente in `devDependencies`), nessuna libreria nuova.

## Output atteso

- `npm run build` completa senza errori, producendo `dist/mac-arm64/FinanceD.app` (+ `.dmg`/`.zip`).
- Il backend Python funziona quando lanciato dall'interno del pacchetto (non solo da terminale con venv attivo).
- Nessun segreto (`backend/.env`) incluso nel pacchetto.

## Status

[x] Completata

**Completata il:** 2026-07-29

**Cosa è stato fatto:**
- `electron/main.js`: `startBackend()` ora risolve esplicitamente `backend/venv/bin/python3` (fallback su `python3` di sistema se il venv non esiste), invece di affidarsi al `PATH` ereditato — che in un'app aperta con doppio click da Finder è molto più povero di quello di un terminale con venv attivo.
- `package.json`: aggiunto `"asar": false` — il backend Python (venv con simlink e binari) non può essere eseguito da dentro un archivio asar; l'intera cartella `backend/` deve restare su filesystem reale.
- `package.json`: esclusi esplicitamente `backend/.env` e `backend/.env.*` dai file impacchettati (la lista file di electron-builder è indipendente da `.gitignore` — senza questa esclusione le credenziali reali Turso/Splitwise sarebbero finite dentro il pacchetto).
- Build eseguita con successo: `dist/mac-arm64/FinanceD.app` (394MB, non firmato — richiede tasto destro > Apri al primo avvio), più `.dmg` e `.zip`.
- Verificato che il backend bundlato funziona davvero: lanciato `venv/bin/python3 -m uvicorn` dall'interno del pacchetto, confermato `/health` e `/api/categories` rispondono.

**Nota per l'utente:** poiché `backend/.env` è escluso di proposito dal pacchetto, l'app pacchettizzata usa SQLite locale (vuoto) finché non si copia manualmente `backend/.env` dentro `FinanceD.app/Contents/Resources/app/backend/.env` — scelta deliberata per non spedire segreti dentro un artefatto binario.

## Aggiunta 2026-07-29 — release automatica Mac + Windows via GitHub Actions

L'utente ha chiesto anche una build Windows. Non è producibile da questo Mac:
il `backend/venv/` bundlato è legato a macOS (simlink al Python di sistema,
wheel compilate ARM64) — servirebbe un ambiente Python Windows reale.

**Cosa è stato fatto:**
- `electron/main.js`: `resolvePython()` ora gestisce anche il layout venv di Windows (`venv/Scripts/python.exe` invece di `venv/bin/python3`).
- `package.json`: aggiunto target `win.nsis` e `publish: {provider: "github"}`.
- `.github/workflows/release.yml`: workflow che si attiva su push di tag `v*.*.*` (o manualmente), builda in parallelo su `macos-latest` e `windows-latest` — ogni job crea il proprio venv nativo (`setup-python` + `pip install -r requirements.txt`) prima di lanciare `electron-builder --publish always`, che allega gli installer alla GitHub Release corrispondente al tag.

**Non ancora fatto:** nessun tag pushato/release creata — questo workflow va testato al primo tag reale.
