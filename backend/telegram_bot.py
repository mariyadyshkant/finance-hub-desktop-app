"""Bot Telegram personale per registrare spese e consultare i totali dal telefono.

Non gira come processo a sé: è un modulo importato dal backend FastAPI
(`routes/telegram.py` espone il webhook). Telegram consegna gli update via
HTTPS a `POST /api/telegram/webhook`, quel route chiama `handle_update()` qui.

Scelte (vedi ADR.md → "Integrazione Telegram Bot"):
- Nessuna libreria `python-telegram-bot`: sono due sole chiamate HTTP alla Bot
  API (`sendMessage`, `setWebhook`), fatte con `requests` — già una dipendenza.
  Stessa filosofia di `turso_client.py` (client HTTP fatto in casa, zero build
  native).
- Parsing dei messaggi in linguaggio naturale con Gemini Flash (SDK
  `google-genai`), piano gratuito di Google AI Studio: costo zero per un bot
  personale.
- Il bot risponde SOLO a `TELEGRAM_CHAT_ID`: chiunque altro conosca il nome del
  bot riceve un rifiuto secco.
- Le spese sono salvate con importo NEGATIVO, come fa l'app desktop per le
  spese manuali (`frontend/.../Transazioni.svelte`: default -10). Entrate e
  rimborsi restano positivi. Un messaggio che comincia per "+" è un'entrata,
  non una spesa (vedi `_handle_text`).
- Se Gemini non risponde (rete giù, quota, modello che cambia nome com'è già
  successo) il messaggio non viene perso: finisce in una coda (tabella
  `telegram_pending`) e un task in background (`queue_worker_loop`, avviato da
  `main.py`) lo ritenta ogni minuto finché non va a buon fine o supera
  `_QUEUE_MAX_ATTEMPTS`.
- Oltre al testo, il bot accetta anche una FOTO (scontrino, notifica di
  pagamento, o una lista di più movimenti in uno screenshot — ogni pagamento
  distinto diventa un candidato separato). A differenza del testo, una foto
  passa sempre da una conferma esplicita prima di scrivere nel database
  (vedi `_handle_photo`/`_handle_confirmation_reply`): l'OCR/vision su
  un'immagine sbaglia più spesso di un numero scritto a mano.
"""
import asyncio
import base64
import json
import os
from datetime import date, timedelta

import requests

import database as db

# ─── Config da ambiente ──────────────────────────────────────────────────────

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
ALLOWED_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
# Modello Gemini per il parsing: abbondante per estrarre importo/descrizione/
# categoria da una frase. Google ritira i modelli vecchi in fretta (i `2.5-*`
# non sono più disponibili ai nuovi progetti da set. 2026) — se l'API risponde
# 404 dicendo di aggiornare, mettere il nome suggerito in TELEGRAM_PARSER_MODEL
# (secret Fly) senza aspettare una modifica al codice.
# `or` e non il default di getenv: la env var può essere presente ma vuota.
PARSER_MODEL = os.getenv("TELEGRAM_PARSER_MODEL") or "gemini-3.6-flash"

TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"

# Categorie per una spesa vs. per un'entrata (vedi il prefisso "+" in
# _handle_text). Le due liste sono disgiunte: una transazione del bot è o
# l'una o l'altra, mai ambigua. "Entrata"/"Rimborso ricevuto" sono le due
# categorie speciali seminate di default (vedi database/categories.py) — le
# altre sono lette dal vivo (vedi _category_pool), non da un elenco statico:
# includono anche le categorie che l'utente aggiunge dall'app desktop
# (Impostazioni → Categorie, es. "Animali"), altrimenti invisibili al bot.
_INCOME_CATEGORIES = ["Entrata", "Rimborso ricevuto"]


def _category_pool(is_income: bool) -> list[str]:
    """Pool di categorie valide per spese o entrate, letto dal vivo dalla
    tabella `categories` — non da un elenco statico in `importers/helpers.py`,
    che non include le categorie aggiunte dall'utente dopo il seed iniziale."""
    all_names = [c["name"] for c in db.get_categories()]
    if is_income:
        return [c for c in all_names if c in _INCOME_CATEGORIES]
    return [c for c in all_names if c not in _INCOME_CATEGORIES]

_MESI_IT = [
    "gen", "feb", "mar", "apr", "mag", "giu",
    "lug", "ago", "set", "ott", "nov", "dic",
]
_GIORNI_IT = ["lunedì", "martedì", "mercoledì", "giovedì", "venerdì", "sabato", "domenica"]

_LAST_TX_KEY = "telegram:last_tx_id"
# Candidato (non ancora salvato) in attesa di conferma dopo una foto — vedi
# _handle_photo/_handle_confirmation_reply. Un solo slot: bot mono-utente,
# una nuova foto sovrascrive un candidato non confermato.
_PENDING_PHOTO_KEY = "telegram:pending_photo"

# Quante volte ritentare un messaggio rimasto in coda (uno ogni
# _QUEUE_INTERVAL_S) prima di arrendersi e avvisare l'utente.
_QUEUE_INTERVAL_S = 60
_QUEUE_MAX_ATTEMPTS = 8


def is_configured() -> bool:
    return bool(BOT_TOKEN and ALLOWED_CHAT_ID)


# ─── Telegram Bot API ────────────────────────────────────────────────────────

def send_message(chat_id, text: str) -> None:
    if not BOT_TOKEN:
        print("[telegram] TELEGRAM_BOT_TOKEN non impostato, messaggio non inviato")
        return
    try:
        requests.post(
            f"{TELEGRAM_API}/sendMessage",
            json={
                "chat_id": chat_id,
                "text": text,
                "disable_web_page_preview": True,
            },
            timeout=15,
        ).raise_for_status()
    except requests.RequestException as e:
        print("[telegram] invio messaggio fallito:", repr(e))


def _download_telegram_file(file_id: str) -> bytes:
    """Scarica il contenuto di un file Telegram (es. una foto) dato il suo
    file_id. Due chiamate come documentato dalla Bot API: getFile per
    ottenere il percorso, poi il download vero e proprio dalla CDN."""
    r = requests.get(f"{TELEGRAM_API}/getFile", params={"file_id": file_id}, timeout=15)
    r.raise_for_status()
    file_path = r.json()["result"]["file_path"]
    file_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_path}"
    r2 = requests.get(file_url, timeout=20)
    r2.raise_for_status()
    return r2.content


# ─── Accesso dati ────────────────────────────────────────────────────────────

def _rows(sql: str, params=()):
    conn = db.get_conn()
    cur = conn.execute(sql, params)
    cols = [d[0] for d in cur.description]
    out = [dict(zip(cols, r)) for r in cur.fetchall()]
    conn.close()
    return out


def _today_iso() -> str:
    return date.today().isoformat()


def _fmt_date_it(iso: str) -> str:
    y, m, d = iso.split("-")
    return f"{int(d)} {_MESI_IT[int(m) - 1]} {y}"


def _fmt_eur(value: float) -> str:
    return f"€{value:,.2f}".replace(",", "·").replace(".", ",").replace("·", ".")


def _spent_between(start_iso: str, end_iso: str) -> float:
    """Totale speso (valore positivo) tra due date incluse."""
    rows = _rows(
        "SELECT COALESCE(-SUM(amount), 0) AS spent FROM transactions "
        "WHERE date BETWEEN ? AND ? AND amount < 0",
        (start_iso, end_iso),
    )
    return float(rows[0]["spent"]) if rows else 0.0


