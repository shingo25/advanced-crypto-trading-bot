from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Any, Dict
from backend.core.security import get_current_user, require_admin
from backend.core.database import db
import json
import logging

router = APIRouter()
logger = logging.getLogger(__name__)


class ConfigValue(BaseModel):
    value: Any


class ConfigItem(BaseModel):
    key: str
    value: Any


@router.get("/dd", response_model=ConfigValue)
async def get_drawdown_config(current_user: dict = Depends(get_current_user)):
    """最大ドローダウン設定を取得"""
    config = db.fetchone("SELECT value FROM config WHERE key = ?", ["max_dd_pct"])
    if not config:
        raise HTTPException(status_code=404, detail="Config not found")

    return ConfigValue(value=json.loads(config[0])["value"])


@router.post("/dd")
async def set_drawdown_config(
    config: ConfigValue, current_user: dict = Depends(require_admin)
):
    """最大ドローダウン設定を更新"""
    db.execute(
        "INSERT OR REPLACE INTO config (key, value, updated_at) VALUES (?, ?, CURRENT_TIMESTAMP)",
        ["max_dd_pct", json.dumps({"value": config.value})],
    )

    logger.info(
        f"Max drawdown updated to {config.value}% by {current_user['username']}"
    )
    return {"ok": True}


@router.get("/position-size", response_model=ConfigValue)
async def get_position_size_config(current_user: dict = Depends(get_current_user)):
    """最大ポジションサイズ設定を取得"""
    config = db.fetchone(
        "SELECT value FROM config WHERE key = ?", ["max_position_size_pct"]
    )
    if not config:
        raise HTTPException(status_code=404, detail="Config not found")

    return ConfigValue(value=json.loads(config[0])["value"])


@router.post("/position-size")
async def set_position_size_config(
    config: ConfigValue, current_user: dict = Depends(require_admin)
):
    """最大ポジションサイズ設定を更新"""
    db.execute(
        "INSERT OR REPLACE INTO config (key, value, updated_at) VALUES (?, ?, CURRENT_TIMESTAMP)",
        ["max_position_size_pct", json.dumps({"value": config.value})],
    )

    logger.info(
        f"Max position size updated to {config.value}% by {current_user['username']}"
    )
    return {"ok": True}


@router.get("/", response_model=Dict[str, Any])
async def get_all_config(current_user: dict = Depends(get_current_user)):
    """すべての設定を取得"""
    configs = db.fetchall("SELECT key, value FROM config")
    return {config[0]: json.loads(config[1])["value"] for config in configs}
