import sys
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Stessa logica di database.py: sotto PyInstaller __file__ non è affidabile,
# .env deve stare accanto all'eseguibile (o allo script in sviluppo).
_base_dir = Path(sys.executable).parent if getattr(sys, "frozen", False) else Path(__file__).parent
load_dotenv(_base_dir / ".env")

from database import init_db, init_monthly_summaries, init_planned_expenses
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


@app.on_event("startup")
def on_startup():
    init_db()
    init_monthly_summaries()
    init_planned_expenses()


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


if __name__ == "__main__":
    # Entry point per l'eseguibile PyInstaller — in sviluppo si usa invece
    # `python -m uvicorn main:app`, che non passa da qui.
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
