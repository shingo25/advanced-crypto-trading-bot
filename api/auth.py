"""
Vercel Serverless Function - Authentication API
認証専用の軽量API
"""

import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# 軽量な認証機能のみ
from backend.api.auth import router as auth_router

app = FastAPI(title="Crypto Bot Auth API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 認証ルーターのみ
app.include_router(auth_router, prefix="/auth", tags=["auth"])

# Vercel handler
handler = app
