from fastapi import APIRouter
from pydantic import BaseModel

import database as db

router = APIRouter()


class SplitwiseKeyIn(BaseModel):
    api_key: str


class ProfileIn(BaseModel):
    display_name: str


@router.get("")
def get_settings():
    return {
        "splitwise_configured": bool(db.get_setting("splitwise_api_key")),
        "display_name": db.get_setting("display_name") or "",
    }


@router.post("/splitwise")
def set_splitwise_key(payload: SplitwiseKeyIn):
    db.set_setting("splitwise_api_key", payload.api_key.strip())
    return {"ok": True}


@router.delete("/splitwise")
def clear_splitwise_key():
    db.set_setting("splitwise_api_key", "")
    return {"ok": True}


@router.post("/profile")
def set_profile(payload: ProfileIn):
    db.set_setting("display_name", payload.display_name.strip())
    return {"ok": True}