def _spent_in_month(month: str) -> float:
    rows = _rows(
        "SELECT COALESCE(-SUM(amount), 0) AS spent FROM transactions "
        "WHERE strftime('%Y-%m', date) = ? AND amount < 0",
        (month,),
    )
    return float(rows[0]["spent"]) if rows else 0.0


def _breakdown(sql_where: str, params) -> list[tuple[str, float]]:
    rows = _rows(
        f"SELECT category, -SUM(amount) AS amt FROM transactions "
        f"WHERE {sql_where} AND amount < 0 GROUP BY category ORDER BY amt DESC",
        params,
    )
    return [(r["category"], float(r["amt"])) for r in rows]


def _valid_iso_date(value: str) -> str | None:
    """Valida una stringa YYYY-MM-DD. Ritorna None se non è una data valida."""
    try:
        return date.fromisoformat((value or "").strip()).isoformat()
    except ValueError:
        return None


def _match_category(raw: str, pool: list[str]) -> str | None:
    """Confronto tollerante per una correzione di categoria: a differenza
    della registrazione iniziale (categoria vincolata a un enum nello
    schema), il valore di una correzione arriva in `nuovo_testo`, un campo
    di testo libero — Gemini può restituirlo con maiuscole/minuscole o
    virgolette diverse da come l'utente le ha scritte (es. 'Animali',
    "Animali", animali). Ritorna il nome canonico dal pool, o None se non
    corrisponde a nessuna categoria valida."""
    normalized = raw.strip().strip("'\"«»“”‘’").strip().lower()
    for cat in pool:
        if cat.lower() == normalized:
            return cat
    return None


def _insert_transaction(
    description: str, amount_abs: float, category: str, date_iso: str, is_income: bool, note: str = ""
) -> int:
    """Inserisce una transazione e ritorna l'id della nuova riga.

    Spesa → importo negativo; entrata/rimborso (is_income) → positivo. Stessa
    convenzione delle spese manuali dell'app desktop.

    RETURNING è supportato sia da SQLite locale (>= 3.35) sia da libsql/Turso —
    evita di dover indovinare l'id con un SELECT successivo, che con il client
    HTTP di Turso girerebbe su una connessione diversa (last_insert_rowid = 0).
    """
    amount = abs(amount_abs) if is_income else -abs(amount_abs)
    conn = db.get_conn()
    cur = conn.execute(
        "INSERT INTO transactions (date, description, amount, category, source, note) "
        "VALUES (?,?,?,?,?,?) RETURNING id",
        (date_iso, description, amount, category, "telegram", note),
    )
    row = cur.fetchone()
    conn.commit()
    conn.close()
    return int(row[0])


# ─── Interpretazione messaggi (Gemini) ─────────────────────────────────────
# Gemini Flash sul piano gratuito di Google AI Studio (1M token/giorno, nessuna
# carta): costo zero per un bot personale. Si usa la "structured output" di
# Gemini (JSON con schema imposto) invece del function-calling: un solo schema
# piatto, output deterministico, mapping banale sul resto del codice.

_NO_FIELD = "nessuno"


def _system_prompt(today_iso: str, is_income: bool) -> str:
    d = date.fromisoformat(today_iso)
    oggi_leggibile = f"{_GIORNI_IT[d.weekday()]} {d.day} {_MESI_IT[d.month - 1]} {d.year}"
    tipo = "un'ENTRATA o un rimborso ricevuto" if is_income else "una SPESA"
    categorie = _category_pool(is_income)
    return (
        "Sei l'assistente di un bot Telegram personale per registrare "
        f"movimenti di conto in italiano. Oggi è {today_iso} ({oggi_leggibile}). "
        f"L'utente ti ha già detto che questo messaggio è {tipo}: usa solo "
        f"queste categorie: {', '.join(categorie)}.\n"
        "Ogni messaggio è di uno di questi tipi:\n"
        "- una NUOVA registrazione: '€8 bar boulevard', 'ho pagato 45 dal "
        "dentista', 'ieri 20 euro benzina', 'il 3 settembre 15 al cinema' → "
        "azione = registra_spesa, con importo (sempre positivo), una "
        "descrizione breve e pulita, la categoria più adatta, e la data in "
        "formato YYYY-MM-DD — risolvi espressioni relative ('ieri', 'l'altro "
        "ieri', 'lunedì scorso') rispetto a oggi; se la data non è menzionata "
        "usa oggi. Se il messaggio contiene anche una nota/precisazione "
        "separata dalla descrizione principale — spesso introdotta da 'nota:' "
        "o da 'con X'/'per Y' dopo una virgola, es. '8 euro bar, nota: con "
        "Marco' o '20 regalo per Giulia, nota: compleanno' — mettila in nota, "
        "altrimenti nota resta vuota.\n"
        "- una CORREZIONE dell'ultima registrazione: 'era 54 non 45', "
        "'mettila in Persona', 'la descrizione è sbagliata, è X', 'in realtà "
        "era di ieri', 'nota: con Marco' → azione = correggi_ultima, con "
        "campo_correzione e il nuovo valore: nuovo_numero per l'importo, "
        "nuovo_testo per categoria/descrizione/nota, nuovo_testo in formato "
        "YYYY-MM-DD per la data. Per una correzione di categoria, nuovo_testo "
        f"deve essere ESATTAMENTE uno di questi nomi, stessa scrittura: "
        f"{', '.join(categorie)} — senza virgolette e senza modificarne "
        "maiuscole/minuscole.\n"
        "- nient'altro → azione = non_pertinente.\n"
        "Non inventare un importo se il messaggio non ne contiene uno. Riempi "
        f"sempre tutti i campi: usa 0, stringa vuota o '{_NO_FIELD}' per quelli "
        "non pertinenti."
    )


def _response_schema(is_income: bool) -> dict:
    categorie = _category_pool(is_income)
    return {
        "type": "object",
        "properties": {
            "azione": {
                "type": "string",
                "enum": ["registra_spesa", "correggi_ultima", "non_pertinente"],
            },
            "descrizione": {"type": "string"},
            "importo": {"type": "number"},
            "categoria": {"type": "string", "enum": categorie},
            "data": {
                "type": "string",
                "description": "YYYY-MM-DD, risolta rispetto a oggi. Se non specificata, oggi.",
            },
            "nota": {"type": "string", "description": "Nota opzionale, stringa vuota se assente."},
            "campo_correzione": {
                "type": "string",
                "enum": ["importo", "categoria", "descrizione", "data", "nota", _NO_FIELD],
            },
            "nuovo_testo": {"type": "string"},
            "nuovo_numero": {"type": "number"},
        },
        "required": [
            "azione", "descrizione", "importo", "categoria", "data", "nota",
            "campo_correzione", "nuovo_testo", "nuovo_numero",
        ],
        "propertyOrdering": [
            "azione", "descrizione", "importo", "categoria", "data", "nota",
            "campo_correzione", "nuovo_testo", "nuovo_numero",
        ],
    }


