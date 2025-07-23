"""
Supabase認証システム - APIRouter実装
統合Crypto Bot APIの認証機能モジュール
"""

import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional

import jwt
from fastapi import APIRouter, Cookie, Depends, HTTPException, Response
from pydantic import BaseModel, field_validator
from supabase import Client, create_client

# ログ設定
logger = logging.getLogger(__name__)

# 環境変数から設定を取得
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "prod-jwt-secret-key-vercel-crypto-trading-bot-32-chars-long")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_EXPIRATION_HOURS = int(os.getenv("JWT_EXPIRATION", "24"))

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY", "")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")

# APIRouterを作成
auth_router = APIRouter()


# リクエスト/レスポンスモデル
class LoginRequest(BaseModel):
    username: str
    password: str


class RegisterRequest(BaseModel):
    username: str
    email: str
    password: str

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        """カスタムEmailバリデーション"""
        import re

        pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        if not re.match(pattern, v):
            raise ValueError("有効なメールアドレスを入力してください")
        return v.lower().strip()

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        """パスワード強度チェック"""
        if len(v) < 8:
            raise ValueError("パスワードは8文字以上である必要があります")
        if not any(c.isupper() for c in v):
            raise ValueError("パスワードには大文字を含む必要があります")
        if not any(c.islower() for c in v):
            raise ValueError("パスワードには小文字を含む必要があります")
        if not any(c.isdigit() for c in v):
            raise ValueError("パスワードには数字を含む必要があります")
        return v


class AuthResponse(BaseModel):
    success: bool
    message: str
    user: Optional[Dict] = None
    access_token: Optional[str] = None


class UserProfileResponse(BaseModel):
    id: str
    username: str
    email: str
    created_at: str


# Supabaseクライアント管理
def get_supabase_client() -> Client:
    """Supabaseクライアントを取得"""
    if not SUPABASE_URL or not SUPABASE_ANON_KEY:
        raise HTTPException(
            status_code=500, detail="Supabase configuration missing. Please set SUPABASE_URL and SUPABASE_ANON_KEY"
        )
    return create_client(SUPABASE_URL, SUPABASE_ANON_KEY)


def get_supabase_admin_client() -> Client:
    """管理者権限のSupabaseクライアントを取得"""
    if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
        raise HTTPException(
            status_code=500, detail="Supabase admin configuration missing. Please set SUPABASE_SERVICE_ROLE_KEY"
        )
    return create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)


# JWT関連関数
def create_jwt_token(user_data: Dict) -> str:
    """JWTトークンを作成"""
    payload = {
        "sub": user_data["id"],
        "username": user_data.get("username", ""),
        "email": user_data.get("email", ""),
        "exp": datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS),
        "iat": datetime.utcnow(),
    }
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def verify_jwt_token(token: str) -> Dict:
    """JWTトークンを検証"""
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")


# 認証依存関数
async def get_current_user(access_token: Optional[str] = Cookie(None)) -> Dict:
    """現在のユーザーを取得（JWTトークンから）"""
    if not access_token:
        raise HTTPException(status_code=401, detail="Access token required")

    try:
        payload = verify_jwt_token(access_token)
        return payload
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"ユーザー認証エラー: {e}")
        raise HTTPException(status_code=401, detail="Authentication failed")


# ユーザー管理関数
def username_to_email(username: str) -> str:
    """ユーザー名をEmailに変換（Supabase Auth用）"""
    # demoユーザーは固定Email
    if username == "demo":
        return "demo@cryptobot.local"
    # その他のユーザーは username@cryptobot.local 形式
    return f"{username}@cryptobot.local"


def get_user_by_username(username: str) -> Optional[Dict]:
    """ユーザー名でプロファイルを検索"""
    try:
        admin_client = get_supabase_admin_client()
        response = admin_client.table("profiles").select("*").eq("username", username).execute()

        if response.data and len(response.data) > 0:
            return response.data[0]
        return None
    except Exception as e:
        logger.error(f"ユーザー検索エラー: {e}")
        return None


