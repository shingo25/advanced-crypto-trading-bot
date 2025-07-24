"""
Vercel Serverless Function - Market Data API
マーケットデータ専用の軽量API
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# マーケットデータ機能のみ
from src.backend.api.market_data import router as market_data_router

app = FastAPI(title="Crypto Bot Market Data API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# マーケットデータルーターのみ
app.include_router(market_data_router, prefix="/api/market-data", tags=["market-data"])

# Vercel handler
handler = app
