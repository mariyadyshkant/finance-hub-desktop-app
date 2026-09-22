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
"""
import asyncio
import json
import os
from datetime import date, timedelta

import requests

import database as db
from importers.helpers import CATEGORIES

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
# l'una o l'altra, mai ambigua.
_INCOME_CATEGORIES = ["Entrata", "Rimborso ricevuto"]
_EXPENSE_CATEGORIES = [c for c in CATEGORIES if c not in _INCOME_CATEGORIES]

_MESI_IT = [
    "gen", "feb", "mar", "apr", "mag", "giu",
    "lug", "ago", "set", "ott", "nov", "dic",
]
_GIORNI_IT = ["lunedì", "martedì", "mercoledì", "giovedì", "venerdì", "sabato", "domenica"]

_LAST_TX_KEY = "telegram:last_tx_id"

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


def _insert_transaction(
    description: str, amount_abs: float, category: str, date_iso: str, is_income: bool
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
        (date_iso, description, amount, category, "telegram", ""),
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
    categorie = _INCOME_CATEGORIES if is_income else _EXPENSE_CATEGORIES
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
        "usa oggi.\n"
        "- una CORREZIONE dell'ultima registrazione: 'era 54 non 45', "
        "'mettila in Persona', 'la descrizione è sbagliata, è X', 'in realtà "
        "era di ieri' → azione = correggi_ultima, con campo_correzione e il "
        "nuovo valore: nuovo_numero per l'importo, nuovo_testo per categoria/"
        "descrizione, nuovo_testo in formato YYYY-MM-DD per la data.\n"
        "- nient'altro → azione = non_pertinente.\n"
        "Non inventare un importo se il messaggio non ne contiene uno. Riempi "
        f"sempre tutti i campi: usa 0, stringa vuota o '{_NO_FIELD}' per quelli "
        "non pertinenti."
    )


def _response_schema(is_income: bool) -> dict:
    categorie = _INCOME_CATEGORIES if is_income else _EXPENSE_CATEGORIES
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
            "campo_correzione": {
                "type": "string",
                "enum": ["importo", "categoria", "descrizione", "data", _NO_FIELD],
            },
            "nuovo_testo": {"type": "string"},
            "nuovo_numero": {"type": "number"},
        },
        "required": [
            "azione", "descrizione", "importo", "categoria", "data",
            "campo_correzione", "nuovo_testo", "nuovo_numero",
        ],
        "propertyOrdering": [
            "azione", "descrizione", "importo", "categoria", "data",
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
        user_content = (
            f"[Ultima registrazione: {last_tx['description']} "
            f"{segno}{_fmt_eur(abs(last_tx['amount']))} · {last_tx['category']} · "
            f"{last_tx['date']}]\n\n{text}"
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
    categorie_ok = _INCOME_CATEGORIES if is_income else _EXPENSE_CATEGORIES

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
            },
        }

    if azione == "correggi_ultima" and last_tx:
        campo = data.get("campo_correzione")
        if campo not in ("importo", "categoria", "descrizione", "data"):
            return {"tool": "non_pertinente", "input": {"motivo": "correzione senza campo"}}
        return {
            "tool": "correggi_ultima",
            "input": {
                "campo": campo,
                "nuovo_importo": data.get("nuovo_numero", 0),
                "nuova_categoria": data.get("nuovo_testo", "") if campo == "categoria" else "",
                "nuova_descrizione": data.get("nuovo_testo", "") if campo == "descrizione" else "",
                "nuova_data": data.get("nuovo_testo", "") if campo == "data" else "",
            },
        }

    return {"tool": "non_pertinente", "input": {"motivo": "non è una spesa"}}


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
    "Correggi l'ultima registrazione scrivendo in chiaro:\n"
    "  «era 54 non 45» · «mettila in Persona» · «era di ieri»\n\n"
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
    send_message(
        chat_id,
        f"{etichetta}: {tx['description']} {_fmt_eur(abs(tx['amount']))} · "
        f"{tx['category']} · {_fmt_date_it(tx['date'])}\n\n"
        f"Per correggerla scrivi ad es. «era 12 non 8», «mettila in Svago» o "
        f"«era di ieri». Per cancellarla: /cancella",
    )


def _cmd_coda(chat_id):
    pending = _get_pending()
    if not pending:
        send_message(chat_id, "Nessun messaggio in coda.")
        return
    lines = [f"{len(pending)} messaggio/i in attesa:", ""]
    lines += [f"  «{p['text']}» (tentativi: {p['attempts']})" for p in pending[:10]]
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


def _enqueue_pending(chat_id, text: str) -> None:
    conn = db.get_conn()
    _ensure_queue_table(conn)
    conn.execute(
        "INSERT INTO telegram_pending (chat_id, text) VALUES (?,?)",
        (str(chat_id), text),
    )
    conn.commit()
    conn.close()


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


def _process_pending_queue() -> None:
    """Un giro di coda: chiamata dal worker in background, e da nessun altro."""
    if not is_configured():
        return
    for row in _get_pending():
        handled = _handle_text(row["chat_id"], row["text"], announce_queue=False)
        if handled:
            _delete_pending(row["id"])
            continue
        attempts = _bump_pending_attempts(row["id"])
        if attempts >= _QUEUE_MAX_ATTEMPTS:
            _delete_pending(row["id"])
            send_message(
                row["chat_id"],
                f"Non sono riuscito a elaborare questo messaggio dopo "
                f"{attempts} tentativi, l'ho scartato:\n«{row['text']}»\n"
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
        pool = _INCOME_CATEGORIES if is_income else _EXPENSE_CATEGORIES
        category = data["categoria"] if data["categoria"] in pool else pool[0]
        tx_date = _valid_iso_date(data.get("data", "")) or _today_iso()
        new_id = _insert_transaction(desc, amount, category, tx_date, is_income)
        db.set_setting(_LAST_TX_KEY, str(new_id))

        verbo = "Registrata entrata" if is_income else "Registrato"
        today = _today_iso()
        if tx_date == today:
            today_total = _spent_between(today, today)
            month_total = _spent_in_month(today[:7])
            riepilogo = f"Oggi: {_fmt_eur(today_total)} · Questo mese: {_fmt_eur(month_total)}"
        else:
            month_total = _spent_in_month(tx_date[:7])
            riepilogo = f"Totale {tx_date[:7]}: {_fmt_eur(month_total)}"
        send_message(
            chat_id,
            f"{verbo} — {desc} {_fmt_eur(amount)} · {category} · "
            f"{_fmt_date_it(tx_date)}\n{riepilogo}",
        )
        return True

    if tool == "correggi_ultima":
        if not last_tx:
            send_message(chat_id, "Non c'è un'ultima registrazione da correggere.")
            return True
        data = result["input"]
        campo = data["campo"]
        was_income = last_tx["amount"] >= 0

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
            new_cat = data.get("nuova_categoria") or ""
            pool = _INCOME_CATEGORIES if was_income else _EXPENSE_CATEGORIES
            if new_cat not in pool:
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
        return True

    # non_pertinente
    send_message(
        chat_id,
        "Non sembra una registrazione. Scrivi ad es. «€8 bar boulevard» "
        "(spesa) o «+50 stipendio» (entrata), oppure /aiuto per i comandi.",
    )
    return True


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
    if not message or "text" not in message:
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

    _handle_text(chat_id, text)