def _interpret(text: str, last_tx: dict | None, is_income: bool = False) -> dict:
    """Ritorna {'tool': <nome>, 'input': {...}} oppure {'tool': 'errore', ...}.

    I nomi 'tool' nel valore di ritorno sono storici (prima si usava il
    function-calling): il resto del modulo li usa come chiavi di dispatch.
    Ogni errore (rete, quota, chiave, modello ritirato) torna qui come
    {'tool': 'errore', ...} — è compito di chi chiama decidere se accodare.
    """
    try:
        from google import genai
        from google.genai import types
    except ImportError:
        return {"tool": "errore", "messaggio": "SDK google-genai non installato sul server."}

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return {"tool": "errore", "messaggio": "GEMINI_API_KEY non impostata sul server."}

    user_content = text
    if last_tx:
        segno = "+" if last_tx["amount"] >= 0 else "-"
        nota_hint = f" · nota: {last_tx['note']}" if last_tx.get("note") else ""
        user_content = (
            f"[Ultima registrazione: {last_tx['description']} "
            f"{segno}{_fmt_eur(abs(last_tx['amount']))} · {last_tx['category']} · "
            f"{last_tx['date']}{nota_hint}]\n\n{text}"
        )

    try:
        client = genai.Client(
            api_key=api_key,
            # Non lasciare una chiamata appesa all'infinito su un problema di
            # rete: 12s per tentativo, un solo retry automatico dell'SDK sugli
            # errori transitori (5xx/connessione) — oltre, l'errore torna a
            # chi chiama, che decide se accodare il messaggio per dopo.
            http_options=types.HttpOptions(
                timeout=12_000,
                retry_options=types.HttpRetryOptions(attempts=2),
            ),
        )
        resp = client.models.generate_content(
            model=PARSER_MODEL,
            contents=user_content,
            config=types.GenerateContentConfig(
                system_instruction=_system_prompt(_today_iso(), is_income),
                temperature=0,
                response_mime_type="application/json",
                response_schema=_response_schema(is_income),
            ),
        )
        data = json.loads(resp.text)
    except Exception as e:  # google.genai.errors.APIError, timeout, JSON non valido, ...
        return {"tool": "errore", "messaggio": f"Errore Gemini: {e}"}

    azione = data.get("azione")
    categorie_ok = _category_pool(is_income)

    if azione == "registra_spesa":
        categoria = data.get("categoria", "")
        if categoria not in categorie_ok:
            categoria = "Entrata" if is_income else "Altro"
        return {
            "tool": "registra_spesa",
            "input": {
                "descrizione": data.get("descrizione", ""),
                "importo": data.get("importo", 0),
                "categoria": categoria,
                "data": _valid_iso_date(data.get("data", "")) or _today_iso(),
                "nota": data.get("nota", "") or "",
            },
        }

    if azione == "correggi_ultima" and last_tx:
        campo = data.get("campo_correzione")
        if campo not in ("importo", "categoria", "descrizione", "data", "nota"):
            return {"tool": "non_pertinente", "input": {"motivo": "correzione senza campo"}}
        return {
            "tool": "correggi_ultima",
            "input": {
                "campo": campo,
                "nuovo_importo": data.get("nuovo_numero", 0),
                "nuova_categoria": data.get("nuovo_testo", "") if campo == "categoria" else "",
                "nuova_descrizione": data.get("nuovo_testo", "") if campo == "descrizione" else "",
                "nuova_data": data.get("nuovo_testo", "") if campo == "data" else "",
                "nuova_nota": data.get("nuovo_testo", "") if campo == "nota" else "",
            },
        }

    return {"tool": "non_pertinente", "input": {"motivo": "non è una spesa"}}


# ─── Interpretazione foto (Gemini vision) ──────────────────────────────────
# Stesso client/modello/timeout di _interpret, ma per immagini: uno
# screenshot di una notifica di pagamento con carta, o la foto di uno
# scontrino cartaceo. A differenza del testo, una foto non corregge mai una
# registrazione già salvata (solo propone una nuova registrazione, che va
# confermata — vedi _handle_photo/_handle_confirmation_reply): lo schema è
# quindi più semplice, niente azione "correggi_ultima".

def _system_prompt_photo(today_iso: str, is_income: bool, caption: str) -> str:
    d = date.fromisoformat(today_iso)
    oggi_leggibile = f"{_GIORNI_IT[d.weekday()]} {d.day} {_MESI_IT[d.month - 1]} {d.year}"
    tipo = "un'ENTRATA o un rimborso ricevuto" if is_income else "una SPESA"
    categorie = _category_pool(is_income)
    didascalia = (
        f"\nL'utente ha aggiunto questa didascalia alla foto: «{caption}». "
        "Usala come contesto; se contiene una nota/precisazione (es. 'con "
        "Marco', 'cena di lavoro', spesso introdotta da 'nota:'), mettila "
        "nel campo nota del pagamento a cui si riferisce." if caption else ""
    )
    return (
        "Sei l'assistente di un bot Telegram personale per registrare "
        f"movimenti di conto in italiano. Oggi è {today_iso} ({oggi_leggibile}). "
        "L'immagine è UNA di queste cose:\n"
        "- uno screenshot di UNA SINGOLA notifica di pagamento con carta "
        "(push notification della banca/app di pagamento): un solo "
        "pagamento, estrai nome del negozio/esercente e importo.\n"
        "- la foto di UNO scontrino cartaceo: estrai il nome del negozio "
        "(intestazione dello scontrino) e il TOTALE pagato (non la somma "
        "delle singole voci se è già scritto un totale) — uno scontrino "
        "corrisponde SEMPRE a un solo pagamento con l'importo totale, mai "
        "uno per riga/articolo.\n"
        "- una LISTA di più movimenti distinti nello stesso screenshot "
        "(es. l'elenco movimenti/transazioni di un'app bancaria, con più "
        "pagamenti a esercenti diversi, ciascuno con il proprio importo e "
        "data): in questo caso estrai UN pagamento per ogni riga/movimento "
        "distinto della lista, non un totale unico.\n"
        f"L'utente ti ha già detto che questi sono {tipo}: usa solo queste "
        f"categorie: {', '.join(categorie)}." + didascalia + "\n"
        "Se riesci a leggere chiaramente almeno un pagamento → azione = "
        "registra_spese, con un elemento in `spese` per ogni pagamento "
        "distinto che riesci a leggere (quasi sempre 1, più di 1 solo per "
        "una lista di movimenti) — per ciascuno: una descrizione breve e "
        "pulita (nome del negozio/esercente se leggibile), l'importo "
        "(sempre positivo), la categoria più adatta, e la data in formato "
        "YYYY-MM-DD se leggibile nell'immagine per quel pagamento, "
        "altrimenti oggi, e una nota se c'è una precisazione leggibile "
        "nell'immagine o nella didascalia (altrimenti stringa vuota).\n"
        "Se l'immagine non è nessuna delle cose sopra, o è troppo poco "
        "chiara per leggere con certezza almeno un importo → azione = "
        "non_pertinente, `spese` vuoto.\n"
        "Non inventare un pagamento o un importo che non riesci a leggere "
        "con certezza."
    )


def _response_schema_photo(is_income: bool) -> dict:
    categorie = _category_pool(is_income)
    spesa_schema = {
        "type": "object",
        "properties": {
            "descrizione": {"type": "string"},
            "importo": {"type": "number"},
            "categoria": {"type": "string", "enum": categorie},
            "data": {
                "type": "string",
                "description": "YYYY-MM-DD letta dall'immagine. Se non leggibile, oggi.",
            },
            "nota": {"type": "string", "description": "Nota opzionale, stringa vuota se assente."},
        },
        "required": ["descrizione", "importo", "categoria", "data", "nota"],
        "propertyOrdering": ["descrizione", "importo", "categoria", "data", "nota"],
    }
    return {
        "type": "object",
        "properties": {
            "azione": {
                "type": "string",
                "enum": ["registra_spese", "non_pertinente"],
            },
            "spese": {"type": "array", "items": spesa_schema},
        },
        "required": ["azione", "spese"],
        "propertyOrdering": ["azione", "spese"],
    }


