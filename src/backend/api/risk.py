"""
Risk Management API

Phase3で実装したAdvancedRiskManagerの機能をAPI化
VaR計算、ストレステスト、動的ポジションサイジングなどの機能を提供
"""

import logging
from datetime import datetime
from typing import Any, Dict, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from src.backend.core.security import get_current_user
from src.backend.risk.advanced_risk_manager import AdvancedRiskManager

router = APIRouter()
logger = logging.getLogger(__name__)

# Global risk manager instance (in production, this would be per-user)
_risk_manager: Optional[AdvancedRiskManager] = None


def get_risk_manager() -> AdvancedRiskManager:
    """リスクマネージャーインスタンスを取得"""
    global _risk_manager
    if _risk_manager is None:
        # AdvancedRiskManagerに空のconfigを渡して初期化
        # 実装では適切なデフォルト値が使用される
        _risk_manager = AdvancedRiskManager(config={})
    return _risk_manager


# Pydantic models
class VaRRequest(BaseModel):
    """VaR計算リクエスト"""

    portfolio_id: str = Field(default="default", description="ポートフォリオID")
    confidence_level: float = Field(default=0.95, ge=0.5, le=0.99, description="信頼水準 (0.5-0.99)")
    time_horizon: str = Field(default="1d", description="時間軸 (1d, 5d, 1w)")
    method: Literal["historical", "parametric", "monte_carlo"] = Field(default="historical", description="VaR計算手法")


class VaRResponse(BaseModel):
    """VaR計算結果"""

    portfolio_id: str
    confidence_level: float
    time_horizon: str
    method: str
    var_amount: float
    var_percentage: float
    portfolio_value: float
    calculated_at: datetime


class StressTestRequest(BaseModel):
    """ストレステストリクエスト"""

    scenario: str = Field(..., description="シナリオ名")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="シナリオパラメータ")


class StressTestResponse(BaseModel):
    """ストレステスト結果"""

    scenario: str
    portfolio_loss: float
    portfolio_loss_percentage: float
    individual_losses: Dict[str, float]
    total_portfolio_value: float
    tested_at: datetime


class PositionSizingRequest(BaseModel):
    """ポジションサイジングリクエスト"""

    strategy_name: str = Field(..., description="戦略名")
    symbol: str = Field(..., description="取引シンボル")
    entry_price: float = Field(..., gt=0, description="エントリー価格")
    direction: Literal["long", "short"] = Field(default="long", description="取引方向")


class PositionSizingResponse(BaseModel):
    """ポジションサイジング結果"""

    strategy_name: str
    symbol: str
    recommended_size_usd: float
    recommended_quantity: float
    risk_per_trade: float
    stop_loss_price: Optional[float]
    take_profit_price: Optional[float]
    max_position_size: float


class RiskSummaryResponse(BaseModel):
    """リスクサマリー"""

    total_portfolio_value: float
    overall_var: Dict[str, Any]
    risk_metrics: Dict[str, Any]
    active_risk_alerts: int
    last_updated: datetime


@router.get("/summary", response_model=RiskSummaryResponse)
async def get_risk_summary(current_user: dict = Depends(get_current_user)):
    """ポートフォリオ全体のリスクサマリーを取得"""
    try:
        risk_manager = get_risk_manager()

        # ダミーポートフォリオデータ（実際の実装では取得）
        portfolio_value = 100000.0

        # VaR計算
        var_result = risk_manager.calculate_var(
            returns=[0.01, -0.02, 0.015, -0.005, 0.008],  # ダミーデータ
            confidence_levels=[0.95],
            method="historical",
        )

        # リスクメトリクス計算
        portfolio_returns = [0.01, -0.02, 0.015, -0.005, 0.008]  # ダミーデータ
        strategy_returns = {"default": portfolio_returns}  # ダミーデータ
        portfolio_positions = {"BTC": 0.5, "ETH": 0.3, "ADA": 0.2}  # ダミーデータ

        risk_metrics = risk_manager.calculate_portfolio_risk_metrics(
            portfolio_returns=portfolio_returns,
            strategy_returns=strategy_returns,
            portfolio_positions=portfolio_positions,
        )

        return RiskSummaryResponse(
            total_portfolio_value=portfolio_value,
            overall_var={
                "confidence_level": 0.95,
                "time_horizon": "1d",
                "amount": var_result * portfolio_value,
                "percentage": var_result,
            },
            risk_metrics=risk_metrics,
            active_risk_alerts=0,  # 実際の実装では計算
            last_updated=datetime.now(),
        )

    except Exception as e:
        logger.error(f"Failed to get risk summary: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get risk summary: {str(e)}")


