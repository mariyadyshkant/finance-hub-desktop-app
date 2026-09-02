import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Stessa logica di database.py: sotto PyInstaller __file__ non è affidabile,
# .env deve stare accanto all'eseguibile (o allo script in sviluppo).
_base_dir = Path(sys.executable).parent if getattr(sys, "frozen", False) else Path(__file__).parent
load_dotenv(_base_dir / ".env")

from database import init_db, init_monthly_summaries, init_planned_expenses, init_settings
from importers.helpers import CATEGORIES, CAT_COLORS
from routes import (
    transactions,
    reimbursements,
    savings,
    shifts,
    salary,
    splitwise,
    summaries,
    planning,
    settings,
    telegram,
)

app = FastAPI(title="FinanceD API")

# App desktop locale: nessun rischio ad aprire il CORS, il backend
# ascolta solo su 127.0.0.1 e il renderer Electron gira su file:// (origin "null").
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Stesso pattern già usato per TURSO_DATABASE_URL: se API_ACCESS_TOKEN non è
# impostata (caso desktop locale, invariato), il middleware non fa nulla. Se
# è impostata (caso hosted su Fly.io per l'app mobile), ogni richiesta senza
# l'header corretto viene rifiutata — esclusa /health, che serve ai controlli
# di Fly.io stesso e non espone dati, e il webhook Telegram, che Telegram
# chiama senza poter mandare header custom (verifica un suo segreto a parte —
# vedi routes/telegram.py).
_TOKEN_EXEMPT = ("/health", "/api/telegram/webhook")


@app.middleware("http")
async def require_api_token(request: Request, call_next):
    token = os.getenv("API_ACCESS_TOKEN")
    if token and not request.url.path.startswith(_TOKEN_EXEMPT):
        if request.headers.get("X-API-Token") != token:
            return JSONResponse(status_code=401, content={"detail": "Token di accesso mancante o non valido"})
    return await call_next(request)


@app.on_event("startup")
def on_startup():
    init_db()
    init_monthly_summaries()
    init_planned_expenses()
    init_settings()


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/api/categories")
def get_categories():
    return {"categories": CATEGORIES, "colors": CAT_COLORS}


app.include_router(transactions.router, prefix="/api/transactions", tags=["transactions"])
app.include_router(reimbursements.router, prefix="/api/reimbursements", tags=["reimbursements"])
app.include_router(savings.router, prefix="/api/savings", tags=["savings"])
app.include_router(shifts.router, prefix="/api/shifts", tags=["shifts"])
app.include_router(salary.router, prefix="/api/salary", tags=["salary"])
app.include_router(splitwise.router, prefix="/api/splitwise", tags=["splitwise"])
app.include_router(summaries.router, prefix="/api/summaries", tags=["summaries"])
app.include_router(planning.router, prefix="/api/planning", tags=["planning"])
app.include_router(settings.router, prefix="/api/settings", tags=["settings"])
app.include_router(telegram.router, prefix="/api/telegram", tags=["telegram"])


if __name__ == "__main__":
    # Entry point per l'eseguibile PyInstaller — in sviluppo si usa invece
    # `python -m uvicorn main:app`, che non passa da qui.
    import os

    import uvicorn

    # Electron sceglie la porta libera e la passa qui via env var, per non
    # bloccarsi se 8000 è già occupata da un altro servizio sulla macchina
    # dell'utente (vedi electron/main.js: findFreePort).
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run(app, host="127.0.0.1", port=port)
