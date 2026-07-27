from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

import database as db

router = APIRouter()


class PlannedExpenseIn(BaseModel):
    description: str
    amount: float
    category: str
    is_recurring: int = 1


class PlannedExpenseUpdate(BaseModel):
    description: Optional[str] = None
    amount: Optional[float] = None
    category: Optional[str] = None
    is_recurring: Optional[int] = None
    active: Optional[int] = None


class BudgetIn(BaseModel):
    month: str
    total: float
    cat_budgets: dict[str, float]
    note: str = ""


class OverrideIn(BaseModel):
    month: str
    planned_id: int
    amount: float
    is_exceptional: int = 0
    note: str = ""


@router.get("/planned-expenses")
def list_planned_expenses():
    return db.get_planned_expenses()


@router.post("/planned-expenses")
def create_planned_expense(p: PlannedExpenseIn):
    db.add_planned_expense(p.description, p.amount, p.category, p.is_recurring)
    return {"ok": True}


@router.put("/planned-expenses/{pid}")
def edit_planned_expense(pid: int, p: PlannedExpenseUpdate):
    fields = {k: v for k, v in p.model_dump().items() if v is not None}
    if not fields:
        raise HTTPException(status_code=400, detail="Nessun campo da aggiornare")
    db.update_planned_expense(pid, **fields)
    return {"ok": True}


@router.delete("/planned-expenses/{pid}")
def remove_planned_expense(pid: int):
    db.delete_planned_expense(pid)
    return {"ok": True}


@router.get("/budget/{month}")
def get_budget(month: str):
    budget = db.get_monthly_budget(month)
    if not budget:
        raise HTTPException(status_code=404, detail="Nessun budget impostato per questo mese")
    return budget


@router.post("/budget")
def set_budget(b: BudgetIn):
    db.upsert_monthly_budget(b.month, b.total, b.cat_budgets, b.note)
    return {"ok": True}


@router.get("/overrides/{month}")
def get_overrides(month: str):
    return db.get_overrides(month)


@router.post("/overrides")
def set_override(o: OverrideIn):
    db.upsert_override(o.month, o.planned_id, o.amount, o.is_exceptional, o.note)
    return {"ok": True}


@router.delete("/overrides/{month}/{planned_id}")
def remove_override(month: str, planned_id: int):
    db.delete_override(month, planned_id)
    return {"ok": True}
