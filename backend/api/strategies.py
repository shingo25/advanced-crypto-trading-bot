from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from backend.core.security import get_current_user, require_admin
from backend.models.trading import get_strategies_model
import logging

router = APIRouter()
logger = logging.getLogger(__name__)


class StrategyBase(BaseModel):
    name: str
    description: Optional[str] = None
    parameters: Dict[str, Any] = {}
    is_active: bool = False


class StrategyCreate(StrategyBase):
    pass


class StrategyUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None


class Strategy(StrategyBase):
    id: str
    user_id: str
    created_at: Optional[str] = None


@router.get("/", response_model=List[Strategy])
async def get_strategies(current_user: dict = Depends(get_current_user)):
    """戦略一覧を取得（ユーザー専用）"""
    try:
        strategies_model = get_strategies_model()
        user_id = current_user["id"]
        
        strategies = strategies_model.get_user_strategies(user_id)
        
        return [
            Strategy(
                id=s["id"],
                user_id=s["user_id"],
                name=s["name"],
                description=s.get("description"),
                parameters=s.get("parameters", {}),
                is_active=s.get("is_active", False),
                created_at=s.get("created_at")
            )
            for s in strategies
        ]
    except Exception as e:
        logger.error(f"Failed to get strategies for user {current_user['id']}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve strategies")


@router.get("/{strategy_id}", response_model=Strategy)
async def get_strategy(strategy_id: str, current_user: dict = Depends(get_current_user)):
    """特定の戦略を取得"""
    try:
        strategies_model = get_strategies_model()
        strategy = strategies_model.get_strategy_by_id(strategy_id)
        
        if not strategy:
            raise HTTPException(status_code=404, detail="Strategy not found")
        
        # セキュリティ: ユーザーが所有する戦略のみアクセス許可
        if strategy["user_id"] != current_user["id"]:
            raise HTTPException(status_code=403, detail="Access denied")
        
        return Strategy(
            id=strategy["id"],
            user_id=strategy["user_id"],
            name=strategy["name"],
            description=strategy.get("description"),
            parameters=strategy.get("parameters", {}),
            is_active=strategy.get("is_active", False),
            created_at=strategy.get("created_at")
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get strategy {strategy_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve strategy")


@router.post("/", response_model=Strategy)
async def create_strategy(
    strategy: StrategyCreate,
    current_user: dict = Depends(get_current_user)
):
    """新しい戦略を作成（ユーザー専用）"""
    try:
        strategies_model = get_strategies_model()
        user_id = current_user["id"]
        
        created_strategy = strategies_model.create_strategy(
            user_id=user_id,
            name=strategy.name,
            description=strategy.description,
            parameters=strategy.parameters,
            is_active=strategy.is_active
        )
        
        if not created_strategy:
            raise HTTPException(status_code=400, detail="Failed to create strategy")
        
        logger.info(f"Strategy '{strategy.name}' created by {current_user['username']}")
        
        return Strategy(
            id=created_strategy["id"],
            user_id=created_strategy["user_id"],
            name=created_strategy["name"],
            description=created_strategy.get("description"),
            parameters=created_strategy.get("parameters", {}),
            is_active=created_strategy.get("is_active", False),
            created_at=created_strategy.get("created_at")
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create strategy: {e}")
        raise HTTPException(status_code=400, detail="Failed to create strategy")


@router.patch("/{strategy_id}", response_model=Strategy)
async def update_strategy(
    strategy_id: str,
    strategy_update: StrategyUpdate,
    current_user: dict = Depends(get_current_user)
):
    """戦略を更新（ユーザー専用）"""
    try:
        strategies_model = get_strategies_model()
        
        # 既存の戦略を確認
        existing_strategy = strategies_model.get_strategy_by_id(strategy_id)
        if not existing_strategy:
            raise HTTPException(status_code=404, detail="Strategy not found")
        
        # セキュリティ: ユーザーが所有する戦略のみ更新許可
        if existing_strategy["user_id"] != current_user["id"]:
            raise HTTPException(status_code=403, detail="Access denied")
        
        # 更新データを準備
        updates = {}
        if strategy_update.name is not None:
            updates["name"] = strategy_update.name
        if strategy_update.description is not None:
            updates["description"] = strategy_update.description
        if strategy_update.parameters is not None:
            updates["parameters"] = strategy_update.parameters
        if strategy_update.is_active is not None:
            updates["is_active"] = strategy_update.is_active
        
        if not updates:
            # 変更がない場合は既存の戦略を返す
            return await get_strategy(strategy_id, current_user)
        
        updated_strategy = strategies_model.update_strategy(strategy_id, **updates)
        if not updated_strategy:
            raise HTTPException(status_code=400, detail="Failed to update strategy")
        
        logger.info(f"Strategy {strategy_id} updated by {current_user['username']}")
        
        return Strategy(
            id=updated_strategy["id"],
            user_id=updated_strategy["user_id"],
            name=updated_strategy["name"],
            description=updated_strategy.get("description"),
            parameters=updated_strategy.get("parameters", {}),
            is_active=updated_strategy.get("is_active", False),
            created_at=updated_strategy.get("created_at")
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update strategy {strategy_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to update strategy")