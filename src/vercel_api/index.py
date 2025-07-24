"""
個人用Crypto Bot API - Vercel対応シンプル版
認証機能なしの個人利用向けアプリケーション
"""

import logging
import os
from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from mangum import Mangum

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# FastAPIアプリケーション作成
app = FastAPI(title="Personal Crypto Bot API", version="5.0.0", description="個人用Crypto Bot API - シンプル版")


# CORS設定 - 全オリジン許可（個人利用のため）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["Content-Type", "X-Requested-With"],
)


# ベーシックエンドポイント
@app.get("/api")
async def root():
    """ルートエンドポイント"""
    return {
        "message": "Personal Crypto Bot API v5.0.0 - シンプル版",
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "description": "個人用暗号通貨トレーディングボットAPI",
        "features": ["価格取得", "取引履歴", "ポートフォリオ管理", "バックテスト"],
        "version": "5.0.0"
    }


@app.get("/api/health")
async def health_check():
    """シンプルヘルスチェック"""
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": "5.0.0",
        "environment": os.getenv("ENVIRONMENT", "production"),
        "uptime": "ready"
    }


# 暗号通貨価格取得API（モック）
@app.get("/api/prices")
async def get_crypto_prices():
    """暗号通貨価格取得（モックデータ）"""
    return {
        "prices": {
            "BTC": {"price": 43250.50, "change_24h": 2.45},
            "ETH": {"price": 2680.75, "change_24h": -1.23},
            "ADA": {"price": 0.58, "change_24h": 3.67},
            "DOT": {"price": 7.42, "change_24h": -0.89}
        },
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "source": "mock_data"
    }


# ポートフォリオ情報API（モック）
@app.get("/api/portfolio")
async def get_portfolio():
    """ポートフォリオ情報取得（モックデータ）"""
    return {
        "total_value": 25847.30,
        "holdings": [
            {"symbol": "BTC", "amount": 0.5, "value": 21625.25},
            {"symbol": "ETH", "amount": 1.2, "value": 3216.90},
            {"symbol": "ADA", "amount": 1000, "value": 580.00},
            {"symbol": "DOT", "amount": 60, "value": 445.20}
        ],
        "change_24h": 1.34,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


# 取引履歴API（モック）
@app.get("/api/trades")
async def get_trades():
    """取引履歴取得（モックデータ）"""
    return {
        "trades": [
            {
                "id": 1,
                "symbol": "BTC",
                "type": "buy",
                "amount": 0.1,
                "price": 42500.00,
                "timestamp": "2025-07-23T10:30:00Z"
            },
            {
                "id": 2,
                "symbol": "ETH",
                "type": "sell",
                "amount": 0.5,
                "price": 2700.00,
                "timestamp": "2025-07-23T14:15:00Z"
            }
        ],
        "total_trades": 2,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


# Vercel handler - Mangumを使用
handler = Mangum(app)
