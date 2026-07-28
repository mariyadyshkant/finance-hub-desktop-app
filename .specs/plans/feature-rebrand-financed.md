# Feature: Rebrand a "FinanceD"

## Obiettivo

Rinominare l'app da "Finance Hub" a "FinanceD" in tutte le stringhe utente-visibili, e sostituire il testo del wordmark nella sidebar con il logo fornito dall'utente.

## Dipendenze

- Design system chiaro già completato (la sidebar da modificare è quella ricostruita in quella feature).
- Logo fornito dall'utente in `frontend/design-system/finance.png`.

## Stack

- Nessuna dipendenza nuova. Vite gestisce l'asset immagine via import statico (`frontend/src/lib/assets/logo.png`).

## Output atteso

- Titolo finestra Electron, `productName`/description in `package.json`, titolo API FastAPI, `<title>` HTML e sidebar tutti coerenti su "FinanceD".
- Logo (ritagliato dallo spazio bianco in eccesso) al posto del testo/wordmark nella sidebar.

## Status

[x] Completata

**Completata il:** 2026-07-28

**Cosa è stato fatto:**
- Ritagliato `frontend/design-system/finance.png` (2000×2000, molto spazio bianco) alla sola area del logo (1557×779, ~2:1) via PIL, salvato in `frontend/src/lib/assets/logo.png`.
- Sostituito il testo "financeD"/"Finance Hub" nella sidebar con `<img>` del logo (dimensioni rifinite dall'utente dopo il mio commit iniziale: altezza 70px).
- Rinominate le stringhe rimaste in `electron/main.js` (titolo finestra), `package.json` (description + productName), `backend/main.py` (titolo FastAPI) — `index.html` e la sidebar erano già stati rinominati dall'utente.
- `name` npm e `appId` electron-builder lasciati invariati (identificatori interni, non branding visibile, cambiarli avrebbe implicazioni su identità/firma dell'app se mai distribuita).
