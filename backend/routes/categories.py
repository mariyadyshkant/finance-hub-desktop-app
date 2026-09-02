from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

import database as db

router = APIRouter()


class CategoryIn(BaseModel):
    name: str
    color: str = "#0e7490"


class CategoryUpdate(BaseModel):
    name: Optional[str] = None
    color: Optional[str] = None


def _names():
    return {c["name"] for c in db.get_categories()}


@router.post("")
def create_category(c: CategoryIn):
    name = c.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Il nome non può essere vuoto")
    if name in _names():
        raise HTTPException(status_code=409, detail=f"La categoria «{name}» esiste già")
    db.add_category(name, c.color.strip() or "#0e7490")
    return {"ok": True}


@router.put("/{name}")
def update_category(name: str, c: CategoryUpdate):
    names = _names()
    if name not in names:
        raise HTTPException(status_code=404, detail="Categoria non trovata")

    if c.color is not None and c.color.strip():
        db.set_category_color(name, c.color.strip())

    if c.name is not None:
        new_name = c.name.strip()
        if new_name and new_name != name:
            if new_name in names:
                raise HTTPException(status_code=409, detail=f"La categoria «{new_name}» esiste già")
            db.rename_category(name, new_name)

    return {"ok": True}


@router.delete("/{name}")
def remove_category(name: str, reassign_to: str):
    names = _names()
    if name not in names:
        raise HTTPException(status_code=404, detail="Categoria non trovata")
    target = reassign_to.strip()
    if target == name or target not in names:
        raise HTTPException(status_code=400, detail="Categoria di destinazione non valida")
    db.delete_category(name, target)
    return {"ok": True}
