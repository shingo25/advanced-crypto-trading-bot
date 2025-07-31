"""
Vercel Serverless Function - Trading Strategies API
取引戦略専用の軽量API
"""

import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 戦略機能のみ
from backend.api.strategies import router as strategies_router
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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
