from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()

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

app = FastAPI(title="Finance Hub API")

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
