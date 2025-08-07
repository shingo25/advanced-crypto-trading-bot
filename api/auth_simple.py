"""
Vercel Serverless Function - Simple Authentication API
DuckDBに依存しない軽量認証システム
"""

import hashlib
import os
import uuid
from datetime import datetime, timedelta
from typing import Dict, Optional

import jwt
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer
from pydantic import BaseModel

# 環境変数から設定を取得
JWT_SECRET = os.getenv("JWT_SECRET_KEY", "dev-jwt-secret-key-for-advanced-crypto-trading-bot-development-32-chars")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION = int(os.getenv("JWT_EXPIRATION", "86400"))  # 24時間

# 個人モード設定
PERSONAL_MODE = os.getenv("PERSONAL_MODE", "false").lower() == "true"
PERSONAL_MODE_AUTO_LOGIN = os.getenv("PERSONAL_MODE_AUTO_LOGIN", "false").lower() == "true"
PERSONAL_MODE_DEFAULT_USER = os.getenv("PERSONAL_MODE_DEFAULT_USER", "demo")
PERSONAL_MODE_SKIP_LIVE_TRADING_AUTH = os.getenv("PERSONAL_MODE_SKIP_LIVE_TRADING_AUTH", "false").lower() == "true"

app = FastAPI(title="Crypto Bot Simple Auth API", version="2.0.0")

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
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)

security = HTTPBearer()


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


# メモリベースの簡易ユーザーストレージ（実際にはRedisやSupabaseを使用）
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


@app.post("/api/auth/login", response_model=AuthResponse)
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


@app.post("/api/auth/register", response_model=AuthResponse)
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


@app.post("/api/auth/auto-login", response_model=AuthResponse)
async def auto_login(response: Response):
    """個人モード用自動ログイン"""
    try:
        # 個人モードが有効でない場合はエラー
        if not PERSONAL_MODE:
            raise HTTPException(status_code=403, detail="Personal mode not enabled")
        
        # デフォルトユーザーでのログイン
        user = get_user(PERSONAL_MODE_DEFAULT_USER)
        if not user:
            raise HTTPException(status_code=404, detail=f"Default user '{PERSONAL_MODE_DEFAULT_USER}' not found")

        # JWTトークン生成
        access_token = create_access_token(user)

        # httpOnlyクッキーに設定
        is_production = os.getenv("ENVIRONMENT") == "production"
        response.set_cookie(
            key="access_token",
            value=access_token,
            httponly=True,
            secure=is_production,
            samesite="lax",
            max_age=JWT_EXPIRATION,
        )

        return AuthResponse(
            success=True,
            message="Auto-login successful (Personal mode)",
            user={"id": user["id"], "username": user["username"], "email": user["email"], "role": user["role"]},
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Auto-login failed: {str(e)}")


@app.post("/api/auth/logout")
async def logout(response: Response):
    """ログアウト処理"""
    response.delete_cookie(key="access_token")
    return {"success": True, "message": "Logged out successfully"}


@app.get("/api/auth/me")
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


@app.get("/api/auth/personal-mode-info")
async def get_personal_mode_info():
    """個人モード設定情報を取得"""
    return {
        "personal_mode": PERSONAL_MODE,
        "auto_login": PERSONAL_MODE_AUTO_LOGIN,
        "default_user": PERSONAL_MODE_DEFAULT_USER,
        "skip_live_trading_auth": PERSONAL_MODE_SKIP_LIVE_TRADING_AUTH,
        "available_users": list(DEMO_USERS.keys()),
    }


@app.get("/api/auth/test")
async def test_endpoint():
    """Vercel環境テスト用エンドポイント"""
    return {"status": "ok", "message": "API is working"}


@app.get("/api/auth/health")
async def health_check():
    """ヘルスチェック"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "2.0.0",
        "environment": os.getenv("ENVIRONMENT", "unknown"),
        "demo_user_available": "demo" in DEMO_USERS,
        "personal_mode": PERSONAL_MODE,
        "endpoints": ["/api/auth/login", "/api/auth/register", "/api/auth/logout", "/api/auth/me", "/api/auth/auto-login", "/api/auth/personal-mode-info", "/api/auth/health", "/api/auth/test"],
    }


# Vercel handler
handler = app
