# Feature: revisione mirata di telegram_bot.py — issue-audit-3

## Obiettivo

Dall'audit del repo (30/09/2026, commit `3b56e4f`, vedi `AUDIT.md`):
`backend/telegram_bot.py` (773 righe) è il file backend più grande del
progetto. È tipicamente dove si annidano edge case: parsing dei messaggi con
Gemini, retry della coda, gestione errori di rete. Non è un problema
confermato, ma un'area a rischio che merita un'occhiata mirata, soprattutto
dopo le modifiche recenti (`issue-telegram-2`, `issue-telegram-3`: webhook che
risponde subito con dedup su `update_id`, coda con retry, entrate con "+" e
data personalizzabile).

## Dipendenze

- Nessuna. Attività di revisione, non di feature.

## Stack

- Backend FastAPI + python-telegram-bot/webhook + Gemini per il parsing,
  coerente con l'ADR.

## Output atteso

- Revisione riga per riga di `telegram_bot.py` con focus su:
  - parsing Gemini: cosa succede se la risposta non è nel formato atteso o
    Gemini è irraggiungibile/lento;
  - coda con retry: comportamento su fallimento permanente (dead letter? log?
    messaggio perso silenziosamente?), idempotenza dei retry;
  - gestione errori di rete verso Telegram e verso il backend/DB;
  - eventuali race condition tra webhook e processamento della coda.
- Documento (o commento nello spec) con l'elenco di edge case trovati,
  ciascuno classificato come "già gestito", "minore" o "da sistemare".
- Per gli edge case classificati "da sistemare": fix mirati, senza refactoring
  più ampio del file (quello è fuori scope qui).
- Verifica: test manuale dei casi critici trovati (es. messaggio malformato,
  Gemini offline, Telegram che ritorna errore) su bot di test.

## Status

[x] Completata

**Completata il:** 2026-09-30

**Edge case trovati, per area:**

*Parsing Gemini (`_interpret`)*
- Già gestito: SDK non installato, `GEMINI_API_KEY` mancante, qualunque
  eccezione della chiamata (timeout, 5xx, JSON non valido, modello ritirato)
  → tutto torna come `{"tool": "errore", ...}`, gestito uniformemente da chi
  chiama (vedi coda). Timeout configurato a 12s con 1 retry SDK, scelta
  esplicita per non restare appesi.
- Minore: se Gemini restituisce `azione="registra_spesa"` con una categoria
  fuori dal pool consentito, il codice fa fallback silenzioso su "Altro"/
  "Entrata" — comportamento ragionevole, nessuna azione.
- **Da sistemare (fatto):** nessuna validazione che `importo > 0` prima di
  inserire la transazione — a differenza del ramo di correzione, che già
  valida `new_amount <= 0`. Un messaggio ambiguo classificato erroneamente
  come `registra_spesa` con importo 0 creava silenziosamente una transazione
  da €0 nel database reale. **Fix:** aggiunto lo stesso guard già presente
  nel ramo di correzione, con messaggio "Non ho capito l'importo — riprova
  specificandolo".

*Coda con retry (`_process_pending_queue`, `queue_worker_loop`)*
- Già gestito: retry ogni 60s, fino a `_QUEUE_MAX_ATTEMPTS=8` poi scarto con
  messaggio esplicito all'utente («non sono riuscito... l'ho scartato»).
  Nessun dead-letter silenzioso.
- **Da sistemare (fatto):** un fallimento del database (non di Gemini) DOPO
  che Gemini aveva già interpretato correttamente il messaggio — durante
  `_insert_transaction`/`db.set_setting` (registrazione) o
  `db.update_transaction` (correzione) — non era catturato da nessun
  try/except. Conseguenze concrete: (1) la spesa non veniva salvata, (2) non
  veniva rimessa in coda (l'enqueue avviene solo nel ramo `tool == "errore"`
  di Gemini), (3) nessun messaggio di errore arrivava all'utente — persa in
  silenzio; e se succedeva durante il riprocessamento della coda,
  l'eccezione non gestita usciva da `_process_pending_queue` fermando
  l'elaborazione di **tutti** i messaggi in coda dietro quello fallito per
  quel giro (il contatore tentativi non veniva mai incrementato per l'item
  che falliva, quindi restava in coda indefinitamente). **Fix:** avvolti
  entrambi i rami (`registra_spesa`, `correggi_ultima`) in try/except che,
  su fallimento, rimette il messaggio in coda (stesso meccanismo già usato
  per gli errori Gemini), avvisa l'utente e ritorna `False` — così il
  contatore tentativi riprende a funzionare normalmente anche per questo
  tipo di fallimento.

*Errori di rete verso Telegram (`send_message`)*
- Già gestito: try/except su `requests.RequestException`, log e basta — un
  invio fallito non blocca il resto del flusso (la transazione è comunque
  salvata). Nessuna azione.

*Idempotenza / race condition (`_already_seen`, webhook vs coda)*
- Già gestito: dedup su `update_id` con INSERT su PRIMARY KEY (atomico anche
  con più macchine Fly), webhook risponde 200 subito e processa in
  background (`routes/telegram.py`), con try/except che logga qualunque
  eccezione da `handle_update` — coerente con l'intento del suo docstring
  ("non solleva") anche se la garanzia è imposta dal chiamante, non dalla
  funzione stessa. Nessuna azione: comportamento corretto end-to-end,
  verificato leggendo `routes/telegram.py`.
- Minore, non affrontato: un messaggio live (webhook) e uno in coda per lo
  stesso `last_tx` potrebbero in teoria essere elaborati in parallelo da due
  thread diversi (webhook in background task, coda nel suo worker), e
  l'ultimo a scrivere `_LAST_TX_KEY` "vince" — entrambe le transazioni
  vengono comunque salvate correttamente, cambia solo quale delle due
  `/cancella` o una correzione andrebbe poi a toccare. Scenario raro per un
  bot mono-utente con volumi bassi; non affrontato per restare nello scope
  di "fix mirati, senza refactoring più ampio".

**Fix applicati:** `backend/telegram_bot.py`, rami `registra_spesa` e
`correggi_ultima` di `_handle_text`.

**Verifica:** dato che `TELEGRAM_BOT_TOKEN` non è configurato in locale (solo
sul backend hosted), non è stato possibile un test end-to-end contro il bot
Telegram reale. Verificato invece a livello di logica con uno script che
monkeypatcha `send_message`/`_enqueue_pending`/`_insert_transaction`/
`db.update_transaction` per simulare: (1) DB che fallisce durante
`registra_spesa` → messaggio rimesso in coda, utente avvisato, `handled =
False`; (2) Gemini che restituisce importo 0 → nessuna transazione inserita,
utente avvisato; (3) DB che fallisce durante `correggi_ultima` → stesso
comportamento del caso 1; (4) percorsi "felici" di entrambi i rami
invariati rispetto a prima del fix. Backend avviato con `uvicorn main:app`
contro Turso reale: startup pulito, nessun errore di import.
