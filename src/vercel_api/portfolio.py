"""
Vercel Serverless Function - Portfolio API
ポートフォリオ管理専用の軽量API
"""

import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# ポートフォリオ機能のみ
from backend.api.portfolio import router as portfolio_router

app = FastAPI(title="Crypto Bot Portfolio API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ポートフォリオルーターのみ
app.include_router(portfolio_router, prefix="/api/portfolio", tags=["portfolio"])

# Vercel handler
handler = app
