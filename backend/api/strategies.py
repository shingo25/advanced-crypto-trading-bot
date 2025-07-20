from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from backend.core.security import get_current_user
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
                created_at=s.get("created_at"),
            )
            for s in strategies
        ]
    except Exception as e:
        logger.error(f"Failed to get strategies for user {current_user['id']}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve strategies")


@router.get("/{strategy_id}", response_model=Strategy)
async def get_strategy(
    strategy_id: str, current_user: dict = Depends(get_current_user)
):
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
            created_at=strategy.get("created_at"),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get strategy {strategy_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve strategy")


@router.post("/", response_model=Strategy)
async def create_strategy(
    strategy: StrategyCreate, current_user: dict = Depends(get_current_user)
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
            is_active=strategy.is_active,
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
            created_at=created_strategy.get("created_at"),
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
    current_user: dict = Depends(get_current_user),
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
        updates: Dict[str, Any] = {}
        if strategy_update.name is not None:
            updates["name"] = strategy_update.name
        if strategy_update.description is not None:
            updates["description"] = strategy_update.description
        if strategy_update.parameters is not None:
            updates["parameters"] = dict(strategy_update.parameters)
        if strategy_update.is_active is not None:
            updates["is_active"] = bool(strategy_update.is_active)

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
            created_at=updated_strategy.get("created_at"),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update strategy {strategy_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to update strategy")


@router.patch("/{strategy_id}/toggle", response_model=Strategy)
async def toggle_strategy_status(
    strategy_id: str,
    current_user: dict = Depends(get_current_user),
):
    """戦略のアクティブ状態を切り替え"""
    try:
        strategies_model = get_strategies_model()

        # 既存の戦略を確認
        existing_strategy = strategies_model.get_strategy_by_id(strategy_id)
        if not existing_strategy:
            raise HTTPException(status_code=404, detail="Strategy not found")

        # セキュリティ: ユーザーが所有する戦略のみ更新許可
        if existing_strategy["user_id"] != current_user["id"]:
            raise HTTPException(status_code=403, detail="Access denied")

        # アクティブ状態を切り替え
        new_active_status = not existing_strategy.get("is_active", False)
        updated_strategy = strategies_model.update_strategy(
            strategy_id, is_active=new_active_status
        )

        if not updated_strategy:
            raise HTTPException(
                status_code=400, detail="Failed to toggle strategy status"
            )

        action = "activated" if new_active_status else "deactivated"
        logger.info(f"Strategy {strategy_id} {action} by {current_user['username']}")

        return Strategy(
            id=updated_strategy["id"],
            user_id=updated_strategy["user_id"],
            name=updated_strategy["name"],
            description=updated_strategy.get("description"),
            parameters=updated_strategy.get("parameters", {}),
            is_active=updated_strategy.get("is_active", False),
            created_at=updated_strategy.get("created_at"),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to toggle strategy {strategy_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to toggle strategy status")


@router.patch("/{strategy_id}/parameters", response_model=Strategy)
async def update_strategy_parameters(
    strategy_id: str,
    parameters: Dict[str, Any],
    current_user: dict = Depends(get_current_user),
):
    """戦略パラメータを更新"""
    try:
        strategies_model = get_strategies_model()

        # 既存の戦略を確認
        existing_strategy = strategies_model.get_strategy_by_id(strategy_id)
        if not existing_strategy:
            raise HTTPException(status_code=404, detail="Strategy not found")

        # セキュリティ: ユーザーが所有する戦略のみ更新許可
        if existing_strategy["user_id"] != current_user["id"]:
            raise HTTPException(status_code=403, detail="Access denied")

        # パラメータを更新（既存パラメータと新しいパラメータをマージ）
        current_parameters = existing_strategy.get("parameters", {})
        updated_parameters = {**current_parameters, **parameters}

        updated_strategy = strategies_model.update_strategy(
            strategy_id, parameters=updated_parameters
        )

        if not updated_strategy:
            raise HTTPException(
                status_code=400, detail="Failed to update strategy parameters"
            )

        logger.info(
            f"Strategy {strategy_id} parameters updated by {current_user['username']}"
        )

        return Strategy(
            id=updated_strategy["id"],
            user_id=updated_strategy["user_id"],
            name=updated_strategy["name"],
            description=updated_strategy.get("description"),
            parameters=updated_strategy.get("parameters", {}),
            is_active=updated_strategy.get("is_active", False),
            created_at=updated_strategy.get("created_at"),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update strategy parameters {strategy_id}: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to update strategy parameters"
        )


@router.get("/{strategy_id}/status")
async def get_strategy_status(
    strategy_id: str,
    current_user: dict = Depends(get_current_user),
):
    """戦略のステータス情報を取得"""
    try:
        strategies_model = get_strategies_model()

        # 戦略の基本情報を取得
        strategy = strategies_model.get_strategy_by_id(strategy_id)
        if not strategy:
            raise HTTPException(status_code=404, detail="Strategy not found")

        # セキュリティ: ユーザーが所有する戦略のみアクセス許可
        if strategy["user_id"] != current_user["id"]:
            raise HTTPException(status_code=403, detail="Access denied")

        # ステータス情報を構築
        status_info = {
            "strategy_id": strategy_id,
            "name": strategy["name"],
            "is_active": strategy.get("is_active", False),
            "parameters": strategy.get("parameters", {}),
            "created_at": strategy.get("created_at"),
            "health": "healthy",  # 基本的なヘルスチェック
            "last_execution": None,  # 実際の実装では実行履歴から取得
            "performance_summary": {
                "total_trades": 0,
                "win_rate": 0.0,
                "total_return": 0.0,
            },
        }

        # パラメータの妥当性をチェック
        parameters = strategy.get("parameters", {})
        if not parameters:
            status_info["health"] = "warning"
            status_info["health_message"] = "No parameters configured"

        return status_info

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get strategy status {strategy_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get strategy status")


@router.get("/active", response_model=List[Strategy])
async def get_active_strategies(current_user: dict = Depends(get_current_user)):
    """アクティブな戦略一覧を取得"""
    try:
        strategies_model = get_strategies_model()
        user_id = current_user["id"]

        # ユーザーの全戦略を取得してアクティブなもののみフィルタ
        all_strategies = strategies_model.get_user_strategies(user_id)
        active_strategies = [s for s in all_strategies if s.get("is_active", False)]

        return [
            Strategy(
                id=s["id"],
                user_id=s["user_id"],
                name=s["name"],
                description=s.get("description"),
                parameters=s.get("parameters", {}),
                is_active=s.get("is_active", False),
                created_at=s.get("created_at"),
            )
            for s in active_strategies
        ]
    except Exception as e:
        logger.error(
            f"Failed to get active strategies for user {current_user['id']}: {e}"
        )
        raise HTTPException(
            status_code=500, detail="Failed to retrieve active strategies"
        )
