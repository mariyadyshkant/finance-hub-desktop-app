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

[x] Codice scritto in `backend/telegram_bot.py` sul branch `issue-telegram-4`
    (creato da `main`, che contiene già i fix di issue-audit-3): download
    foto da Telegram, `_interpret_photo`/prompt/schema vision dedicati,
    stato "candidato in attesa" su `app_settings`, conferma/correzione/
    annulla, estensione della coda (`kind`: `text`/`photo`/`confirmed`),
    `_describe_pending` per `/coda`, `_HELP` aggiornato.
[x] Verificato in locale con script di logica (mock di `send_message`,
    `_download_telegram_file`, `_interpret`/`_interpret_photo`,
    `_insert_transaction`, `db.get_setting`/`set_setting`, invocando
    `handle_update` end-to-end): foto valida → conferma → «sì» → inserita;
    «annulla» → scartata; foto → correzione → nuovo prompt → «sì» →
    inserita coi valori corretti; Gemini vision irraggiungibile → coda
    `kind="photo"`; DB che fallisce alla conferma → coda `kind="confirmed"`;
    foto non pertinente; didascalia con `+` → entrata; retry di coda per
    entrambi i nuovi `kind`; percorso testuale esistente (registrazione,
    `/aiuto`) invariato — 9 scenari foto + 2 di non-regressione, tutti OK.
[x] `ast.parse` + import del modulo contro il backend locale (Turso reale):
    nessun errore; migrazione pigra di `telegram_pending` verificata
    (colonne `kind`/`payload_json` presenti dopo lo startup).
[ ] Deploy su Fly.io e verifica end-to-end dal telefono (foto reale di uno
    scontrino e screenshot di una notifica di pagamento, contro Gemini
    vision reale) — non verificabile da qui per mancanza di
    `GEMINI_API_KEY`/`TELEGRAM_BOT_TOKEN` in locale.
[ ] Merge `issue-telegram-4` in `dev`, poi in `main`.

