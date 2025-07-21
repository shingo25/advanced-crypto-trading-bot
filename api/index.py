"""
Vercel Serverless Function - Main API Entry Point
軽量版のメインAPIエンドポイント
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Crypto Bot API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Vercel用にシンプル化
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    return {"message": "Crypto Bot API is running", "version": "1.0.0"}


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "crypto-bot-api"}


# Vercel handler
handler = app
