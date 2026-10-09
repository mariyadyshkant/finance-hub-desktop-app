# Feature: spese da foto nel bot Telegram — issue-telegram-4

## Obiettivo

Il bot Telegram oggi registra spese solo da testo libero (interpretato da
Gemini Flash). L'utente vuole poter anche **mandare una foto** — uno
screenshot di una notifica di pagamento con carta, o la foto di uno
scontrino cartaceo — e farsi registrare la spesa automaticamente, senza
doverla trascrivere a mano.

Decisioni prese con l'utente:
- **Una foto = una transazione** con il totale (niente spacchettamento per
  voce di scontrino — stessa logica "un messaggio, una transazione" già in
  uso per il testo).
- **Entrata vs spesa**: stessa convenzione del testo — didascalia che inizia
  per `+` = entrata, altrimenti sempre spesa.
- **Conferma prima di salvare**: a differenza del testo (che registra e basta,
  corregge dopo), per le foto il bot mostra cosa ha letto e aspetta una
  conferma esplicita prima di scrivere nel database — l'OCR su uno
  scontrino sbaglia più spesso di un numero scritto a mano.

## Dipendenze

- Nessuna dipendenza nuova: `google-genai` 2.21.0 (già installato) supporta
  input multimodale via `types.Part.from_bytes(data=..., mime_type=...)`,
  stesso `genai.Client` già usato da `_interpret` per il testo.
- Nessun cambio di infrastruttura: stesso webhook, stesso deploy Fly.io,
  nessun nuovo secret.
- Si appoggia ai fix di `issue-audit-3` (try/except su fallimento DB dopo
  parsing riuscito, validazione `importo > 0`): branch da creare a partire
  da `main`, che li contiene già (`dev` è indietro di 6 commit).

## Stack

- Backend FastAPI + Gemini Flash vision (SDK `google-genai`, stesso modello
  `TELEGRAM_PARSER_MODEL` già configurato), coerente con l'ADR.

## Output atteso

### Ricezione e download

- `handle_update`: nuovo ramo per `"photo" in message` → `_handle_photo`,
  prima del controllo su `"text"`. Stesso controllo auth/dedup di oggi.
- `_download_telegram_file(file_id) -> bytes`: `getFile` + GET sul file,
  stesso pattern `requests` già in uso. Fallimento → avviso di riprovare,
  **non va in coda** (fallimento raro e immediato, diverso da quello di
  Gemini).

### Interpretazione (`_interpret_photo`)

- Mirror di `_interpret`: stesso `genai.Client`/timeout/retry, stesso
  pattern try/except → `{"tool": "errore", ...}`.
- `_system_prompt_photo` / `_response_schema_photo`: schema più semplice di
  quello testuale (solo `registra_spesa`/`non_pertinente`, niente
  `correggi_ultima` — le foto non correggono mai una transazione già
  salvata, solo propongono una nuova registrazione da confermare).
- Didascalia (se presente) passata come contesto aggiuntivo, stesso ruolo
  che oggi ha `last_tx` nel prompt testuale.

### Conferma prima di salvare

- Nuovo stato "candidato in attesa", in `app_settings` (chiave
  `telegram:pending_photo`, JSON) — un solo slot, bot mono-utente.
- `_apply_photo_result`: dispatcha `errore`/`non_pertinente`/
  `registra_spesa` (con guard `importo > 0`), salva il candidato, manda il
  prompt di conferma.
- In `handle_update`, per il testo libero non-comando: se c'è un candidato
  pendente, la risposta va a `_handle_confirmation_reply` invece che al
  normale `_handle_text`. Comandi slash e riprocessamento della coda
  testuale (`kind="text"`) **non** passano da qui.
- `_handle_confirmation_reply`: risposta affermativa → inserisce (con lo
  stesso try/except→enqueue di issue-audit-3 se il DB fallisce); negativa →
  scarta; altro testo → **riusa `_interpret` esistente** (non duplicato)
  per interpretare una correzione sul candidato in memoria, con una nuova
  `_apply_candidate_correction` che applica la stessa validazione per campo
  già presente in `_handle_text` ma su un dict invece che su
  `db.update_transaction`.

### Coda con retry

- `telegram_pending`: due nuove colonne via migrazione pigra (stesso
  pattern `ALTER TABLE` in try/except di `database/categories.py`): `kind
  TEXT NOT NULL DEFAULT 'text'`, `payload_json TEXT`.
- `_enqueue_pending(chat_id, text, *, kind="text", payload=None)`: firma
  estesa con default, la chiamata esistente resta identica.
- Tre `kind`: `"text"` (invariato), `"photo"` (payload = caption + is_income
  + foto in base64, scaricata subito — il retry non ri-scarica da
  Telegram), `"confirmed"` (payload = candidato già confermato, il cui
  insert era fallito — il retry ripete solo l'insert, nessuna chiamata a
  Gemini).
- `/coda` e messaggio di scarto finale: nuova `_describe_pending(row)` per
  un'etichetta leggibile anche per i `kind` nuovi.

### Documentazione

- `_HELP` (`/aiuto`): due righe sulla nuova funzionalità.
- Questo file, sezione Status, aggiornato a fine lavoro.

## Verifica

- Niente `TELEGRAM_BOT_TOKEN`/`GEMINI_API_KEY` in locale → nessun test
  end-to-end reale possibile da qui.
- Test di logica con mock (stesso approccio di issue-audit-3): foto valida →
  conferma → «sì» → inserita; «annulla» → scartata; correzione → candidato
  aggiornato → nuovo prompt; Gemini vision irraggiungibile → coda
  (`kind="photo"`); DB che fallisce alla conferma → coda (`kind="confirmed"`);
  retry di entrambi i nuovi `kind`; percorso testo esistente invariato.
- `ast.parse` + import del modulo contro il backend locale (Turso reale),
  per verificare che le modifiche a `_ensure_queue_table` non rompano lo
  startup.
- **Da fare dopo il deploy** (non spuntabile da qui): test dal telefono con
  una foto reale di scontrino e uno screenshot di pagamento, contro Gemini
  vision reale.

## Status

[ ] Da fare
