#!/usr/bin/env python3
"""
簡単なテストサーバー - 暗号通貨取引ボットのコア機能をテスト
"""

import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from datetime import datetime
from typing import Dict, List

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel


# Basic models
class HealthResponse(BaseModel):
    status: str
    timestamp: str
    version: str


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str
    user: dict


class StrategyInfo(BaseModel):
    id: str
    name: str
    description: str
    parameters: Dict
    status: str


class PortfolioSummary(BaseModel):
    total_value: float
    daily_pnl: float
    daily_pnl_pct: float
    total_pnl: float
    active_strategies: int
    unread_alerts: int
    open_positions: int
    active_orders: int
    portfolio: Dict
    recent_trades: List[Dict]


# Create FastAPI app
app = FastAPI(
    title="Crypto Trading Bot API",
    description="高度な暗号通貨取引ボットシステム",
    version="1.0.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mock data
MOCK_STRATEGIES = [
    {
        "id": "ema_strategy",
        "name": "EMA Strategy",
        "description": "指数移動平均を使用したトレンドフォロー戦略",
        "parameters": {
            "ema_fast": 12,
            "ema_slow": 26,
            "volume_threshold": 0.8,
            "trend_confirmation": True,
        },
        "status": "active",
    },
    {
        "id": "rsi_strategy",
        "name": "RSI Strategy",
        "description": "相対強度指数による逆張り戦略",
        "parameters": {
            "rsi_period": 14,
            "oversold_threshold": 30,
            "overbought_threshold": 70,
        },
        "status": "inactive",
    },
    {
        "id": "macd_strategy",
        "name": "MACD Strategy",
        "description": "MACD線とシグナル線のクロス戦略",
        "parameters": {"fast_period": 12, "slow_period": 26, "signal_period": 9},
        "status": "active",
    },
]

MOCK_PORTFOLIO = {
    "total_value": 10000.0,
    "daily_pnl": 250.0,
    "daily_pnl_pct": 0.025,
    "total_pnl": 1500.0,
    "active_strategies": 3,
    "unread_alerts": 2,
    "open_positions": 5,
    "active_orders": 2,
    "portfolio": {
        "assets": {
            "BTCUSDT": {
                "balance": 0.25,
                "market_value": 12500.0,
                "actual_weight": 0.6,
                "target_weight": 0.5,
            },
            "ETHUSDT": {
                "balance": 2.5,
                "market_value": 6250.0,
                "actual_weight": 0.3,
                "target_weight": 0.3,
            },
            "ADAUSDT": {
                "balance": 5000.0,
                "market_value": 2500.0,
                "actual_weight": 0.1,
                "target_weight": 0.2,
            },
        }
    },
    "recent_trades": [
        {
            "symbol": "BTCUSDT",
            "side": "buy",
            "amount": 0.1,
            "price": 50000.0,
            "pnl": 100.0,
            "timestamp": "2023-01-01T10:00:00Z",
        },
        {
            "symbol": "ETHUSDT",
            "side": "sell",
            "amount": 1.0,
            "price": 2500.0,
            "pnl": 50.0,
            "timestamp": "2023-01-01T09:30:00Z",
        },
        {
            "symbol": "ADAUSDT",
            "side": "buy",
            "amount": 1000.0,
            "price": 0.5,
            "pnl": -25.0,
            "timestamp": "2023-01-01T09:00:00Z",
        },
    ],
}


# Routes
@app.get("/health", response_model=HealthResponse)
async def health_check():
    """ヘルスチェック"""
    return HealthResponse(status="healthy", timestamp=datetime.now().isoformat(), version="1.0.0")


@app.post("/api/auth/login", response_model=LoginResponse)
async def login(request: LoginRequest):
    """ログイン"""
    if request.username == "admin" and request.password == "password":
        return LoginResponse(
            access_token="mock_jwt_token",
            token_type="bearer",
            user={"username": "admin", "role": "admin"},
        )
    raise HTTPException(status_code=401, detail="Invalid credentials")


@app.get("/api/strategies", response_model=List[StrategyInfo])
async def get_strategies():
    """戦略一覧取得"""
    return [StrategyInfo(**strategy) for strategy in MOCK_STRATEGIES]


@app.get("/api/portfolio/summary", response_model=PortfolioSummary)
async def get_portfolio_summary():
    """ポートフォリオ概要取得"""
    return PortfolioSummary(**MOCK_PORTFOLIO)


@app.post("/api/strategies/{strategy_id}/start")
async def start_strategy(strategy_id: str):
    """戦略開始"""
    strategy = next((s for s in MOCK_STRATEGIES if s["id"] == strategy_id), None)
    if not strategy:
        raise HTTPException(status_code=404, detail="Strategy not found")

    strategy["status"] = "active"
    return {"message": f"Strategy {strategy_id} started", "status": "success"}


@app.post("/api/strategies/{strategy_id}/stop")
async def stop_strategy(strategy_id: str):
    """戦略停止"""
    strategy = next((s for s in MOCK_STRATEGIES if s["id"] == strategy_id), None)
    if not strategy:
        raise HTTPException(status_code=404, detail="Strategy not found")

    strategy["status"] = "inactive"
    return {"message": f"Strategy {strategy_id} stopped", "status": "success"}


@app.get("/api/alerts")
async def get_alerts():
    """アラート一覧取得"""
    return [
        {
            "id": "alert_1",
            "type": "info",
            "message": "EMA戦略がBTCUSDTで買いシグナルを検出しました",
            "timestamp": "2023-01-01T10:00:00Z",
            "read": False,
        },
        {
            "id": "alert_2",
            "type": "warning",
            "message": "ポートフォリオの日次損失が2%を超えました",
            "timestamp": "2023-01-01T09:30:00Z",
            "read": False,
        },
    ]


@app.get("/")
async def root():
    """ルートエンドポイント"""
    return {
        "message": "🚀 Advanced Crypto Trading Bot API",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "health": "/health",
            "docs": "/docs",
            "strategies": "/api/strategies",
            "portfolio": "/api/portfolio/summary",
            "alerts": "/api/alerts",
        },
    }


if __name__ == "__main__":
    print("🚀 Starting Crypto Trading Bot Test Server...")
    print("📊 Mock data loaded:")
    print(f"  - {len(MOCK_STRATEGIES)} strategies")
    print(f"  - Portfolio value: ${MOCK_PORTFOLIO['total_value']:,.2f}")
    print("🌐 Server will be available at:")
    print("  - API: http://localhost:8000")
    print("  - Docs: http://localhost:8000/docs")
    print("  - Health: http://localhost:8000/health")
    print("👤 Test login: admin / password")

    uvicorn.run(app, host="0.0.0.0", port=8001, log_level="info")
