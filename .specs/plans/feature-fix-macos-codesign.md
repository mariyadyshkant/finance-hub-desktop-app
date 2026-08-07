# Fix: backend irraggiungibile su macOS (v0.1.1) + supporto Linux

## Problema

Dopo la release v0.1.1 (fix di portabilità del backend via PyInstaller),
alcuni utenti hanno comunque riscontrato "Backend non raggiungibile" con
pagine 404/errore di connessione su ogni sezione dell'app.

Diagnosi: `spctl -a -vv` sull'app scaricata restituiva `rejected` con
`"code has no resources but signature indicates they must be present"`.
Causa: `extraResources` aggiunge l'eseguibile PyInstaller (non firmato)
dentro `Resources/`, ma electron-builder firma solo il bundle esterno in
modo non coerente con le risorse annidate — Gatekeeper rifiuta l'intero
bundle con un errore strutturale che blocca silenziosamente lo spawn del
processo backend, anche dopo "tasto destro > Apri".

## Fix

1. `scripts/afterPack.js` (hook electron-builder `afterPack`): ri-firma
   l'intero bundle `.app` con `codesign --deep --force --sign -`
   (firma **ad-hoc**, nessun certificato/account Apple necessario) DOPO
   che tutte le risorse sono al loro posto, così la firma è coerente su
   tutto l'albero.
2. `"mac": {"identity": null}` in `package.json`: durante il rebuild
   locale, electron-builder ha rilevato automaticamente un certificato
   "Apple Development" presente nel keychain (installato per il testing
   iOS del progetto mobile) e ha sovrascritto la firma ad-hoc con questo
   certificato — ancora meno adatto per la distribuzione a terzi.
   `identity: null` forza electron-builder a saltare la propria firma
   automatica, lasciando solo la firma ad-hoc di `afterPack.js` come
   definitiva.
3. Aggiunto target Linux (`AppImage`) in `package.json` e `ubuntu-latest`
   alla matrice del workflow di release — Linux non richiede firma del
   codice, nessun passaggio aggiuntivo necessario.

## Verifica

- `codesign --verify --deep --strict --verbose=4` sul bundle rebuilded:
  `valid on disk`, `satisfies its Designated Requirement`, nessun errore
  di risorse mancanti (il vecchio errore strutturale non compare più).
- `spctl -a -vv` mostra ancora `rejected` — **atteso e normale** per
  un'app ad-hoc firmata da sviluppatore non identificato (richiede
  comunque "tasto destro > Apri" al primo avvio), non è più l'errore
  strutturale di prima.
- Test end-to-end: `open dist/mac-arm64/FinanceD.app`, poi
  `curl http://127.0.0.1:8000/health` e `/api/categories` →
  risposte corrette, confermando che Electron spawna il backend
  PyInstaller correttamente nel bundle pacchettizzato (non solo
  eseguibile standalone in isolamento, già verificato in precedenza).

## Note

- La firma ad-hoc (`--sign -`) non è una firma Apple Developer reale: è
  gratuita, non richiede account, e serve solo a rendere coerente il
  bundle per Gatekeeper — non conferisce alcuna fiducia agli occhi di
  macOS. L'utente finale deve comunque fare "tasto destro > Apri" al
  primo avvio.
- Prossimo step: bump versione, tag, verifica release via GitHub Actions
  (macOS + Windows + Linux), pubblicazione.

- [x] Completata (2026-08-07)
