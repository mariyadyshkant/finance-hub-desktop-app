from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel

import database as db

router = APIRouter()


class SalaryIn(BaseModel):
    month: str
    net: float
    gross: Optional[float] = None
    hours_worked: Optional[float] = None
    note: str = ""


@router.get("")
def list_salary_records():
    return db.get_salary_records()


@router.post("")
def create_salary_record(s: SalaryIn):
    db.add_salary_record(s.month, s.net, s.gross, s.hours_worked, s.note)
    return {"ok": True}


@router.delete("/{s_id}")
def remove_salary_record(s_id: int):
    db.delete_salary_record(s_id)
    return {"ok": True}
