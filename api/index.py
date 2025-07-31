"""
個人用Crypto Bot API - Vercel対応統合版
個人利用向けシンプル認証 + データ管理統合アプリケーション
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
from pydantic import BaseModel

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 環境変数から設定を取得
JWT_SECRET = os.getenv("JWT_SECRET_KEY", "prod-jwt-secret-key-vercel-crypto-trading-bot-32-chars-long")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION = int(os.getenv("JWT_EXPIRATION", "86400"))  # 24時間

# FastAPIアプリケーション作成
app = FastAPI(title="Personal Crypto Bot API", version="6.0.0", description="個人用Crypto Bot API - 統合認証・データ管理版")

# CORS設定 - Vercel環境対応
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

# デモ用のハードコードされたユーザー（個人利用向け）
DEMO_USERS = {
    "demo": {
        "id": "demo-user-id",
        "username": "demo",
        "email": "demo@example.com",
        "password_hash": hashlib.pbkdf2_hmac("sha256", "demo".encode(), b"salt", 100000).hex(),
        "role": "admin",
        "created_at": datetime.now().isoformat(),
    }
}

# 動的ユーザー登録用ストレージ（個人利用では簡易メモリストレージ）
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
        "message": "Personal Crypto Bot API v6.0.0 - 統合認証・データ管理版",
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "description": "個人用暗号通貨トレーディングボットAPI - 統合版",
        "features": ["認証システム", "価格取得", "取引履歴", "ポートフォリオ管理", "バックテスト", "auto-login"],
        "version": "6.0.0",
        "demo_user": "demo/demo",
    }

@app.get("/health")
async def health_check():
    """詳細ヘルスチェック"""
    try:
        jwt_secret = os.getenv("JWT_SECRET_KEY", "")
        
        health_status = {
            "status": "healthy",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "version": "6.0.0",
            "environment": os.getenv("ENVIRONMENT", "production"),
            "configuration": {
                "jwt_configured": bool(jwt_secret),
            },
            "endpoints": ["/auth/login", "/auth/register", "/auth/logout", "/auth/me", "/prices", "/portfolio", "/trades"],
            "demo_user_available": "demo" in DEMO_USERS,
            "registered_users_count": len(REGISTERED_USERS),
        }

        # 設定不備の警告  
        if not jwt_secret:
            health_status["warnings"] = ["JWT_SECRET_KEY not configured - using default"]

        return health_status

    except Exception as e:
        logger.error(f"ヘルスチェックエラー: {e}")
        return {
            "status": "unhealthy",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "version": "6.0.0",
            "error": str(e),
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

        logger.info(f"ユーザー {request.username} がログインしました")
        return AuthResponse(
            success=True,
            message="Login successful",
            user={"id": user["id"], "username": user["username"], "email": user["email"], "role": user["role"]},
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"ログインエラー: {e}")
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
            "role": "user",
            "created_at": datetime.now().isoformat(),
        }

        # メモリストレージに保存（個人利用向け簡易実装）
        REGISTERED_USERS[request.username] = new_user

        logger.info(f"新規ユーザー {request.username} が登録されました")
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
        logger.error(f"登録エラー: {e}")
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
        logger.error(f"認証エラー: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# データ取得エンドポイント（モックデータ）
@app.get("/prices")
async def get_crypto_prices():
    """暗号通貨価格取得（モックデータ）"""
    return {
        "prices": {
            "BTC": {"price": 43250.50, "change_24h": 2.45, "volume_24h": 28450000000},
            "ETH": {"price": 2680.75, "change_24h": -1.23, "volume_24h": 12850000000},
            "ADA": {"price": 0.58, "change_24h": 3.67, "volume_24h": 890000000},
            "DOT": {"price": 7.42, "change_24h": -0.89, "volume_24h": 450000000},
            "LINK": {"price": 15.23, "change_24h": 1.75, "volume_24h": 670000000},
        },
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "source": "mock_data",
        "market_cap_total": 1847500000000,
    }

@app.get("/portfolio")
async def get_portfolio():
    """ポートフォリオ情報取得（モックデータ）"""
    return {
        "total_value": 25847.30,
        "total_pnl": 2847.30,
        "total_pnl_percent": 12.34,
        "holdings": [
            {"symbol": "BTC", "amount": 0.5, "value": 21625.25, "pnl": 1825.25, "pnl_percent": 9.2},
            {"symbol": "ETH", "amount": 1.2, "value": 3216.90, "pnl": 416.90, "pnl_percent": 14.9},
            {"symbol": "ADA", "amount": 1000, "value": 580.00, "pnl": 80.00, "pnl_percent": 16.0},
            {"symbol": "DOT", "amount": 60, "value": 445.20, "pnl": 45.20, "pnl_percent": 11.3},
            {"symbol": "LINK", "amount": 30, "value": 456.90, "pnl": 56.90, "pnl_percent": 14.2},
        ],
        "change_24h": 1.34,
        "last_updated": datetime.now(timezone.utc).isoformat(),
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
                "total": 4250.00,
                "fee": 12.75,
                "timestamp": "2025-07-29T10:30:00Z",
                "status": "completed",
            },
            {
                "id": 2,
                "symbol": "ETH",
                "type": "sell",
                "amount": 0.5,
                "price": 2700.00,
                "total": 1350.00,
                "fee": 4.05,
                "timestamp": "2025-07-29T14:15:00Z",
                "status": "completed",
            },
            {
                "id": 3,
                "symbol": "ADA",
                "type": "buy",
                "amount": 500,
                "price": 0.56,
                "total": 280.00,
                "fee": 0.84,
                "timestamp": "2025-07-30T09:45:00Z",
                "status": "completed",
            },
        ],
        "total_trades": 3,
        "total_volume": 5880.00,
        "total_fees": 17.64,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

@app.get("/trading-settings")
async def get_trading_settings():
    """取引設定取得（モックデータ）"""
    return {
        "mode": "paper",  # paper | live
        "auto_trading": False,
        "risk_level": "medium",  # low | medium | high
        "max_position_size": 1000.00,
        "stop_loss_percent": 5.0,
        "take_profit_percent": 15.0,
        "trading_pairs": ["BTC/USDT", "ETH/USDT", "ADA/USDT"],
        "last_updated": datetime.now(timezone.utc).isoformat(),
    }

@app.post("/trading-settings")
async def update_trading_settings(settings: dict):
    """取引設定更新（モック実装）"""
    return {
        "success": True,
        "message": "Trading settings updated successfully",
        "settings": settings,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

# Vercel handler
handler = app