def _interpret_photo(image_bytes: bytes, caption: str, is_income: bool = False) -> dict:
    """Come _interpret, ma per un'immagine. Una foto può contenere più
    pagamenti distinti (es. una lista di movimenti bancari), non solo uno:
    il risultato è sempre {'tool': 'registra_spesa', 'input': {'spese': [...]}}
    con uno o più elementi, oppure 'non_pertinente'/'errore'."""
    try:
        from google import genai
        from google.genai import types
    except ImportError:
        return {"tool": "errore", "messaggio": "SDK google-genai non installato sul server."}

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return {"tool": "errore", "messaggio": "GEMINI_API_KEY non impostata sul server."}

    try:
        client = genai.Client(
            api_key=api_key,
            http_options=types.HttpOptions(
                timeout=12_000,
                retry_options=types.HttpRetryOptions(attempts=2),
            ),
        )
        image_part = types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg")
        resp = client.models.generate_content(
            model=PARSER_MODEL,
            contents=[image_part, "Analizza questa immagine."],
            config=types.GenerateContentConfig(
                system_instruction=_system_prompt_photo(_today_iso(), is_income, caption),
                temperature=0,
                response_mime_type="application/json",
                response_schema=_response_schema_photo(is_income),
            ),
        )
        data = json.loads(resp.text)
    except Exception as e:
        return {"tool": "errore", "messaggio": f"Errore Gemini: {e}"}

    spese_raw = data.get("spese") or []
    if data.get("azione") != "registra_spese" or not spese_raw:
        return {"tool": "non_pertinente", "input": {"motivo": "immagine non riconosciuta"}}

    categorie_ok = _category_pool(is_income)
    spese = []
    for item in spese_raw:
        categoria = item.get("categoria", "")
        if categoria not in categorie_ok:
            categoria = "Entrata" if is_income else "Altro"
        spese.append({
            "descrizione": item.get("descrizione", ""),
            "importo": item.get("importo", 0),
            "categoria": categoria,
            "data": _valid_iso_date(item.get("data", "")) or _today_iso(),
            "nota": item.get("nota", "") or "",
        })
    return {"tool": "registra_spesa", "input": {"spese": spese}}


# ─── Comandi ────────────────────────────────────────────────────────────────

_HELP = (
    "FinanceD — bot spese\n\n"
    "Scrivi una spesa in linguaggio naturale, anche con data diversa da oggi:\n"
    "  «€8 bar boulevard»\n"
    "  «ho pagato 45 dal dentista»\n"
    "  «ieri 20 euro benzina»\n\n"
    "Scrivi + davanti per registrare un'ENTRATA invece di una spesa:\n"
    "  «+50 stipendio»\n"
    "  «+20 rimborso da Marco»\n\n"
    "Aggiungi una nota con «nota: ...» nello stesso messaggio:\n"
    "  «15 regalo per Giulia, nota: compleanno»\n\n"
    "Manda una FOTO di uno scontrino, uno screenshot di una notifica di "
    "pagamento, o anche una lista di più movimenti (es. l'elenco "
    "transazioni dell'app della banca): ti mostro cosa ho letto, uno alla "
    "volta se sono più di uno, e aspetto una conferma prima di salvare "
    "ciascuno (rispondi «sì», «annulla» per saltarlo, «annulla tutto» per "
    "scartare tutti i rimanenti, o scrivi una correzione). Stesso + "
    "davanti alla didascalia per un'entrata, nota: nella didascalia per "
    "aggiungere una nota.\n\n"
    "Correggi l'ultima registrazione (o un pagamento in attesa di conferma) "
    "scrivendo in chiaro:\n"
    "  «era 54 non 45» · «mettila in Persona» · «era di ieri» · "
    "«nota: con Marco»\n\n"
    "Comandi:\n"
    "/oggi — spese di oggi\n"
    "/settimana — ultimi 7 giorni\n"
    "/mese — dal 1° del mese\n"
    "/budget — budget del mese e quanto resta\n"
    "/ultima — ultima registrazione\n"
    "/cancella — cancella l'ultima registrazione\n"
    "/coda — messaggi in attesa di essere elaborati\n"
    "/aiuto — questo messaggio\n\n"
    "Se Gemini non risponde (rete o quota) il messaggio non si perde: resta "
    "in coda e viene ritentato da solo ogni minuto."
)


def _cmd_oggi(chat_id):
    today = _today_iso()
    items = _breakdown("date = ?", (today,))
    if not items:
        send_message(chat_id, "Oggi nessuna spesa registrata.")
        return
    total = sum(a for _, a in items)
    lines = [f"Spese di oggi — {_fmt_eur(total)}", ""]
    lines += [f"  {c}: {_fmt_eur(a)}" for c, a in items]
    send_message(chat_id, "\n".join(lines))


def _cmd_settimana(chat_id):
    end = date.today()
    start = end - timedelta(days=6)
    items = _breakdown("date BETWEEN ? AND ?", (start.isoformat(), end.isoformat()))
    if not items:
        send_message(chat_id, "Ultimi 7 giorni: nessuna spesa.")
        return
    total = sum(a for _, a in items)
    lines = [f"Ultimi 7 giorni — {_fmt_eur(total)}", ""]
    lines += [f"  {c}: {_fmt_eur(a)}" for c, a in items]
    send_message(chat_id, "\n".join(lines))


def _cmd_mese(chat_id):
    month = _today_iso()[:7]
    items = _breakdown("strftime('%Y-%m', date) = ?", (month,))
    if not items:
        send_message(chat_id, f"{month}: nessuna spesa registrata.")
        return
    total = sum(a for _, a in items)
    lines = [f"Spese di {month}", ""]
    lines += [f"  {c}: {_fmt_eur(a)}" for c, a in items]
    lines += ["", f"Totale: {_fmt_eur(total)}"]
    send_message(chat_id, "\n".join(lines))


def _cmd_budget(chat_id):
    month = _today_iso()[:7]
    budget = db.get_monthly_budget(month)
    spent = _spent_in_month(month)
    if not budget or budget.get("total") is None:
        send_message(
            chat_id,
            f"Nessun budget impostato per {month}.\n"
            f"Speso finora: {_fmt_eur(spent)}\n"
            f"Imposta il budget dall'app desktop (sezione Pianificazione).",
        )
        return
    total = float(budget["total"])
    left = total - spent
    verdict = "ancora disponibili" if left >= 0 else "OLTRE il budget di"
    send_message(
        chat_id,
        f"Budget {month}\n\n"
        f"  Impostato: {_fmt_eur(total)}\n"
        f"  Speso: {_fmt_eur(spent)}\n"
        f"  {verdict}: {_fmt_eur(abs(left))}",
    )


