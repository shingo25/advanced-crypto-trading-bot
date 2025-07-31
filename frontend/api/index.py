"""
個人用Crypto Bot API - Vercel対応認証統合版
個人利用向けアプリケーション with Simple Auth
"""

import hashlib
import logging
import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional

import jwt
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer
from mangum import Mangum
from pydantic import BaseModel

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 環境変数から設定を取得
JWT_SECRET = os.getenv("JWT_SECRET_KEY", "dev-jwt-secret-key-for-advanced-crypto-trading-bot-development-32-chars")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION = int(os.getenv("JWT_EXPIRATION", "86400"))  # 24時間

# FastAPIアプリケーション作成
app = FastAPI(title="Personal Crypto Bot API", version="5.1.0", description="個人用Crypto Bot API - 認証統合版")

security = HTTPBearer()

# 本番環境では適切なオリジンを指定
allowed_origins = (
    ["*"]
    if os.getenv("ENVIRONMENT") == "development"
    else ["https://*.vercel.app", "https://advanced-crypto-trading-bot.vercel.app"]
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["Content-Type", "Authorization", "X-Requested-With"],
)

# リクエスト/レスポンスモデル
class LoginRequest(BaseModel):
    username: str
    password: str

class RegisterRequest(BaseModel):
    username: str
    email: str
    password: str

class AuthResponse(BaseModel):
    success: bool
    message: str
    user: Optional[Dict] = None

# デモ用のハードコードされたユーザー
DEMO_USERS = {
    "demo": {
        "id": "demo-user-id",
        "username": "demo",
        "email": "demo@example.com",
        "password_hash": hashlib.pbkdf2_hmac("sha256", "demo".encode(), b"salt", 100000).hex(),
        "role": "viewer",
        "created_at": datetime.now().isoformat(),
    }
}

# 動的ユーザー登録用ストレージ（実際の実装ではデータベースを使用）
REGISTERED_USERS = {}

def hash_password(password: str) -> str:
    """パスワードをハッシュ化"""
    return hashlib.pbkdf2_hmac("sha256", password.encode(), b"salt", 100000).hex()

def verify_password(password: str, hashed: str) -> bool:
    """パスワードを検証"""
    return hash_password(password) == hashed

def get_user(username: str) -> Optional[Dict]:
    """ユーザーを取得"""
    if username in DEMO_USERS:
        return DEMO_USERS[username]
    if username in REGISTERED_USERS:
        return REGISTERED_USERS[username]
    return None

def create_access_token(user_data: Dict) -> str:
    """JWTアクセストークンを作成"""
    payload = {
        "sub": user_data["username"],
        "user_id": user_data["id"],
        "role": user_data["role"],
        "exp": datetime.utcnow() + timedelta(seconds=JWT_EXPIRATION),
        "iat": datetime.utcnow(),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

# ベーシックエンドポイント
@app.get("/")
async def root():
    """ルートエンドポイント"""
    return {
        "message": "Personal Crypto Bot API v5.1.0 - 認証統合版",
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "description": "個人用暗号通貨トレーディングボットAPI",
        "features": ["認証システム", "価格取得", "取引履歴", "ポートフォリオ管理", "バックテスト"],
        "version": "5.1.0",
    }

@app.get("/health")
async def health_check():
    """シンプルヘルスチェック"""
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": "5.1.0",
        "environment": os.getenv("ENVIRONMENT", "production"),
        "uptime": "ready",
        "demo_user_available": "demo" in DEMO_USERS,
    }

# 認証エンドポイント
@app.post("/auth/login", response_model=AuthResponse)
async def login(request: LoginRequest, response: Response):
    """ログイン処理"""
    try:
        # ユーザー検証
        user = get_user(request.username)
        if not user or not verify_password(request.password, user["password_hash"]):
            raise HTTPException(status_code=401, detail="Invalid username or password")

        # JWTトークン生成
        access_token = create_access_token(user)

        # httpOnlyクッキーに設定（環境に応じてsecure設定を調整）
        is_production = os.getenv("ENVIRONMENT") == "production"
        response.set_cookie(
            key="access_token",
            value=access_token,
            httponly=True,
            secure=is_production,  # 本番環境のみHTTPS必須
            samesite="lax",
            max_age=JWT_EXPIRATION,
        )

        return AuthResponse(
            success=True,
            message="Login successful",
            user={"id": user["id"], "username": user["username"], "email": user["email"], "role": user["role"]},
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Login failed: {str(e)}")

@app.post("/auth/register", response_model=AuthResponse)
async def register(request: RegisterRequest):
    """ユーザー登録処理"""
    try:
        # 重複チェック
        if get_user(request.username):
            raise HTTPException(status_code=400, detail="Username already exists")

        # 新規ユーザー作成
        user_id = str(uuid.uuid4())
        new_user = {
            "id": user_id,
            "username": request.username,
            "email": request.email,
            "password_hash": hash_password(request.password),
            "role": "viewer",
            "created_at": datetime.now().isoformat(),
        }

        # メモリストレージに保存（本番では永続化データベースを使用）
        REGISTERED_USERS[request.username] = new_user

        return AuthResponse(
            success=True,
            message="User registered successfully",
            user={
                "id": new_user["id"],
                "username": new_user["username"],
                "email": new_user["email"],
                "role": new_user["role"],
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Registration failed: {str(e)}")

@app.post("/auth/logout")
async def logout(response: Response):
    """ログアウト処理"""
    response.delete_cookie(key="access_token")
    return {"success": True, "message": "Logged out successfully"}

@app.get("/auth/me")
async def get_current_user(request: Request):
    """現在のユーザー情報を取得"""
    try:
        # クッキーからトークンを取得
        token = request.cookies.get("access_token")
        if not token:
            raise HTTPException(status_code=401, detail="Not authenticated")

        # JWTトークンをデコード
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        username = payload.get("sub")

        user = get_user(username)
        if not user:
            raise HTTPException(status_code=401, detail="User not found")

        return {"id": user["id"], "username": user["username"], "email": user["email"], "role": user["role"]}

    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# データ取得エンドポイント
@app.get("/prices")
async def get_crypto_prices():
    """暗号通貨価格取得（モックデータ）"""
    return {
        "prices": {
            "BTC": {"price": 43250.50, "change_24h": 2.45},
            "ETH": {"price": 2680.75, "change_24h": -1.23},
            "ADA": {"price": 0.58, "change_24h": 3.67},
            "DOT": {"price": 7.42, "change_24h": -0.89},
        },
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "source": "mock_data",
    }

@app.get("/portfolio")
async def get_portfolio():
    """ポートフォリオ情報取得（モックデータ）"""
    return {
        "total_value": 25847.30,
        "holdings": [
            {"symbol": "BTC", "amount": 0.5, "value": 21625.25},
            {"symbol": "ETH", "amount": 1.2, "value": 3216.90},
            {"symbol": "ADA", "amount": 1000, "value": 580.00},
            {"symbol": "DOT", "amount": 60, "value": 445.20},
        ],
        "change_24h": 1.34,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

@app.get("/trades")
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
                "timestamp": "2025-07-23T10:30:00Z",
            },
            {
                "id": 2,
                "symbol": "ETH",
                "type": "sell",
                "amount": 0.5,
                "price": 2700.00,
                "timestamp": "2025-07-23T14:15:00Z",
            },
        ],
        "total_trades": 2,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

# Vercel handler - Mangumを使用
handler = Mangum(app)