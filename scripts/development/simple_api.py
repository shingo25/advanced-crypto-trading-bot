#!/usr/bin/env python3
"""
デモ用の簡単なAPIサーバー
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from datetime import datetime, timedelta
import random

app = FastAPI(title="Crypto Bot Demo API", version="1.0.0")

# CORS設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://192.168.150.102:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ダミーデータ
mock_trades = [
    {
        "id": 1,
        "symbol": "BTC/USDT",
        "side": "buy",
        "amount": 0.01,
        "price": 45000,
        "timestamp": datetime.now() - timedelta(hours=1),
        "status": "completed",
    },
    {
        "id": 2,
        "symbol": "ETH/USDT",
        "side": "sell",
        "amount": 0.5,
        "price": 3200,
        "timestamp": datetime.now() - timedelta(minutes=30),
        "status": "completed",
    },
]

mock_strategies = [
    {
        "id": 1,
        "name": "Moving Average",
        "description": "Simple moving average strategy",
        "is_active": True,
        "profit": 150.75,
    },
    {
        "id": 2,
        "name": "RSI Oscillator",
        "description": "RSI-based trading strategy",
        "is_active": False,
        "profit": -25.30,
    },
]


@app.get("/")
async def root():
    return {"message": "Crypto Bot Demo API", "status": "running"}


@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now()}


@app.post("/api/auth/login")
async def login(credentials: dict):
    # デモ用の簡単な認証
    if credentials.get("username") == "demo" and credentials.get("password") == "demo":
        return {
            "access_token": "demo_token_12345",
            "token_type": "bearer",
            "expires_in": 86400,
            "user": {"id": "1", "username": "demo", "email": "demo@example.com"},
        }
    raise HTTPException(status_code=401, detail="Invalid credentials")


@app.get("/api/auth/me")
async def get_current_user():
    return {"username": "demo", "id": 1, "email": "demo@example.com"}


@app.get("/api/trades")
async def get_trades():
    return {"trades": mock_trades, "total": len(mock_trades)}


@app.get("/api/strategies")
async def get_strategies():
    return {"strategies": mock_strategies, "total": len(mock_strategies)}


@app.get("/api/dashboard/stats")
async def get_dashboard_stats():
    return {
        "total_trades": len(mock_trades),
        "active_strategies": len([s for s in mock_strategies if s["is_active"]]),
        "total_profit": sum(s["profit"] for s in mock_strategies),
        "balance": 10000 + random.uniform(-500, 500),
    }


@app.get("/api/market/prices")
async def get_market_prices():
    # ランダムな価格データを生成
    return {
        "BTC/USDT": 45000 + random.uniform(-1000, 1000),
        "ETH/USDT": 3200 + random.uniform(-200, 200),
        "ADA/USDT": 0.45 + random.uniform(-0.05, 0.05),
        "DOT/USDT": 7.8 + random.uniform(-0.5, 0.5),
    }


if __name__ == "__main__":
    print("🚀 Crypto Bot Demo API サーバーを起動中...")
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