def _cmd_ultima(chat_id):
    raw = db.get_setting(_LAST_TX_KEY)
    tx = _get_tx(int(raw)) if raw else None
    if not tx:
        send_message(chat_id, "Nessuna registrazione recente del bot.")
        return
    etichetta = "Ultima entrata" if tx["amount"] >= 0 else "Ultima spesa"
    nota_suffix = f" · nota: {tx['note']}" if tx.get("note") else ""
    send_message(
        chat_id,
        f"{etichetta}: {tx['description']} {_fmt_eur(abs(tx['amount']))} · "
        f"{tx['category']} · {_fmt_date_it(tx['date'])}{nota_suffix}\n\n"
        f"Per correggerla scrivi ad es. «era 12 non 8», «mettila in Svago», "
        f"«era di ieri» o «nota: con Marco». Per cancellarla: /cancella",
    )


def _cmd_coda(chat_id):
    pending = _get_pending()
    if not pending:
        send_message(chat_id, "Nessun messaggio in coda.")
        return
    lines = [f"{len(pending)} messaggio/i in attesa:", ""]
    lines += [f"  «{_describe_pending(p)}» (tentativi: {p['attempts']})" for p in pending[:10]]
    send_message(chat_id, "\n".join(lines))


def _cmd_cancella(chat_id):
    raw = db.get_setting(_LAST_TX_KEY)
    tx = _get_tx(int(raw)) if raw else None
    if not tx:
        send_message(chat_id, "Niente da cancellare.")
        return
    db.delete_transaction(tx["id"])
    db.set_setting(_LAST_TX_KEY, "")
    # "Cancellata" concorda sia con "spesa" sia con "entrata" (entrambe f.),
    # quindi non serve distinguere i due casi qui.
    send_message(
        chat_id,
        f"Cancellata — {tx['description']} {_fmt_eur(abs(tx['amount']))} · {tx['category']}",
    )


def _get_tx(tx_id: int) -> dict | None:
    rows = _rows("SELECT * FROM transactions WHERE id = ?", (tx_id,))
    return rows[0] if rows else None


# ─── Coda dei messaggi non elaborati ────────────────────────────────────────
# Se Gemini non risponde (rete giù, quota esaurita, modello ritirato — è già
# successo) il testo dell'utente non deve sparire nel vuoto: finisce qui, e
# `queue_worker_loop` (avviato da main.py) lo ritenta a intervalli regolari.

