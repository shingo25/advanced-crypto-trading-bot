from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import date
from backend.core.security import get_current_user, require_admin
from backend.core.database import get_db
import json
import logging

router = APIRouter()
logger = logging.getLogger(__name__)


class BacktestRequest(BaseModel):
    strategy_id: int
    start_date: date
    end_date: date
    initial_capital: float = 10000.0
    config: Optional[Dict[str, Any]] = None


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


@router.post("/run", response_model=dict)
async def run_backtest(
    backtest_request: BacktestRequest,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(require_admin),
):
    """バックテストを実行"""
    db = get_db()
    # 戦略の存在確認
    strategy = db.fetchone(
        "SELECT id, name FROM strategies WHERE id = ?", [backtest_request.strategy_id]
    )
    if not strategy:
        raise HTTPException(status_code=404, detail="Strategy not found")

    # バックテストをバックグラウンドで実行
    background_tasks.add_task(
        _run_backtest_task, backtest_request, current_user["username"]
    )

    logger.info(
        f"Backtest queued for strategy {strategy[1]} by {current_user['username']}"
    )
    return {"status": "queued", "message": "Backtest started"}


@router.get("/results", response_model=List[BacktestResult])
async def get_backtest_results(
    strategy_id: Optional[int] = None, current_user: dict = Depends(get_current_user)
):
    """バックテスト結果を取得"""
    db = get_db()
    query = """
        SELECT id, strategy_id, start_date, end_date, initial_capital,
               final_capital, total_trades, win_rate, sharpe_ratio,
               max_drawdown, results
        FROM backtests
    """
    params = []

    if strategy_id:
        query += " WHERE strategy_id = ?"
        params.append(strategy_id)

    query += " ORDER BY created_at DESC"

    results = db.fetchall(query, params)
    return [
        BacktestResult(
            id=r[0],
            strategy_id=r[1],
            start_date=r[2],
            end_date=r[3],
            initial_capital=r[4],
            final_capital=r[5],
            total_trades=r[6],
            win_rate=r[7],
            sharpe_ratio=r[8],
            max_drawdown=r[9],
            results=json.loads(r[10]) if r[10] else {},
        )
        for r in results
    ]


@router.get("/results/{backtest_id}", response_model=BacktestResult)
async def get_backtest_result(
    backtest_id: int, current_user: dict = Depends(get_current_user)
):
    """特定のバックテスト結果を取得"""
    db = get_db()
    result = db.fetchone(
        """
        SELECT id, strategy_id, start_date, end_date, initial_capital,
               final_capital, total_trades, win_rate, sharpe_ratio,
               max_drawdown, results
        FROM backtests WHERE id = ?
        """,
        [backtest_id],
    )

    if not result:
        raise HTTPException(status_code=404, detail="Backtest result not found")

    return BacktestResult(
        id=result[0],
        strategy_id=result[1],
        start_date=result[2],
        end_date=result[3],
        initial_capital=result[4],
        final_capital=result[5],
        total_trades=result[6],
        win_rate=result[7],
        sharpe_ratio=result[8],
        max_drawdown=result[9],
        results=json.loads(result[10]) if result[10] else {},
    )


def _run_backtest_task(backtest_request: BacktestRequest, username: str):
    """バックテストを実行するタスク（バックグラウンド処理）"""
    try:
        db = get_db()
        # TODO: 実際のバックテストロジックを実装
        # 現在はダミーデータを返す

        # ダミー結果
        final_capital = backtest_request.initial_capital * 1.15  # 15% リターン
        total_trades = 42
        win_rate = 65.5
        sharpe_ratio = 1.23
        max_drawdown = 8.5

        results = {
            "returns": [0.01, 0.02, -0.01, 0.03, 0.01],
            "trades": [
                {"date": "2024-01-01", "symbol": "BTCUSDT", "side": "buy", "pnl": 100},
                {"date": "2024-01-02", "symbol": "BTCUSDT", "side": "sell", "pnl": 50},
            ],
            "metrics": {"profit_factor": 1.5, "total_return": 0.15, "volatility": 0.12},
        }

        # 結果をDBに保存
        db.execute(
            """
            INSERT INTO backtests (
                strategy_id, start_date, end_date, initial_capital,
                final_capital, total_trades, win_rate, sharpe_ratio,
                max_drawdown, results
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                backtest_request.strategy_id,
                backtest_request.start_date,
                backtest_request.end_date,
                backtest_request.initial_capital,
                final_capital,
                total_trades,
                win_rate,
                sharpe_ratio,
                max_drawdown,
                json.dumps(results),
            ],
        )

        logger.info(f"Backtest completed for strategy {backtest_request.strategy_id}")

    except Exception as e:
        logger.error(f"Backtest failed: {e}")
        raise
