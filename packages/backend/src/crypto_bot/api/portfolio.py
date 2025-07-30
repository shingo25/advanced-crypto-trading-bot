"""
Advanced Portfolio Management API

Phase3で実装したAdvancedPortfolioManagerの機能をAPI化
戦略配分、パフォーマンス追跡、リバランシングなどの機能を提供
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from crypto_bot.core.security import get_current_user
from crypto_bot.portfolio.strategy_portfolio_manager import (
    AdvancedPortfolioManager,
    StrategyStatus,
)
from crypto_bot.strategies.base import BaseStrategy
from crypto_bot.strategies.implementations.bollinger_strategy import BollingerBandsStrategy
from crypto_bot.strategies.implementations.macd_strategy import MACDStrategy
from crypto_bot.strategies.implementations.rsi_strategy import RSIStrategy

router = APIRouter()
logger = logging.getLogger(__name__)

# Global portfolio manager instance (in production, this would be per-user)
_portfolio_manager: Optional[AdvancedPortfolioManager] = None


def get_portfolio_manager() -> AdvancedPortfolioManager:
    """ポートフォリオマネージャーインスタンスを取得"""
    global _portfolio_manager
    if _portfolio_manager is None:
        _portfolio_manager = AdvancedPortfolioManager(initial_capital=100000.0)
    return _portfolio_manager


# Pydantic models
class StrategyAllocationRequest(BaseModel):
    """戦略追加リクエスト"""

    strategy_type: str = Field(..., description="戦略タイプ (rsi, macd, bollinger)")
    allocation_weight: float = Field(..., ge=0.01, le=1.0, description="配分重み (0.01-1.0)")
    parameters: Optional[Dict[str, Any]] = Field(default_factory=dict, description="戦略パラメータ")
    symbol: str = Field(default="BTCUSDT", description="取引シンボル")
    timeframe: str = Field(default="1h", description="時間足")


class StrategyAllocationResponse(BaseModel):
    """戦略配分レスポンス"""

    strategy_name: str
    strategy_type: str
    allocation_weight: float
    allocated_capital: float
    status: str
    symbol: str
    timeframe: str
    parameters: Dict[str, Any]
    performance: Optional[Dict[str, Any]] = None


class StrategyStatusUpdate(BaseModel):
    """戦略ステータス更新"""

    status: str = Field(..., description="新しいステータス (active, paused, disabled)")


class PortfolioOverview(BaseModel):
    """ポートフォリオ概要"""

    initial_capital: float
    current_capital: float
    total_strategies: int
    active_strategies: int
    total_return: float
    sharpe_ratio: float
    max_drawdown: float
    win_rate: float


class PortfolioSummaryResponse(BaseModel):
    """ポートフォリオサマリー"""

    portfolio_overview: PortfolioOverview
    strategy_allocations: Dict[str, StrategyAllocationResponse]
    performance_metrics: Dict[str, Any]
    risk_metrics: Dict[str, Any]
    trade_summary: Dict[str, Any]


class RebalanceResponse(BaseModel):
    """リバランシング提案"""

    rebalancing_actions: List[Dict[str, Any]]
    current_allocations: Dict[str, float]
    recommended_allocations: Dict[str, float]
    expected_improvement: Dict[str, Any]


def create_strategy_instance(
    strategy_type: str, symbol: str, timeframe: str, parameters: Dict[str, Any]
) -> BaseStrategy:
    """戦略インスタンスを作成"""
    strategy_name = f"{strategy_type.upper()}_Strategy"

    if strategy_type.lower() == "rsi":
        strategy = RSIStrategy(
            name=strategy_name,
            symbol=symbol,
            timeframe=timeframe,
            parameters={
                "required_data_length": 50,
                "rsi_period": parameters.get("rsi_period", 14),
                "oversold": parameters.get("oversold", 30),
                "overbought": parameters.get("overbought", 70),
                **parameters,
            },
        )
    elif strategy_type.lower() == "macd":
        strategy = MACDStrategy(
            name=strategy_name,
            symbol=symbol,
            timeframe=timeframe,
            parameters={
                "required_data_length": 50,
                "fast_period": parameters.get("fast_period", 12),
                "slow_period": parameters.get("slow_period", 26),
                "signal_period": parameters.get("signal_period", 9),
                **parameters,
            },
        )
    elif strategy_type.lower() == "bollinger":
        strategy = BollingerBandsStrategy(
            name=strategy_name,
            symbol=symbol,
            timeframe=timeframe,
            parameters={
                "required_data_length": 50,
                "bb_period": parameters.get("bb_period", 20),
                "bb_std_dev": parameters.get("bb_std_dev", 2.0),
                **parameters,
            },
        )
    else:
        raise ValueError(f"Unsupported strategy type: {strategy_type}")

    return strategy


@router.get("/", response_model=PortfolioSummaryResponse)
async def get_portfolio_summary(current_user: dict = Depends(get_current_user)):
    """ポートフォリオサマリーを取得"""
    try:
        portfolio_manager = get_portfolio_manager()
        summary = portfolio_manager.get_portfolio_summary()

        # レスポンス形式に変換
        portfolio_overview = PortfolioOverview(
            initial_capital=summary["portfolio_overview"]["initial_capital"],
            current_capital=summary["portfolio_overview"]["current_capital"],
            total_strategies=summary["portfolio_overview"]["total_strategies"],
            active_strategies=summary["portfolio_overview"]["active_strategies"],
            total_return=summary["performance_metrics"]["total_return"],
            sharpe_ratio=summary["performance_metrics"]["sharpe_ratio"],
            max_drawdown=summary["performance_metrics"]["max_drawdown"],
            win_rate=summary["performance_metrics"]["win_rate"],
        )

        # 戦略配分情報を変換
        strategy_allocations = {}
        for strategy_name, alloc_data in summary["strategy_allocations"].items():
            allocation = portfolio_manager.strategy_allocations.get(strategy_name)
            if allocation:
                strategy_allocations[strategy_name] = StrategyAllocationResponse(
                    strategy_name=strategy_name,
                    strategy_type=allocation.strategy_instance.__class__.__name__.replace("Strategy", "").lower(),
                    allocation_weight=alloc_data["target_weight"],
                    allocated_capital=alloc_data["allocated_capital"],
                    status=alloc_data["status"],
                    symbol=allocation.strategy_instance.symbol,
                    timeframe=allocation.strategy_instance.timeframe,
                    parameters=allocation.strategy_instance.parameters,
                    performance=alloc_data["performance"],
                )

        return PortfolioSummaryResponse(
            portfolio_overview=portfolio_overview,
            strategy_allocations=strategy_allocations,
            performance_metrics=summary["performance_metrics"],
            risk_metrics=summary["risk_metrics"],
            trade_summary=summary["trade_summary"],
        )

    except Exception as e:
        logger.error(f"Failed to get portfolio summary: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get portfolio summary: {str(e)}")


@router.post("/strategies", response_model=StrategyAllocationResponse)
async def add_strategy(request: StrategyAllocationRequest, current_user: dict = Depends(get_current_user)):
    """新しい戦略をポートフォリオに追加"""
    try:
        portfolio_manager = get_portfolio_manager()

        # 戦略インスタンスを作成
        strategy = create_strategy_instance(
            strategy_type=request.strategy_type,
            symbol=request.symbol,
            timeframe=request.timeframe,
            parameters=request.parameters,
        )

        # ポートフォリオに追加
        success = portfolio_manager.add_strategy(
            strategy=strategy,
            allocation_weight=request.allocation_weight,
            status=StrategyStatus.ACTIVE,
        )

        if not success:
            raise HTTPException(status_code=400, detail="Failed to add strategy to portfolio")

        logger.info(f"Strategy {strategy.name} added to portfolio by user {current_user['id']}")

        # 追加された戦略情報を返す
        allocation = portfolio_manager.strategy_allocations[strategy.name]
        return StrategyAllocationResponse(
            strategy_name=strategy.name,
            strategy_type=request.strategy_type,
            allocation_weight=allocation.target_weight,
            allocated_capital=allocation.allocated_capital,
            status=allocation.status.value,
            symbol=strategy.symbol,
            timeframe=strategy.timeframe,
            parameters=strategy.parameters,
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to add strategy: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to add strategy: {str(e)}")


@router.delete("/strategies/{strategy_name}")
async def remove_strategy(strategy_name: str, current_user: dict = Depends(get_current_user)):
    """戦略をポートフォリオから削除"""
    try:
        portfolio_manager = get_portfolio_manager()

        success = portfolio_manager.remove_strategy(strategy_name)
        if not success:
            raise HTTPException(status_code=404, detail="Strategy not found")

        logger.info(f"Strategy {strategy_name} removed from portfolio by user {current_user['id']}")
        return {"message": f"Strategy {strategy_name} removed successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to remove strategy {strategy_name}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to remove strategy: {str(e)}")


@router.patch("/strategies/{strategy_name}/status")
async def update_strategy_status(
    strategy_name: str,
    status_update: StrategyStatusUpdate,
    current_user: dict = Depends(get_current_user),
):
    """戦略のステータスを更新"""
    try:
        portfolio_manager = get_portfolio_manager()

        # ステータス文字列をenumに変換
        status_mapping = {
            "active": StrategyStatus.ACTIVE,
            "paused": StrategyStatus.PAUSED,
            "disabled": StrategyStatus.DISABLED,
        }

        if status_update.status not in status_mapping:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid status. Must be one of: {list(status_mapping.keys())}",
            )

        new_status = status_mapping[status_update.status]
        success = portfolio_manager.update_strategy_status(strategy_name, new_status)

        if not success:
            raise HTTPException(status_code=404, detail="Strategy not found")

        logger.info(f"Strategy {strategy_name} status updated to {status_update.status} by user {current_user['id']}")
        return {"message": f"Strategy {strategy_name} status updated to {status_update.status}"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update strategy status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update strategy status: {str(e)}")


@router.get("/strategies/{strategy_name}/performance", response_model=Dict[str, Any])
async def get_strategy_performance(strategy_name: str, current_user: dict = Depends(get_current_user)):
    """特定戦略のパフォーマンスを取得"""
    try:
        portfolio_manager = get_portfolio_manager()

        if strategy_name not in portfolio_manager.strategy_allocations:
            raise HTTPException(status_code=404, detail="Strategy not found")

        performance = portfolio_manager.calculate_strategy_performance(strategy_name)

        return {
            "strategy_name": strategy_name,
            "total_return": performance.total_return,
            "win_rate": performance.win_rate,
            "trades_count": performance.trades_count,
            "avg_trade_return": performance.avg_trade_return,
            "sharpe_ratio": performance.sharpe_ratio,
            "max_drawdown": performance.max_drawdown,
            "profit_factor": performance.profit_factor,
            "volatility": performance.volatility,
            "var_95": performance.var_95,
            "calmar_ratio": performance.calmar_ratio,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get strategy performance: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get strategy performance: {str(e)}")


@router.get("/correlation", response_model=Dict[str, Any])
async def get_strategy_correlation(current_user: dict = Depends(get_current_user)):
    """戦略間相関行列を取得"""
    try:
        portfolio_manager = get_portfolio_manager()
        correlation_matrix = portfolio_manager.get_strategy_correlation_matrix()

        if correlation_matrix.empty:
            return {
                "message": "Not enough data for correlation analysis",
                "correlation_matrix": {},
            }

        return {
            "correlation_matrix": correlation_matrix.to_dict(),
            "max_correlation": float(correlation_matrix.abs().max().max()),
            "avg_correlation": float(correlation_matrix.abs().mean().mean()),
            "strategy_count": len(correlation_matrix.columns),
        }

    except Exception as e:
        logger.error(f"Failed to get strategy correlation: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get strategy correlation: {str(e)}")


@router.post("/rebalance", response_model=RebalanceResponse)
async def get_rebalance_recommendations(current_user: dict = Depends(get_current_user)):
    """リバランシング提案を取得"""
    try:
        portfolio_manager = get_portfolio_manager()
        rebalance_actions = portfolio_manager.rebalance_strategies()

        # 現在の配分を取得
        current_allocations = {
            name: allocation.target_weight for name, allocation in portfolio_manager.strategy_allocations.items()
        }

        # 推奨配分を計算（リバランシングアクション適用後）
        recommended_allocations = current_allocations.copy()
        for action in rebalance_actions:
            strategy_name = action["strategy"]
            recommended_allocations[strategy_name] = action["new_weight"]

        # 期待される改善効果を計算
        expected_improvement = {
            "risk_reduction": len([a for a in rebalance_actions if "reduce" in a.get("reason", "").lower()]),
            "diversification_improvement": len(
                [a for a in rebalance_actions if "diversif" in a.get("reason", "").lower()]
            ),
            "performance_optimization": len(
                [a for a in rebalance_actions if "performance" in a.get("reason", "").lower()]
            ),
        }

        return RebalanceResponse(
            rebalancing_actions=rebalance_actions,
            current_allocations=current_allocations,
            recommended_allocations=recommended_allocations,
            expected_improvement=expected_improvement,
        )

    except Exception as e:
        logger.error(f"Failed to get rebalance recommendations: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get rebalance recommendations: {str(e)}")


@router.get("/risk-report", response_model=Dict[str, Any])
async def get_portfolio_risk_report(current_user: dict = Depends(get_current_user)):
    """ポートフォリオリスクレポートを取得"""
    try:
        portfolio_manager = get_portfolio_manager()
        risk_report = portfolio_manager.get_risk_report()

        return risk_report

    except Exception as e:
        logger.error(f"Failed to get portfolio risk report: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get portfolio risk report: {str(e)}")


@router.post("/optimize", response_model=Dict[str, Any])
async def get_portfolio_optimization(current_user: dict = Depends(get_current_user)):
    """ポートフォリオ最適化提案を取得"""
    try:
        portfolio_manager = get_portfolio_manager()
        optimization = portfolio_manager.optimize_portfolio()

        return optimization

    except Exception as e:
        logger.error(f"Failed to get portfolio optimization: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get portfolio optimization: {str(e)}")


@router.get("/health")
async def portfolio_health_check():
    """ポートフォリオシステムのヘルスチェック"""
    try:
        portfolio_manager = get_portfolio_manager()

        health_data = {
            "status": "healthy",
            "portfolio_initialized": portfolio_manager is not None,
            "strategies_count": len(portfolio_manager.strategy_allocations),
            "total_capital": portfolio_manager.current_capital,
            "trade_history_count": len(portfolio_manager.trade_history),
            "timestamp": datetime.now().isoformat(),
        }

        return health_data

    except Exception as e:
        logger.error(f"Portfolio health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
        }