def _ensure_queue_table(conn) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS telegram_pending (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id TEXT NOT NULL,
            text TEXT NOT NULL,
            attempts INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now'))
        )
        """
    )
    conn.commit()
    # Migrazione per le code create prima delle foto (issue-telegram-4):
    # `kind` distingue cosa va ritentato (testo → Gemini testuale, foto →
    # Gemini vision sui bytes salvati, conferma → solo l'insert nel DB,
    # niente Gemini) — stesso pattern di migrazione pigra già usato per
    # `categories.icon`.
    for statement in (
        "ALTER TABLE telegram_pending ADD COLUMN kind TEXT NOT NULL DEFAULT 'text'",
        "ALTER TABLE telegram_pending ADD COLUMN payload_json TEXT",
    ):
        try:
            conn.execute(statement)
            conn.commit()
        except Exception:
            pass  # colonna già presente


def _enqueue_pending(chat_id, text: str, *, kind: str = "text", payload: dict | None = None) -> None:
    conn = db.get_conn()
    _ensure_queue_table(conn)
    conn.execute(
        "INSERT INTO telegram_pending (chat_id, text, kind, payload_json) VALUES (?,?,?,?)",
        (str(chat_id), text, kind, json.dumps(payload) if payload is not None else None),
    )
    conn.commit()
    conn.close()


def _describe_pending(row: dict) -> str:
    """Etichetta leggibile per /coda e per il messaggio di scarto finale —
    il campo `text` grezzo è vuoto o poco utile per i kind diversi da
    "text"."""
    kind = row.get("kind") or "text"
    if kind == "text":
        return row["text"]
    payload = json.loads(row["payload_json"]) if row.get("payload_json") else {}
    if kind == "photo":
        cap = payload.get("caption") or ""
        return f"[foto]{' · ' + cap if cap else ''}"
    if kind == "confirmed":
        return f"[foto confermata] {payload.get('descrizione', '?')} {_fmt_eur(payload.get('importo', 0))}"
    return row.get("text") or "?"


def _get_pending() -> list[dict]:
    conn = db.get_conn()
    _ensure_queue_table(conn)
    cur = conn.execute("SELECT * FROM telegram_pending ORDER BY id ASC")
    cols = [d[0] for d in cur.description]
    rows = [dict(zip(cols, r)) for r in cur.fetchall()]
    conn.close()
    return rows


def _bump_pending_attempts(pid: int) -> int:
    conn = db.get_conn()
    _ensure_queue_table(conn)
    conn.execute("UPDATE telegram_pending SET attempts = attempts + 1 WHERE id=?", (pid,))
    cur = conn.execute("SELECT attempts FROM telegram_pending WHERE id=?", (pid,))
    row = cur.fetchone()
    conn.commit()
    conn.close()
    return int(row[0]) if row else _QUEUE_MAX_ATTEMPTS


def _delete_pending(pid: int) -> None:
    conn = db.get_conn()
    _ensure_queue_table(conn)
    conn.execute("DELETE FROM telegram_pending WHERE id=?", (pid,))
    conn.commit()
    conn.close()


def _retry_pending_row(row: dict) -> bool:
    """Ritenta una riga di coda in base al suo `kind`. Ritorna True se
    gestita (va rimossa dalla coda), False se va ritentata più tardi."""
    kind = row.get("kind") or "text"

    if kind == "text":
        return _handle_text(row["chat_id"], row["text"], announce_queue=False)

    if kind == "photo":
        payload = json.loads(row["payload_json"])
        image_bytes = base64.b64decode(payload["photo_b64"])
        result = _interpret_photo(image_bytes, payload["caption"], payload["is_income"])
        if result.get("tool") == "errore":
            return False
        _apply_photo_result(row["chat_id"], result, payload["is_income"])
        return True

    if kind == "confirmed":
        candidate = json.loads(row["payload_json"])
        try:
            new_id = _insert_transaction(
                candidate["descrizione"], candidate["importo"], candidate["categoria"],
                candidate["data"], candidate["is_income"], candidate.get("note", ""),
            )
            db.set_setting(_LAST_TX_KEY, str(new_id))
        except Exception as e:
            print("[telegram] retry conferma foto fallito:", repr(e))
            return False
        verbo = "Registrata entrata" if candidate["is_income"] else "Registrato"
        nota_suffix = f" · nota: {candidate['note']}" if candidate.get("note") else ""
        send_message(
            row["chat_id"],
            f"{verbo} — {candidate['descrizione']} {_fmt_eur(candidate['importo'])} · "
            f"{candidate['categoria']} · {_fmt_date_it(candidate['data'])}{nota_suffix}",
        )
        return True

    return True  # kind sconosciuto (non dovrebbe succedere): scarta senza ritentare


def _process_pending_queue() -> None:
    """Un giro di coda: chiamata dal worker in background, e da nessun altro."""
    if not is_configured():
        return
    for row in _get_pending():
        handled = _retry_pending_row(row)
        if handled:
            _delete_pending(row["id"])
            continue
        attempts = _bump_pending_attempts(row["id"])
        if attempts >= _QUEUE_MAX_ATTEMPTS:
            _delete_pending(row["id"])
            send_message(
                row["chat_id"],
                f"Non sono riuscito a elaborare questo messaggio dopo "
                f"{attempts} tentativi, l'ho scartato:\n«{_describe_pending(row)}»\n"
                f"Prova a riscriverlo.",
            )


async def queue_worker_loop() -> None:
    """Task in background avviato da main.py: ritenta la coda ogni minuto.

    Le chiamate vere (Gemini, Telegram, DB) sono bloccanti — girano nel
    threadpool per non bloccare il loop asyncio del server.
    """
    from starlette.concurrency import run_in_threadpool

    while True:
        await asyncio.sleep(_QUEUE_INTERVAL_S)
        try:
            await run_in_threadpool(_process_pending_queue)
        except Exception as e:
            print("[telegram] errore nel worker di coda:", repr(e))


# ─── Testo libero: spesa, entrata o correzione ─────────────────────────────

def _handle_text(chat_id, text: str, *, announce_queue: bool = True) -> bool:
    """Interpreta e agisce su un messaggio libero.

    Ritorna True se il messaggio è stato gestito (anche se il risultato è "non
    è una spesa"), False se c'è stato un errore transitorio (Gemini
    irraggiungibile) e il messaggio va lasciato/rimesso in coda — vedi
    _process_pending_queue, che è l'unico altro chiamante con
    announce_queue=False.
    """
    stripped = text.strip()
    is_income = stripped.startswith("+")
    clean_text = stripped[1:].strip() if is_income else stripped
    if not clean_text:
        return True

    raw = db.get_setting(_LAST_TX_KEY)
    last_tx = _get_tx(int(raw)) if raw else None

    result = _interpret(clean_text, last_tx, is_income=is_income)
    tool = result.get("tool")

    if tool == "errore":
        if announce_queue:
            _enqueue_pending(chat_id, text)
            send_message(
                chat_id,
                "⏳ Non riesco a elaborarlo adesso (rete o modello non "
                "disponibile). L'ho messo in coda: appena torna tutto ok lo "
                "elaboro da solo, senza bisogno di riscriverlo. /coda per "
                "vedere cosa c'è in attesa.",
            )
        return False

    if tool == "registra_spesa":
        data = result["input"]
        desc = str(data["descrizione"]).strip() or ("Entrata" if is_income else "Spesa")
        amount = abs(float(data["importo"]))
        if amount <= 0:
            # Gemini a volte classifica un messaggio come registra_spesa senza
            # un importo riconoscibile (es. un messaggio ambiguo) — meglio
            # chiedere di riprovare che salvare una transazione da €0 nel
            # database reale.
            send_message(
                chat_id,
                "Non ho capito l'importo — riprova specificandolo, es. «€8 bar boulevard».",
            )
            return True
        pool = _category_pool(is_income)
        category = data["categoria"] if data["categoria"] in pool else pool[0]
        tx_date = _valid_iso_date(data.get("data", "")) or _today_iso()
        note = (data.get("nota") or "").strip()
        try:
            new_id = _insert_transaction(desc, amount, category, tx_date, is_income, note)
            db.set_setting(_LAST_TX_KEY, str(new_id))
        except Exception as e:
            # A differenza degli errori di Gemini (già gestiti sopra), un
            # fallimento qui arriva DOPO che Gemini ha già interpretato il
            # messaggio: senza questo except, un blip momentaneo del database
            # (Turso irraggiungibile) perderebbe silenziosamente la spesa,
            # senza salvarla, senza rimetterla in coda e senza avvisare
            # l'utente — vedi issue-audit-3.
            print("[telegram] scrittura su DB fallita per registra_spesa:", repr(e))
            if announce_queue:
                _enqueue_pending(chat_id, text)
                send_message(
                    chat_id,
                    "⏳ Ho capito cosa registrare ma il database non risponde ora. "
                    "L'ho messo in coda, ci riprovo da solo tra poco. /coda per "
                    "vedere cosa c'è in attesa.",
                )
            return False

        verbo = "Registrata entrata" if is_income else "Registrato"
        today = _today_iso()
        if tx_date == today:
            today_total = _spent_between(today, today)
            month_total = _spent_in_month(today[:7])
            riepilogo = f"Oggi: {_fmt_eur(today_total)} · Questo mese: {_fmt_eur(month_total)}"
        else:
            month_total = _spent_in_month(tx_date[:7])
            riepilogo = f"Totale {tx_date[:7]}: {_fmt_eur(month_total)}"
        nota_suffix = f" · nota: {note}" if note else ""
        send_message(
            chat_id,
            f"{verbo} — {desc} {_fmt_eur(amount)} · {category} · "
            f"{_fmt_date_it(tx_date)}{nota_suffix}\n{riepilogo}",
        )
        return True

    if tool == "correggi_ultima":
        if not last_tx:
            send_message(chat_id, "Non c'è un'ultima registrazione da correggere.")
            return True
        data = result["input"]
        campo = data["campo"]
        was_income = last_tx["amount"] >= 0

        try:
            if campo == "importo":
                new_amount = abs(float(data.get("nuovo_importo") or 0))
                if new_amount <= 0:
                    send_message(chat_id, "Importo non valido.")
                    return True
                db.update_transaction(last_tx["id"], amount=new_amount if was_income else -new_amount)
                send_message(
                    chat_id,
                    f"Corretto — {last_tx['description']} {_fmt_eur(new_amount)} · {last_tx['category']}",
                )
            elif campo == "categoria":
                pool = _category_pool(was_income)
                new_cat = _match_category(data.get("nuova_categoria") or "", pool)
                if not new_cat:
                    send_message(chat_id, "Categoria non riconosciuta.")
                    return True
                db.update_transaction(last_tx["id"], category=new_cat)
                send_message(chat_id, f"Categoria aggiornata → {new_cat}")
            elif campo == "descrizione":
                new_desc = (data.get("nuova_descrizione") or "").strip()
                if not new_desc:
                    send_message(chat_id, "Descrizione non valida.")
                    return True
                db.update_transaction(last_tx["id"], description=new_desc)
                send_message(chat_id, f"Descrizione aggiornata → {new_desc}")
            elif campo == "data":
                new_date = _valid_iso_date(data.get("nuova_data", ""))
                if not new_date:
                    send_message(chat_id, "Data non valida.")
                    return True
                db.update_transaction(last_tx["id"], date=new_date)
                send_message(chat_id, f"Data aggiornata → {_fmt_date_it(new_date)}")
            elif campo == "nota":
                # Nota vuota accettata: è il modo per rimuoverla.
                new_note = (data.get("nuova_nota") or "").strip()
                db.update_transaction(last_tx["id"], note=new_note)
                send_message(chat_id, f"Nota aggiornata → {new_note}" if new_note else "Nota rimossa.")
        except Exception as e:
            # Stesso ragionamento del ramo registra_spesa sopra: un fallimento
            # del DB qui arriva dopo che Gemini ha già interpretato la
            # correzione, quindi senza questo except andrebbe persa in
            # silenzio invece di finire in coda — vedi issue-audit-3.
            print("[telegram] scrittura su DB fallita per correggi_ultima:", repr(e))
            if announce_queue:
                _enqueue_pending(chat_id, text)
                send_message(
                    chat_id,
                    "⏳ Ho capito la correzione ma il database non risponde ora. "
                    "L'ho messa in coda, ci riprovo da solo tra poco. /coda per "
                    "vedere cosa c'è in attesa.",
                )
            return False
        return True

    # non_pertinente
    send_message(
        chat_id,
        "Non sembra una registrazione. Scrivi ad es. «€8 bar boulevard» "
        "(spesa) o «+50 stipendio» (entrata), oppure /aiuto per i comandi.",
    )
    return True


# ─── Foto: spesa/entrata da scontrino o notifica di pagamento ─────────────
# A differenza del testo (che registra subito e corregge dopo), una foto
# passa sempre per una conferma esplicita prima di scrivere nel database —
# l'OCR/vision su un'immagine sbaglia più spesso di un numero scritto a
# mano. Lo stato del candidato in attesa vive in app_settings (un solo
# slot, bot mono-utente), stessa infrastruttura di _LAST_TX_KEY.

_AFFIRMATIVE = {"si", "sì", "ok", "okay", "va bene", "confermo", "conferma", "yes", "👍", "✅"}
_NEGATIVE = {"no", "annulla", "annullato", "scarta", "scartala", "cancella"}
_NEGATIVE_ALL = {"annulla tutto", "annulla tutti", "scarta tutto", "scarta tutti"}


def _get_pending_photo_state() -> dict | None:
    """{'queue': [candidato, ...], 'index': posizione 1-based del primo
    della coda nel lotto originale, 'total': quanti erano in tutto}. None se
    non c'è nessun pagamento in attesa di conferma."""
    raw = db.get_setting(_PENDING_PHOTO_KEY)
    if not raw:
        return None
    try:
        state = json.loads(raw)
    except (ValueError, TypeError):
        return None
    return state if state and state.get("queue") else None


