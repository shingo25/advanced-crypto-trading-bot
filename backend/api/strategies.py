from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from backend.core.security import get_current_user, require_admin
from backend.core.database import db
import json
import logging

router = APIRouter()
logger = logging.getLogger(__name__)


class StrategyBase(BaseModel):
    name: str
    enabled: bool = True
    config: Dict[str, Any]


class StrategyCreate(StrategyBase):
    pass


class StrategyUpdate(BaseModel):
    enabled: Optional[bool] = None
    config: Optional[Dict[str, Any]] = None


class Strategy(StrategyBase):
    id: int


@router.get("/", response_model=List[Strategy])
async def get_strategies(current_user: dict = Depends(get_current_user)):
    """戦略一覧を取得"""
    strategies = db.fetchall("SELECT id, name, enabled, config FROM strategies")
    return [
        Strategy(
            id=s[0],
            name=s[1],
            enabled=s[2],
            config=json.loads(s[3]) if s[3] else {}
        )
        for s in strategies
    ]


@router.get("/{strategy_id}", response_model=Strategy)
async def get_strategy(strategy_id: int, current_user: dict = Depends(get_current_user)):
    """特定の戦略を取得"""
    strategy = db.fetchone(
        "SELECT id, name, enabled, config FROM strategies WHERE id = ?",
        [strategy_id]
    )
    if not strategy:
        raise HTTPException(status_code=404, detail="Strategy not found")
    
    return Strategy(
        id=strategy[0],
        name=strategy[1],
        enabled=strategy[2],
        config=json.loads(strategy[3]) if strategy[3] else {}
    )


@router.post("/", response_model=Strategy)
async def create_strategy(
    strategy: StrategyCreate,
    current_user: dict = Depends(require_admin)
):
    """新しい戦略を作成"""
    try:
        db.execute(
            "INSERT INTO strategies (name, enabled, config) VALUES (?, ?, ?)",
            [strategy.name, strategy.enabled, json.dumps(strategy.config)]
        )
        
        # 作成した戦略を取得
        created = db.fetchone("SELECT id FROM strategies WHERE name = ?", [strategy.name])
        logger.info(f"Strategy '{strategy.name}' created by {current_user['username']}")
        
        return await get_strategy(created[0], current_user)
    except Exception as e:
        logger.error(f"Failed to create strategy: {e}")
        raise HTTPException(status_code=400, detail="Failed to create strategy")


@router.patch("/{strategy_id}", response_model=Strategy)
async def update_strategy(
    strategy_id: int,
    strategy_update: StrategyUpdate,
    current_user: dict = Depends(require_admin)
):
    """戦略を更新"""
    # 既存の戦略を確認
    existing = db.fetchone("SELECT id FROM strategies WHERE id = ?", [strategy_id])
    if not existing:
        raise HTTPException(status_code=404, detail="Strategy not found")
    
    # 更新クエリを構築
    updates = []
    params = []
    
    if strategy_update.enabled is not None:
        updates.append("enabled = ?")
        params.append(strategy_update.enabled)
    
    if strategy_update.config is not None:
        updates.append("config = ?")
        params.append(json.dumps(strategy_update.config))
    
    if updates:
        updates.append("updated_at = CURRENT_TIMESTAMP")
        query = f"UPDATE strategies SET {', '.join(updates)} WHERE id = ?"
        params.append(strategy_id)
        db.execute(query, params)
        
        logger.info(f"Strategy {strategy_id} updated by {current_user['username']}")
    
    return await get_strategy(strategy_id, current_user)