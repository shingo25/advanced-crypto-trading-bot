"""
Vercel Serverless Function - Simple Health Check
軽量なヘルスチェック専用エンドポイント
"""

import os
from datetime import datetime, timezone

from fastapi import FastAPI

# 軽量なFastAPIアプリケーション
app = FastAPI(title="Health Check API", version="1.0.0")


@app.get("/")
async def health_check():
    """軽量ヘルスチェック"""
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": "4.0.0",
        "environment": os.getenv("ENVIRONMENT", "production"),
        "message": "Crypto Bot API - Health Check OK",
    }


# Vercel handler
handler = app