def _set_pending_photo_state(state: dict | None) -> None:
    db.set_setting(_PENDING_PHOTO_KEY, json.dumps(state) if state and state.get("queue") else "")


def _format_confirmation_prompt(candidate: dict, index: int, total: int) -> str:
    tipo = "un'entrata" if candidate["is_income"] else "una spesa"
    header = f"📷 Ho letto {tipo} ({index}/{total}):\n" if total > 1 else f"📷 Ho letto {tipo}:\n"
    footer = (
        "Confermi? Rispondi «sì» per salvare, «annulla» per saltarla, oppure "
        "scrivi una correzione (es. «era 12 non 8», «mettila in Salute»)."
    )
    if total > 1:
        footer += " «annulla tutto» scarta anche i pagamenti rimasti."
    nota_suffix = f" · nota: {candidate['note']}" if candidate.get("note") else ""
    return (
        header
        + f"{candidate['descrizione']} {_fmt_eur(candidate['importo'])} · "
        f"{candidate['categoria']} · {_fmt_date_it(candidate['data'])}{nota_suffix}\n\n"
        + footer
    )


def _handle_photo(chat_id, photo_sizes: list, caption: str) -> None:
    stripped = (caption or "").strip()
    is_income = stripped.startswith("+")
    clean_caption = stripped[1:].strip() if is_income else stripped

    file_id = photo_sizes[-1]["file_id"]  # l'ultimo elemento è la risoluzione più alta
    try:
        image_bytes = _download_telegram_file(file_id)
    except Exception as e:
        print("[telegram] download foto fallito:", repr(e))
        send_message(chat_id, "Non sono riuscito a scaricare la foto da Telegram, riprova.")
        return

    result = _interpret_photo(image_bytes, clean_caption, is_income)
    if result.get("tool") == "errore":
        payload = {
            "caption": clean_caption,
            "is_income": is_income,
            "photo_b64": base64.b64encode(image_bytes).decode("ascii"),
        }
        _enqueue_pending(chat_id, clean_caption, kind="photo", payload=payload)
        send_message(
            chat_id,
            "⏳ Non riesco a leggere la foto adesso (rete o modello non "
            "disponibile). L'ho messa in coda: appena torna tutto ok la "
            "elaboro da solo. /coda per vedere cosa c'è in attesa.",
        )
        return
    _apply_photo_result(chat_id, result, is_income)


def _apply_photo_result(chat_id, result: dict, is_income: bool) -> None:
    """Dispatcha un risultato di _interpret_photo già arrivato (dal percorso
    live o da un retry di coda): propone i pagamenti letti per conferma,
    uno alla volta — non scrive mai direttamente nel database. Una foto può
    contenere più pagamenti distinti (es. una lista di movimenti bancari)."""
    tool = result.get("tool")
    if tool == "non_pertinente":
        send_message(
            chat_id,
            "Non mi sembra uno scontrino o una notifica di pagamento. Se lo "
            "è, prova con una foto più chiara, o scrivimi l'importo a parole.",
        )
        return

    candidates = []
    for item in result["input"]["spese"]:
        candidate = {
            "descrizione": str(item["descrizione"]).strip() or ("Entrata" if is_income else "Spesa"),
            "importo": abs(float(item["importo"])),
            "categoria": item["categoria"],
            "data": _valid_iso_date(item.get("data", "")) or _today_iso(),
            "note": (item.get("nota") or "").strip(),
            "is_income": is_income,
        }
        if candidate["importo"] > 0:
            candidates.append(candidate)

    if not candidates:
        send_message(
            chat_id,
            "Non riesco a leggere nessun importo dalla foto — riprova con "
            "una foto più chiara, o scrivimi l'importo a parole.",
        )
        return

    if _get_pending_photo_state() is not None:
        send_message(chat_id, "Avevo altri pagamenti in attesa di conferma — li ho sostituiti con questi.")
    total = len(candidates)
    _set_pending_photo_state({"queue": candidates, "index": 1, "total": total})
    send_message(chat_id, _format_confirmation_prompt(candidates[0], 1, total))


def _apply_candidate_correction(candidate: dict, result: dict) -> str | None:
    """Applica al candidato (non ancora salvato) il risultato di
    tool=='correggi_ultima' di _interpret. Ritorna un messaggio d'errore se
    la correzione non è valida, altrimenti None (corretto con successo) —
    stessa validazione per campo di _handle_text, ma su un dict in memoria
    invece che con db.update_transaction."""
    data = result["input"]
    campo = data["campo"]
    if campo == "importo":
        new_amount = abs(float(data.get("nuovo_importo") or 0))
        if new_amount <= 0:
            return "Importo non valido."
        candidate["importo"] = new_amount
    elif campo == "categoria":
        pool = _category_pool(candidate["is_income"])
        new_cat = _match_category(data.get("nuova_categoria") or "", pool)
        if not new_cat:
            return "Categoria non riconosciuta."
        candidate["categoria"] = new_cat
    elif campo == "descrizione":
        new_desc = (data.get("nuova_descrizione") or "").strip()
        if not new_desc:
            return "Descrizione non valida."
        candidate["descrizione"] = new_desc
    elif campo == "data":
        new_date = _valid_iso_date(data.get("nuova_data", ""))
        if not new_date:
            return "Data non valida."
        candidate["data"] = new_date
    elif campo == "nota":
        candidate["note"] = (data.get("nuova_nota") or "").strip()
    return None


def _advance_pending_photo_queue(chat_id, state: dict) -> None:
    """Rimuove il pagamento corrente (già gestito) dalla coda e mostra la
    conferma del prossimo, se ce ne sono altri — altrimenti chiude lo
    stato. Comune a conferma, salto e fallimento DB."""
    state["queue"].pop(0)
    if state["queue"]:
        state["index"] += 1
        _set_pending_photo_state(state)
        send_message(chat_id, _format_confirmation_prompt(state["queue"][0], state["index"], state["total"]))
    else:
        _set_pending_photo_state(None)