**Revisione (2026-10-09) — più pagamenti in una foto.** L'utente ha fatto
notare un caso non coperto: uno screenshot con più pagamenti distinti nello
stesso giorno (es. la lista movimenti di un'app bancaria). Con lo schema
originale (un totale unico per foto) Gemini avrebbe dovuto indovinare quale
pagamento prendere o inventare un totale sommato senza senso.

Esteso senza rompere il caso singolo (verificato: il messaggio di conferma
per una foto con un solo pagamento è identico a prima, nessun contatore):
- `_response_schema_photo`/`_system_prompt_photo`/`_interpret_photo`: Gemini
  ora restituisce sempre un **elenco** di pagamenti (`spese: [...]`, azione
  `registra_spese`), uno per riga/movimento distinto se l'immagine è una
  lista, uno solo se è un singolo scontrino/notifica (il prompt chiarisce la
  differenza: scontrino con più voci → sempre un totale unico, lista di
  movimenti → un elemento per movimento).
- Stato di conferma: da "un candidato" a `{"queue": [...], "index", "total"}`
  — stessa infrastruttura (`app_settings`), confermati **uno alla volta in
  sequenza** (non tutti insieme): riusa quasi tutto il codice di conferma/
  correzione già scritto, cambia solo cosa succede dopo un sì/annulla (si
  passa al prossimo della coda invece di chiudere lo stato).
- Nuovi comandi testuali nella conferma: «annulla» ora salta solo il
  pagamento corrente (non tutta la coda); «annulla tutto»/«annulla tutti»
  scarta anche i rimanenti.
- Se il DB fallisce alla conferma di uno dei N, quello va in coda
  (`kind="confirmed"`, invariato) e si continua a chiedere conferma per i
  successivi — un fallimento non blocca gli altri.
- Verificato con 6 nuovi scenari di logica mockati (3 pagamenti confermati
  tutti in sequenza; uno saltato nel mezzo; «annulla tutto» a metà; una
  correzione sul pagamento corrente che non tocca gli altri in coda; una
  foto con un solo pagamento → formato messaggio invariato; DB che fallisce
  su uno dei N → coda, si continua con gli altri) + ri-verificati i 9+2
  scenari precedenti, tutti OK.

**Revisione (2026-10-09) — nota opzionale.** Aggiunta la possibilità di
scrivere una nota, sia per il testo libero che per le foto, scritta nello
stesso messaggio/didascalia (non un passaggio separato):

- Campo `nota` aggiunto a `_response_schema`/`_system_prompt` (testo) e
  `_response_schema_photo`/`_system_prompt_photo` (foto, per ciascun
  pagamento): Gemini la riconosce quando introdotta da «nota:» o da un
  "con X"/"per Y" dopo una virgola, altrimenti resta vuota.
- `campo_correzione` esteso con `"nota"` in entrambi gli schemi: si può
  aggiungere/cambiare/rimuovere la nota anche dopo, con «nota: ...»
  (nota vuota = rimossa), sia su `last_tx` (testo) sia sul candidato in
  attesa di conferma (foto) — stessa infrastruttura di correzione già
  esistente, nessun codice nuovo per il dispatch.
- `_insert_transaction` accetta ora `note` (default `""`, come il resto del
  bot prima di questa modifica) e lo scrive nella colonna `note` già
  esistente nella tabella `transactions` (stessa colonna usata dall'app
  desktop).
- La nota, quando presente, compare nei messaggi di conferma/registrazione
  e in `/ultima` (` · nota: ...`); nessun cambiamento quando è vuota.
- Verificato con 6 scenari di logica mockati (testo: registrazione con nota
  inline, registrazione senza nota, correzione che aggiunge una nota a una
  transazione già salvata, rimozione nota; foto: nota dalla didascalia
  mostrata nel prompt di conferma e nel messaggio finale, correzione della
  nota sul candidato in attesa) + ri-verificata la regressione completa
  (foto singola, multi-pagamento, testo semplice, `/aiuto`), tutti OK.

**Fix (2026-10-09) — categorie custom invisibili al bot.** L'utente ha
testato il bot dal vivo (prima del merge, probabilmente contro un deploy
precedente) e ha trovato un bug reale: correggere la categoria di una
spesa da foto in «Animali» falliva con «Categoria non riconosciuta», pur
essendo «Animali» una categoria valida visibile nell'app desktop.

Causa: `telegram_bot.py` costruiva `_EXPENSE_CATEGORIES` da un elenco
**statico** (`importers.helpers.CATEGORIES`, le 18 categorie di default),
non dalla tabella `categories` del database — quindi qualunque categoria
aggiunta dall'utente dopo il seed iniziale (Impostazioni → Categorie
nell'app desktop) era invisibile al bot, sia per la registrazione iniziale
(Gemini non poteva mai scegliere "Animali" per una foto del pet store, da
qui "Shopping" nello screenshot dell'utente) sia per le correzioni.

Fix: nuova `_category_pool(is_income)` che legge `db.get_categories()` dal
vivo a ogni chiamata (stesso pattern delle altre funzioni del bot, nessuna
cache) — sostituisce tutti i 9 usi del vecchio pattern
`_INCOME_CATEGORIES if ... else _EXPENSE_CATEGORIES`. Rimossi
`_EXPENSE_CATEGORIES` e l'import di `importers.helpers.CATEGORIES`.
`_INCOME_CATEGORIES` resta una costante (le due categorie speciali
entrata/rimborso, seminate di default).

Aggiunto anche, indipendentemente dalla causa di fondo: `_match_category`,
un confronto tollerante (maiuscole/minuscole, virgolette) per le
correzioni di categoria — a differenza della registrazione iniziale (dove
`categoria` è vincolata a un enum nello schema), il campo di una
correzione (`nuovo_testo`) è testo libero e Gemini può restituirlo con una
scrittura leggermente diversa da come compare nel pool. Rafforzato anche
il prompt testuale perché richieda esplicitamente il nome esatto.

Verificato: lo schema Gemini (testo e foto) ora include "Animali" come
categoria valida; 5 varianti di scrittura della stessa categoria
("Animali" con virgolette doppie/singole, minuscolo, spazi, maiuscolo)
tutte riconosciute correttamente in una correzione; una categoria
inesistente resta correttamente rifiutata; ri-verificata l'intera
regressione (foto con categoria custom, multi-pagamento, testo semplice,
correzione categoria con nome esatto), tutti OK.

**Da fare**: questo fix non è ancora deployato — se il bot che l'utente ha
testato dal vivo era già su Fly.io, serve un nuovo deploy perché il
comportamento cambi in produzione.

**Fix (2026-10-09) — log mancante sui fallimenti Gemini.** L'utente ha
condiviso i log reali di Fly (`fly logs`) per investigare i due fallimenti
Gemini visti durante il test dal vivo. I log non mostravano nulla di utile:
solo `POST /api/telegram/webhook 200 OK` (risposta immediata, invariata
qualunque cosa succeda dopo in background) e due deploy/riavvii macchina.
Guardando il codice: `_interpret`/`_interpret_photo` catturavano
l'eccezione di Gemini e la convertivano in `{"tool": "errore", ...}` per
decidere se accodare, **senza mai stampare nulla** — quindi anche avendo i
log disponibili, il motivo esatto (quota, rete, modello ritirato...) non
sarebbe mai comparso.

Fix: aggiunto un `print("[telegram] _interpret(_photo) fallito:", repr(e))`
in entrambi gli except, prima del `return`. La prossima volta che succede,
`fly logs --app financed-backend` mostrerà il messaggio di errore completo
di Gemini (es. l'esatto testo di un 429 RESOURCE_EXHAUSTED).

Verificato: simulata un'eccezione dentro `_interpret` (monkeypatch di
`genai.Client.models.generate_content`) e confermato che il log cattura il
messaggio esatto; ri-verificato il flusso testuale di base, invariato.
