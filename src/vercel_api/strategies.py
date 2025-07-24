"""
Vercel Serverless Function - Trading Strategies API
取引戦略専用の軽量API
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# 戦略機能のみ
from src.backend.api.strategies import router as strategies_router

app = FastAPI(title="Crypto Bot Strategies API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 戦略ルーターのみ
app.include_router(strategies_router, prefix="/strategies", tags=["strategies"])

# Vercel handler
handler = app