def _handle_confirmation_reply(chat_id, text: str, state: dict) -> None:
    norm = text.strip().lower()
    candidate = state["queue"][0]
    is_batch = state["total"] > 1

    if norm in _NEGATIVE_ALL:
        _set_pending_photo_state(None)
        send_message(chat_id, "Annullati tutti i pagamenti rimasti.")
        return

    if norm in _AFFIRMATIVE:
        try:
            new_id = _insert_transaction(
                candidate["descrizione"], candidate["importo"], candidate["categoria"],
                candidate["data"], candidate["is_income"], candidate.get("note", ""),
            )
            db.set_setting(_LAST_TX_KEY, str(new_id))
        except Exception as e:
            print("[telegram] scrittura su DB fallita per conferma foto:", repr(e))
            _enqueue_pending(chat_id, "", kind="confirmed", payload=candidate)
            send_message(
                chat_id,
                "⏳ Confermato, ma il database non risponde ora. L'ho messo "
                "in coda, ci riprovo da solo tra poco. /coda per vedere cosa "
                "c'è in attesa.",
            )
            _advance_pending_photo_queue(chat_id, state)
            return
        verbo = "Registrata entrata" if candidate["is_income"] else "Registrato"
        nota_suffix = f" · nota: {candidate['note']}" if candidate.get("note") else ""
        send_message(
            chat_id,
            f"{verbo} — {candidate['descrizione']} {_fmt_eur(candidate['importo'])} · "
            f"{candidate['categoria']} · {_fmt_date_it(candidate['data'])}{nota_suffix}",
        )
        _advance_pending_photo_queue(chat_id, state)
        return

    if norm in _NEGATIVE:
        send_message(chat_id, "Saltato." if is_batch else "Annullato.")
        _advance_pending_photo_queue(chat_id, state)
        return

    # Non è un sì/no: tentativo di correzione del pagamento corrente,
    # riusando l'interprete testuale esistente (stesso schema/prompt di
    # correzione già usato per _LAST_TX_KEY) — il candidato ha gli stessi
    # campi che _interpret si aspetta da last_tx.
    fake_last_tx = {
        "amount": candidate["importo"] if candidate["is_income"] else -candidate["importo"],
        "description": candidate["descrizione"],
        "category": candidate["categoria"],
        "date": candidate["data"],
        "note": candidate.get("note", ""),
    }
    result = _interpret(text, fake_last_tx, is_income=candidate["is_income"])
    tool = result.get("tool")

    if tool == "errore":
        send_message(
            chat_id,
            "⏳ Non riesco a interpretare la correzione adesso (rete o "
            "modello non disponibile). Riprova, oppure rispondi «sì» per "
            "confermare com'è o «annulla» per saltarla.",
        )
        return

    if tool == "correggi_ultima":
        error = _apply_candidate_correction(candidate, result)
        if error:
            send_message(chat_id, error)
            return
        state["queue"][0] = candidate
        _set_pending_photo_state(state)
        send_message(chat_id, _format_confirmation_prompt(candidate, state["index"], state["total"]))
        return

    send_message(
        chat_id,
        "Rispondi «sì» per confermare, «annulla» per saltarla, o scrivi una "
        "correzione (es. «era 12 non 8»).",
    )


# ─── Entry point ────────────────────────────────────────────────────────────

_COMMANDS = {
    "/start": lambda cid: send_message(cid, _HELP),
    "/aiuto": lambda cid: send_message(cid, _HELP),
    "/help": lambda cid: send_message(cid, _HELP),
    "/oggi": _cmd_oggi,
    "/settimana": _cmd_settimana,
    "/mese": _cmd_mese,
    "/budget": _cmd_budget,
    "/ultima": _cmd_ultima,
    "/cancella": _cmd_cancella,
    "/coda": _cmd_coda,
}


def _already_seen(update_id) -> bool:
    """True se questo update_id di Telegram è già stato preso in carico.

    Scrive subito un segnaposto (INSERT su una PRIMARY KEY): se la stessa
    consegna arriva due volte — Telegram rimanda un update quando non riceve
    una risposta rapida al webhook, e con due macchine Fly la seconda copia
    può capitare sull'altra — la seconda INSERT fallisce per chiave duplicata
    e viene scartata prima di rifare tutta l'elaborazione (chiamata a Gemini,
    inserimento della transazione, messaggio di conferma). In caso di dubbio
    (un errore diverso, es. Turso momentaneamente irraggiungibile) si preferisce
    elaborare comunque: un duplicato occasionale è recuperabile con /cancella,
    un messaggio perso silenziosamente no.
    """
    if update_id is None:
        return False
    try:
        conn = db.get_conn()
        conn.execute(
            "CREATE TABLE IF NOT EXISTS telegram_seen_updates "
            "(update_id INTEGER PRIMARY KEY, seen_at TEXT DEFAULT (datetime('now')))"
        )
        conn.execute("INSERT INTO telegram_seen_updates (update_id) VALUES (?)", (update_id,))
        conn.commit()
        # Pulizia occasionale invece di un job a parte: tiene la tabella
        # piccola senza doverci pensare.
        if update_id % 200 == 0:
            conn.execute(
                "DELETE FROM telegram_seen_updates WHERE seen_at < datetime('now', '-7 days')"
            )
            conn.commit()
        conn.close()
        return False
    except Exception as e:
        msg = str(e).lower()
        if "unique" in msg or "primary key" in msg or "constraint" in msg:
            return True
        print("[telegram] controllo update_id fallito, elaboro comunque:", repr(e))
        return False


def handle_update(update: dict) -> None:
    """Gestisce un update Telegram. Non solleva: logga e basta."""
    message = update.get("message") or update.get("edited_message")
    if not message or ("text" not in message and "photo" not in message):
        return

    if _already_seen(update.get("update_id")):
        print(f"[telegram] update {update.get('update_id')} già elaborato, ignorato (reinvio Telegram)")
        return

    chat = message.get("chat", {})
    chat_id = chat.get("id")

    # Sicurezza: solo il proprietario. Confronto come stringa perché la env var
    # è sempre stringa e chat_id è int.
    if str(chat_id) != str(ALLOWED_CHAT_ID):
        send_message(chat_id, "Questo bot è personale e non risponde a questo account.")
        print(f"[telegram] messaggio ignorato da chat_id non autorizzato: {chat_id}")
        return

    if "photo" in message:
        _handle_photo(chat_id, message["photo"], message.get("caption") or "")
        return

    text = message["text"].strip()
    if not text:
        return

    if text.startswith("/"):
        cmd = text.split()[0].split("@")[0].lower()
        handler = _COMMANDS.get(cmd)
        if handler:
            handler(chat_id)
        else:
            send_message(chat_id, "Comando sconosciuto. /aiuto per la lista.")
        return

    # Se c'è una foto in attesa di conferma, il prossimo testo libero va
    # alla conferma (sì/annulla/correzione), non alla normale registrazione
    # — vedi _handle_confirmation_reply. Il riprocessamento della coda
    # testuale (kind="text") non passa da qui, solo il testo live.
    pending_photo = _get_pending_photo_state()
    if pending_photo is not None:
        _handle_confirmation_reply(chat_id, text, pending_photo)
        return

    _handle_text(chat_id, text)
