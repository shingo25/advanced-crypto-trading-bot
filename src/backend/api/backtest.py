import asyncio
import logging
from datetime import date, datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel

from backend.backtesting.engine import BacktestEngine
from backend.core.security import get_current_user, require_admin
from backend.strategies.loader import StrategyLoader

router = APIRouter()
logger = logging.getLogger(__name__)


class BacktestRequest(BaseModel):
    strategy_name: str
    symbol: str = "BTC/USDT"
    timeframe: str = "1h"
    start_date: date
    end_date: date
    initial_capital: float = 10000.0
    commission: float = 0.001
    slippage: float = 0.0005
    exchange: str = "binance"
    use_real_data: bool = True
    data_quality_threshold: float = 0.95
    config: Optional[Dict[str, Any]] = None


class DataQualityResponse(BaseModel):
    symbol: str
    timeframe: str
    total_records: int
    missing_records: int
    duplicate_records: int
    data_coverage: float
    quality_score: float
    issues: List[str]
    is_valid: bool


class BacktestResponse(BaseModel):
    backtest_id: str
    status: str
    message: str


class BacktestResult(BaseModel):
    id: int
    strategy_id: int
    start_date: date
    end_date: date
    initial_capital: float
    final_capital: float
    total_trades: int
    win_rate: float
    sharpe_ratio: float
    max_drawdown: float
    results: Dict[str, Any]


@router.post("/validate-data", response_model=DataQualityResponse)
async def validate_backtest_data(
    symbol: str,
    timeframe: str,
    start_date: date,
    end_date: date,
    exchange: str = "binance",
    current_user: dict = Depends(get_current_user),
):
    """バックテスト用データの品質を事前確認"""
    try:
        # バックテストエンジンを初期化
        engine = BacktestEngine(exchange=exchange, use_real_data=True)

        # データ品質をチェック
        quality_report = await engine.validate_backtest_data(
            symbol=symbol,
            timeframe=timeframe,
            start_date=datetime.combine(start_date, datetime.min.time()),
            end_date=datetime.combine(end_date, datetime.min.time()),
        )

        return DataQualityResponse(
            symbol=quality_report.symbol,
            timeframe=quality_report.timeframe,
            total_records=quality_report.total_records,
            missing_records=quality_report.missing_records,
            duplicate_records=quality_report.duplicate_records,
            data_coverage=quality_report.data_coverage,
            quality_score=quality_report.quality_score,
            issues=quality_report.issues,
            is_valid=quality_report.is_valid(),
        )

    except Exception as e:
        logger.error(f"Data validation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/run", response_model=BacktestResponse)
async def run_backtest(
    backtest_request: BacktestRequest,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(require_admin),
):
    """実データを使用してバックテストを実行"""
    try:
        # ストラテジーローダーで戦略を取得
        strategy_loader = StrategyLoader()
        strategy = strategy_loader.load_strategy(backtest_request.strategy_name)

        if not strategy:
            raise HTTPException(status_code=404, detail="Strategy not found")

        # バックテストをバックグラウンドで実行
        background_tasks.add_task(_run_enhanced_backtest_task, backtest_request, current_user["username"])

        logger.info(
            f"Enhanced backtest queued for strategy {backtest_request.strategy_name} by {current_user['username']}"
        )

        return BacktestResponse(
            backtest_id="",  # バックグラウンド処理で生成される
            status="queued",
            message="Backtest started with real data processing",
        )

    except Exception as e:
        logger.error(f"Backtest request failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/results", response_model=List[Dict[str, Any]])
async def get_backtest_results(
    strategy_name: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    current_user: dict = Depends(get_current_user),
):
    """Supabaseからバックテスト結果一覧を取得"""
    try:
        # バックテストエンジンを使用してSupabaseから結果を取得
        engine = BacktestEngine()
        results = await engine.list_backtest_results(strategy_name=strategy_name, limit=limit, offset=offset)

        return results

    except Exception as e:
        logger.error(f"Failed to get backtest results: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/results/{backtest_id}", response_model=Dict[str, Any])
async def get_backtest_result(backtest_id: str, current_user: dict = Depends(get_current_user)):
    """特定のバックテスト結果をSupabaseから取得"""
    try:
        # バックテストエンジンを使用してSupabaseから結果を取得
        engine = BacktestEngine()
        result = await engine.load_backtest_result(backtest_id)

        if not result:
            raise HTTPException(status_code=404, detail="Backtest result not found")

        # BacktestResultを辞書形式に変換
        return result.to_dict()

    except Exception as e:
        logger.error(f"Failed to get backtest result {backtest_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def _run_enhanced_backtest_task(backtest_request: BacktestRequest, username: str):
    """強化されたバックテストを実行するタスク（バックグラウンド処理）"""
    try:
        logger.info(f"Starting enhanced backtest for {backtest_request.strategy_name} by {username}")

        # ストラテジーローダーで戦略を取得
        strategy_loader = StrategyLoader()
        strategy = strategy_loader.load_strategy(backtest_request.strategy_name)

        if not strategy:
            raise Exception(f"Strategy {backtest_request.strategy_name} not found")

        # バックテストエンジンを初期化
        engine = BacktestEngine(
            initial_capital=backtest_request.initial_capital,
            commission=backtest_request.commission,
            slippage=backtest_request.slippage,
            exchange=backtest_request.exchange,
            use_real_data=backtest_request.use_real_data,
            data_quality_threshold=backtest_request.data_quality_threshold,
        )

        # 日付を datetime に変換
        start_date = datetime.combine(backtest_request.start_date, datetime.min.time())
        end_date = datetime.combine(backtest_request.end_date, datetime.min.time())

        # バックテストを実行
        result = await engine.run_backtest_with_real_data(
            strategy=strategy,
            symbol=backtest_request.symbol,
            timeframe=backtest_request.timeframe,
            start_date=start_date,
            end_date=end_date,
            strategy_name=backtest_request.strategy_name,
        )

        # 結果をSupabaseに保存
        backtest_id = await engine.save_results_to_database(result)

        logger.info(f"Enhanced backtest completed for {backtest_request.strategy_name}, ID: {backtest_id}")

        return backtest_id

    except Exception as e:
        logger.error(f"Enhanced backtest failed: {e}")
        raise


def _run_backtest_task(backtest_request: BacktestRequest, username: str):
    """従来のバックテストタスク（互換性のため保持）"""
    # 新しいタスクを非同期で実行
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(_run_enhanced_backtest_task(backtest_request, username))
        return result
    except Exception as e:
        logger.error(f"Backtest wrapper failed: {e}")
        raise
    finally:
        loop.close()