@router.post("/var", response_model=VaRResponse)
async def calculate_var(request: VaRRequest, current_user: dict = Depends(get_current_user)):
    """指定パラメータでVaRを計算"""
    try:
        risk_manager = get_risk_manager()

        # ダミーデータ（実際の実装では時系列データを取得）
        returns = [
            0.01,
            -0.02,
            0.015,
            -0.005,
            0.008,
            0.012,
            -0.008,
            0.003,
            -0.015,
            0.007,
        ]
        portfolio_value = 100000.0

        # 統一されたcalculate_varメソッドを使用
        var_result = risk_manager.calculate_var(
            returns, confidence_levels=[request.confidence_level], method=request.method
        )

        # VaRResultから適切な値を取得
        var_value = var_result.var_95 if request.confidence_level == 0.95 else var_result.var_99

        return VaRResponse(
            portfolio_id=request.portfolio_id,
            confidence_level=request.confidence_level,
            time_horizon=request.time_horizon,
            method=request.method,
            var_amount=var_value * portfolio_value,
            var_percentage=var_value,
            portfolio_value=portfolio_value,
            calculated_at=datetime.now(),
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to calculate VaR: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to calculate VaR: {str(e)}")


@router.post("/stress-test", response_model=StressTestResponse)
async def run_stress_test(request: StressTestRequest, current_user: dict = Depends(get_current_user)):
    """ストレステストを実行"""
    try:
        # ダミーポートフォリオデータ
        portfolio_value = 100000.0
        positions = {
            "BTCUSDT": {"value": 50000.0, "weight": 0.5},
            "ETHUSDT": {"value": 30000.0, "weight": 0.3},
            "BNBUSDT": {"value": 20000.0, "weight": 0.2},
        }

        # ストレステスト実行
        if request.scenario == "BTC_CRASH_30_PERCENT":
            # BTCが30%下落するシナリオ
            btc_impact = positions["BTCUSDT"]["value"] * 0.30
            total_loss = btc_impact

            individual_losses = {
                "BTCUSDT": btc_impact,
                "ETHUSDT": 0.0,  # 他の通貨への波及効果は簡略化
                "BNBUSDT": 0.0,
            }

        elif request.scenario == "MARKET_CRASH_20_PERCENT":
            # 全体的に20%下落するシナリオ
            total_loss = portfolio_value * 0.20
            individual_losses = {symbol: pos["value"] * 0.20 for symbol, pos in positions.items()}

        elif request.scenario == "FLASH_CRASH_50_PERCENT":
            # 瞬間的に50%下落するシナリオ
            total_loss = portfolio_value * 0.50
            individual_losses = {symbol: pos["value"] * 0.50 for symbol, pos in positions.items()}

        else:
            raise ValueError(f"Unsupported stress test scenario: {request.scenario}")

        return StressTestResponse(
            scenario=request.scenario,
            portfolio_loss=total_loss,
            portfolio_loss_percentage=total_loss / portfolio_value,
            individual_losses=individual_losses,
            total_portfolio_value=portfolio_value,
            tested_at=datetime.now(),
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to run stress test: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to run stress test: {str(e)}")


@router.get("/position-sizing", response_model=PositionSizingResponse)
async def get_position_sizing(
    strategy_name: str = Query(..., description="戦略名"),
    symbol: str = Query(..., description="取引シンボル"),
    entry_price: float = Query(..., gt=0, description="エントリー価格"),
    direction: str = Query(default="long", description="取引方向"),
    current_user: dict = Depends(get_current_user),
):
    """推奨ポジションサイズを取得"""
    try:
        risk_manager = get_risk_manager()

        # ダミーデータ（実際の実装では戦略設定から取得）
        portfolio_value = 100000.0
        risk_per_trade = 0.01  # 1%リスク
        max_position_size = portfolio_value * 0.1  # 最大10%

        # 動的ポジションサイジング
        volatility = 0.025  # ダミーボラティリティ
        recent_performance = 0.05  # ダミーパフォーマンス

        position_size = risk_manager.calculate_dynamic_position_size(
            base_capital=portfolio_value,
            volatility=volatility,
            recent_performance=recent_performance,
        )

        # 最大ポジションサイズで制限
        recommended_size = min(position_size, max_position_size)
        recommended_quantity = recommended_size / entry_price

        # ストップロス計算（簡略化）
        stop_loss_distance = volatility * 2  # ボラティリティの2倍
        if direction == "long":
            stop_loss_price = entry_price * (1 - stop_loss_distance)
            take_profit_price = entry_price * (1 + stop_loss_distance * 2)
        else:
            stop_loss_price = entry_price * (1 + stop_loss_distance)
            take_profit_price = entry_price * (1 - stop_loss_distance * 2)

        return PositionSizingResponse(
            strategy_name=strategy_name,
            symbol=symbol,
            recommended_size_usd=recommended_size,
            recommended_quantity=recommended_quantity,
            risk_per_trade=risk_per_trade,
            stop_loss_price=stop_loss_price,
            take_profit_price=take_profit_price,
            max_position_size=max_position_size,
        )

    except Exception as e:
        logger.error(f"Failed to calculate position sizing: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to calculate position sizing: {str(e)}")


@router.get("/scenarios")
async def get_available_stress_test_scenarios(
    current_user: dict = Depends(get_current_user),
):
    """利用可能なストレステストシナリオ一覧を取得"""
    scenarios = [
        {
            "name": "BTC_CRASH_30_PERCENT",
            "description": "Bitcoin 30%下落シナリオ",
            "parameters": {"percentage_drop": 0.30},
        },
        {
            "name": "MARKET_CRASH_20_PERCENT",
            "description": "市場全体 20%下落シナリオ",
            "parameters": {"percentage_drop": 0.20},
        },
        {
            "name": "FLASH_CRASH_50_PERCENT",
            "description": "フラッシュクラッシュ 50%下落シナリオ",
            "parameters": {"percentage_drop": 0.50},
        },
    ]

    return {"scenarios": scenarios}


@router.get("/health")
async def risk_health_check():
    """リスクシステムのヘルスチェック"""
    try:
        risk_manager = get_risk_manager()

        health_data = {
            "status": "healthy",
            "risk_manager_initialized": risk_manager is not None,
            "available_methods": ["historical", "parametric", "monte_carlo"],
            "available_scenarios": [
                "BTC_CRASH_30_PERCENT",
                "MARKET_CRASH_20_PERCENT",
                "FLASH_CRASH_50_PERCENT",
            ],
            "timestamp": datetime.now().isoformat(),
        }

        return health_data

    except Exception as e:
        logger.error(f"Risk health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
        }
