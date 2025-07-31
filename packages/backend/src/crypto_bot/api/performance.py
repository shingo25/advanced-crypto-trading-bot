"""
Performance API endpoints
パフォーマンス関連のAPIエンドポイント
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from crypto_bot.core.supabase_db import get_supabase_client

logger = logging.getLogger(__name__)

# ルーター作成
router = APIRouter()


class PerformanceData(BaseModel):
    """パフォーマンスデータモデル"""

    timestamp: datetime
    total_value: float
    daily_return: float
    cumulative_return: float
    drawdown: float


async def calculate_performance_from_price_data(
    period: str = "7d", base_symbol: str = "BTCUSDT", initial_value: float = 100000.0
) -> List[Dict[str, Any]]:
    """
    価格データからパフォーマンスを計算
    実際のポートフォリオデータがないため、BTCUSDTの価格変動を基にモック計算
    """
    try:
        supabase = get_supabase_client()

        # 期間を日数に変換
        period_days = {"1d": 1, "7d": 7, "30d": 30, "90d": 90}.get(period, 7)

        # 開始時刻を計算
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(days=period_days)

        # 価格データを取得（日足データを使用）
        response = (
            supabase.table("price_data")
            .select("*")
            .eq("exchange", "binance")
            .eq("symbol", base_symbol)
            .eq("timeframe", "1d")
            .gte("timestamp", start_time.isoformat())
            .lte("timestamp", end_time.isoformat())
            .order("timestamp", desc=False)
            .execute()
        )

        if not response.data:
            logger.warning("No price data found for performance calculation")
            return []

        performance_data = []
        initial_price = None
        previous_close = None
        max_value = initial_value

        for i, row in enumerate(response.data):
            close_price = float(row["close_price"])
            timestamp = datetime.fromisoformat(row["timestamp"].replace("Z", "+00:00"))

            if initial_price is None:
                initial_price = close_price
                previous_close = close_price

            # 価格変動率を計算
            price_change_ratio = close_price / initial_price
            total_value = initial_value * price_change_ratio

            # 日次リターンを計算
            daily_return = (close_price - previous_close) / previous_close if previous_close else 0.0

            # 累積リターンを計算
            cumulative_return = (close_price - initial_price) / initial_price

            # 最大値を更新
            if total_value > max_value:
                max_value = total_value

            # ドローダウンを計算
            drawdown = (max_value - total_value) / max_value if max_value > 0 else 0.0

            performance_data.append(
                {
                    "timestamp": timestamp.isoformat(),
                    "total_value": total_value,
                    "daily_return": daily_return,
                    "cumulative_return": cumulative_return,
                    "drawdown": drawdown,
                }
            )

            previous_close = close_price

        return performance_data

    except Exception as e:
        logger.error(f"Error calculating performance data: {e}")
        # エラー時はモックデータを返す
        return generate_mock_performance_data(period)


def generate_mock_performance_data(period: str = "7d") -> List[Dict[str, Any]]:
    """モックパフォーマンスデータを生成"""
    import random

    period_days = {"1d": 1, "7d": 7, "30d": 30, "90d": 90}.get(period, 7)

    mock_data = []
    now = datetime.now(timezone.utc)
    initial_value = 100000.0
    current_value = initial_value
    max_value = initial_value

    for i in range(period_days + 1):
        date = now - timedelta(days=period_days - i)

        # ランダムな価格変動を生成（-3% to +3%）
        # nosec B311: デモ用のテストデータ生成のため、暗号学的に安全である必要はない
        daily_change = random.uniform(-0.03, 0.03)  # nosec B311
        current_value *= 1 + daily_change

        # 最大値を更新
        if current_value > max_value:
            max_value = current_value

        # 累積リターンを計算
        cumulative_return = (current_value - initial_value) / initial_value

        # ドローダウンを計算
        drawdown = (max_value - current_value) / max_value if max_value > 0 else 0.0

        mock_data.append(
            {
                "timestamp": date.isoformat(),
                "total_value": current_value,
                "daily_return": daily_change,
                "cumulative_return": cumulative_return,
                "drawdown": drawdown,
            }
        )

    return mock_data


@router.get("/history", response_model=List[PerformanceData])
async def get_performance_history(
    period: str = Query(default="7d", description="期間（1d, 7d, 30d, 90d）"),
):
    """
    パフォーマンス履歴を取得

    - **period**: 取得期間（1d, 7d, 30d, 90d）
    """

    # パラメータバリデーション
    valid_periods = ["1d", "7d", "30d", "90d"]
    if period not in valid_periods:
        raise HTTPException(
            status_code=400,
            detail=f"無効な期間です。有効な値: {', '.join(valid_periods)}",
        )

    try:
        # パフォーマンスデータを計算
        performance_data = await calculate_performance_from_price_data(period)

        # レスポンス形式に変換
        response_data = []
        for item in performance_data:
            response_data.append(
                PerformanceData(
                    timestamp=datetime.fromisoformat(item["timestamp"].replace("Z", "+00:00")),
                    total_value=item["total_value"],
                    daily_return=item["daily_return"],
                    cumulative_return=item["cumulative_return"],
                    drawdown=item["drawdown"],
                )
            )

        return response_data

    except Exception as e:
        logger.error(f"Error in get_performance_history: {e}")
        raise HTTPException(status_code=500, detail="パフォーマンスデータの取得に失敗しました")


@router.get("/summary")
async def get_performance_summary():
    """
    パフォーマンスサマリーを取得
    """
    try:
        # 7日間のパフォーマンスデータを取得
        performance_data = await calculate_performance_from_price_data("7d")

        if not performance_data:
            raise HTTPException(status_code=404, detail="パフォーマンスデータが見つかりません")

        # サマリー統計を計算
        latest = performance_data[-1]
        total_value = latest["total_value"]
        cumulative_return = latest["cumulative_return"]

        # 過去7日間の日次リターンから統計を計算
        daily_returns = [item["daily_return"] for item in performance_data if item["daily_return"] != 0]

        if daily_returns:
            avg_daily_return = sum(daily_returns) / len(daily_returns)
            max_daily_return = max(daily_returns)
            min_daily_return = min(daily_returns)
            volatility = (sum((r - avg_daily_return) ** 2 for r in daily_returns) / len(daily_returns)) ** 0.5
        else:
            avg_daily_return = max_daily_return = min_daily_return = volatility = 0.0

        # 最大ドローダウンを計算
        max_drawdown = max((item["drawdown"] for item in performance_data), default=0.0)

        return {
            "total_value": total_value,
            "cumulative_return": cumulative_return,
            "daily_return_avg": avg_daily_return,
            "daily_return_max": max_daily_return,
            "daily_return_min": min_daily_return,
            "volatility": volatility,
            "max_drawdown": max_drawdown,
            "sharpe_ratio": avg_daily_return / volatility if volatility > 0 else 0.0,
            "calculation_period": "7d",
            "last_updated": datetime.now(timezone.utc).isoformat(),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_performance_summary: {e}")
        raise HTTPException(status_code=500, detail="パフォーマンスサマリーの取得に失敗しました")


@router.get("/health")
async def performance_health():
    """
    Performance APIのヘルスチェック
    """
    try:
        # データベース接続テスト
        supabase = get_supabase_client()
        response = (
            supabase.table("price_data").select("count", count="exact").eq("symbol", "BTCUSDT").limit(1).execute()
        )

        return {
            "status": "healthy",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "database_connection": "ok",
            "btc_records": response.count if response.count else 0,
        }

    except Exception as e:
        logger.error(f"Performance health check failed: {e}")
        raise HTTPException(status_code=503, detail=f"サービス利用不可: {str(e)}")