def ensure_demo_user():
    """デモユーザーの存在を確認・作成"""
    try:
        admin_client = get_supabase_admin_client()

        # 既存のdemoユーザーを検索
        existing_user = get_user_by_username("demo")
        if existing_user:
            logger.info("デモユーザーは既に存在します")
            return True

        # デモユーザーを作成（管理者権限が必要）
        demo_email = "demo@cryptobot.local"
        demo_password = "demo"

        # まず、auth.usersにユーザーを作成
        response = admin_client.auth.admin.create_user(
            {
                "email": demo_email,
                "password": demo_password,
                "email_confirm": True,  # 確認済みとして作成
            }
        )

        if response.user:
            # プロファイルテーブルにも作成
            profile_data = {
                "id": response.user.id,
                "username": "demo",
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
            admin_client.table("profiles").upsert(profile_data).execute()
            logger.info("デモユーザーを作成しました")
            return True

    except Exception as e:
        logger.error(f"デモユーザー作成エラー: {e}")
        return False

    return False


# 認証エンドポイント
@auth_router.post("/login", response_model=AuthResponse)
async def login(request: LoginRequest, response: Response):
    """ログイン処理（Supabase Auth使用）"""
    try:
        # ユーザー名をEmailに変換
        email = username_to_email(request.username)

        # Supabase認証を試行
        client = get_supabase_client()
        auth_response = client.auth.sign_in_with_password({"email": email, "password": request.password})

        if not auth_response.user:
            raise HTTPException(status_code=401, detail="Invalid username or password")

        # プロファイル情報を取得
        user_profile = get_user_by_username(request.username)
        if not user_profile:
            # プロファイルが存在しない場合は作成
            profile_data = {
                "id": auth_response.user.id,
                "username": request.username,
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
            admin_client = get_supabase_admin_client()
            admin_client.table("profiles").upsert(profile_data).execute()
            user_profile = profile_data

        # JWTトークンを作成
        user_data = {
            "id": auth_response.user.id,
            "username": user_profile["username"],
            "email": auth_response.user.email,
        }
        access_token = create_jwt_token(user_data)

        # httpOnlyクッキーに設定
        response.set_cookie(
            key="access_token",
            value=access_token,
            httponly=True,
            secure=os.getenv("ENVIRONMENT") == "production",
            samesite="strict",
            max_age=JWT_EXPIRATION_HOURS * 3600,
        )

        logger.info(f"ユーザー {request.username} がログインしました")

        return AuthResponse(success=True, message="Login successful", user=user_data, access_token=access_token)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"ログインエラー: {e}")
        raise HTTPException(status_code=500, detail="Login failed")


@auth_router.post("/register", response_model=AuthResponse)
async def register(request: RegisterRequest):
    """ユーザー登録処理（Supabase Auth使用）"""
    try:
        # ユーザー名の重複チェック
        existing_user = get_user_by_username(request.username)
        if existing_user:
            raise HTTPException(status_code=400, detail="Username already exists")

        # Supabaseでユーザーを作成
        client = get_supabase_client()
        auth_response = client.auth.sign_up({"email": request.email, "password": request.password})

        if not auth_response.user:
            raise HTTPException(status_code=400, detail="Registration failed")

        # プロファイルを作成
        profile_data = {
            "id": auth_response.user.id,
            "username": request.username,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        admin_client = get_supabase_admin_client()
        admin_client.table("profiles").upsert(profile_data).execute()

        logger.info(f"新規ユーザー {request.username} が登録されました")

        user_data = {"id": auth_response.user.id, "username": request.username, "email": request.email}

        return AuthResponse(success=True, message="Registration successful", user=user_data)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"登録エラー: {e}")
        raise HTTPException(status_code=500, detail="Registration failed")


@auth_router.post("/logout")
async def logout(response: Response):
    """ログアウト処理"""
    response.delete_cookie(key="access_token")
    return {"success": True, "message": "Logout successful"}


@auth_router.get("/me", response_model=UserProfileResponse)
async def get_current_user_info(current_user: Dict = Depends(get_current_user)):
    """現在のユーザー情報を取得"""
    try:
        # プロファイル情報を取得
        user_profile = get_user_by_username(current_user.get("username", ""))

        if not user_profile:
            raise HTTPException(status_code=404, detail="User profile not found")

        return UserProfileResponse(
            id=current_user["sub"],
            username=current_user["username"],
            email=current_user["email"],
            created_at=user_profile.get("created_at", ""),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"ユーザー情報取得エラー: {e}")
        raise HTTPException(status_code=500, detail="Failed to get user information")


@auth_router.get("/health")
async def auth_health_check():
    """認証システムのヘルスチェック"""
    try:
        # Supabase接続テスト
        client = get_supabase_client()
        client.table("profiles").select("id").limit(1).execute()
        supabase_status = "healthy"

        # デモユーザー確認
        demo_user_exists = get_user_by_username("demo") is not None

        return {
            "status": "healthy",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "version": "4.0.0",
            "supabase_connection": supabase_status,
            "demo_user_available": demo_user_exists,
            "configuration": {
                "jwt_configured": bool(JWT_SECRET_KEY),
                "supabase_url_configured": bool(SUPABASE_URL),
                "supabase_key_configured": bool(SUPABASE_ANON_KEY),
            },
        }

    except Exception as e:
        logger.error(f"認証ヘルスチェックエラー: {e}")
        return {
            "status": "unhealthy",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "version": "4.0.0",
            "error": str(e),
        }


# アプリケーション起動時にデモユーザーを確保
try:
    if SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY:
        ensure_demo_user()
        logger.info("デモユーザーの初期化完了")
    else:
        logger.warning("Supabase設定が不完全なため、デモユーザーの初期化をスキップ")
except Exception as e:
    logger.error(f"デモユーザー初期化エラー: {e}")
