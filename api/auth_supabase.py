"""
Supabase認証を使用したVercel用認証API
完全にステートレス、永続的なデータストレージ対応
"""

import os
import logging
from datetime import datetime, timezone
from typing import Dict, Optional

from fastapi import FastAPI, HTTPException, Request, Response, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
# TEMP: デプロイテスト用にコメントアウト
# from supabase import create_client, Client

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 環境変数から設定を取得
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "prod-jwt-secret-key-vercel-crypto-trading-bot-32-chars-long")
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY", "")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")

app = FastAPI(title="Crypto Bot Supabase Auth API", version="3.0.0")

# CORS設定
allowed_origins = ["*"] if os.getenv("ENVIRONMENT") == "development" else [
    "https://*.vercel.app",
    "https://advanced-crypto-trading-bot.vercel.app"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
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

# Supabaseクライアント初期化
# TEMP: デプロイテスト用にコメントアウト
# def get_supabase_client() -> Client:
#     """Supabaseクライアントを取得"""
#     if not SUPABASE_URL or not SUPABASE_ANON_KEY:
#         raise HTTPException(
#             status_code=500, 
#             detail="Supabase configuration missing. Please set SUPABASE_URL and SUPABASE_ANON_KEY"
#         )
#     return create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

# def get_supabase_admin_client() -> Client:
#     """管理者権限のSupabaseクライアントを取得"""
#     if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
#         raise HTTPException(
#             status_code=500,
#             detail="Supabase admin configuration missing"
#         )
#     return create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

# ユーザー名->Emailマッピング関数
# TEMP: デプロイテスト用にコメントアウト
# def username_to_email(username: str) -> str:
#     """ユーザー名をEmailに変換（Supabase Auth用）"""
#     # demoユーザーは固定Email
#     if username == "demo":
#         return "demo@cryptobot.local"
#     # その他のユーザーは username@cryptobot.local 形式
#     return f"{username}@cryptobot.local"

# def get_user_by_username(username: str) -> Optional[Dict]:
#     """ユーザー名でプロファイルを検索"""
#     try:
#         admin_client = get_supabase_admin_client()
#         response = admin_client.table("profiles").select("*").eq("username", username).execute()
#         
#         if response.data and len(response.data) > 0:
#             return response.data[0]
#         return None
#     except Exception as e:
#         logger.error(f"ユーザー検索エラー: {e}")
#         return None

# def ensure_demo_user():
#     """デモユーザーの存在を確認・作成"""
#     try:
#         admin_client = get_supabase_admin_client()
#         
#         # 既存のdemoユーザーを検索
#         existing_user = get_user_by_username("demo")
#         if existing_user:
#             logger.info("デモユーザーは既に存在します")
#             return
#         
#         # デモユーザーを作成（管理者権限が必要）
#         demo_email = "demo@cryptobot.local"
#         demo_password = "demo"
#         
#         # まず、auth.usersにユーザーを作成
#         response = admin_client.auth.admin.create_user({
#             "email": demo_email,
#             "password": demo_password,
#             "email_confirm": True  # 確認済みとして作成
#         })
#         
#         if response.user:
#             # プロファイルテーブルにも作成（通常はトリガーで自動実行されるが、手動で確実に）
#             profile_data = {
#                 "id": response.user.id,
#                 "username": "demo",
#                 "created_at": datetime.now(timezone.utc).isoformat()
#             }
#             admin_client.table("profiles").upsert(profile_data).execute()
#             logger.info("デモユーザーを作成しました")
#         
#     except Exception as e:
#         logger.error(f"デモユーザー作成エラー: {e}")
#         # エラーが発生してもアプリケーションは継続

# アプリケーション起動時にデモユーザーを確保
# TEMP: デプロイテスト用に一時的にコメントアウト
# ensure_demo_user()

# TEMP: デプロイテスト用にコメントアウト - すべてのAPIエンドポイント
# 最小限の構成でデプロイテストを実施

# @app.post("/api/auth/login", response_model=AuthResponse)
# async def login(request: LoginRequest, response: Response):
#     """ログイン処理（Supabase Auth使用）"""
#     # [すべての実装をコメントアウト]

# @app.post("/api/auth/register", response_model=AuthResponse) 
# async def register(request: RegisterRequest):
#     """ユーザー登録処理（Supabase Auth使用）"""
#     # [すべての実装をコメントアウト]

# @app.post("/api/auth/logout")
# async def logout(response: Response):
#     """ログアウト処理"""
#     # [すべての実装をコメントアウト]

# @app.get("/api/auth/me")
# async def get_current_user(request: Request):
#     """現在のユーザー情報を取得"""
#     # [すべての実装をコメントアウト]

@app.get("/api/auth/health")
async def health_check():
    """ヘルスチェック（デプロイテスト用簡易版）"""
    try:
        # TEMP: デプロイテスト用にSupabase接続テストを無効化
        # client = get_supabase_client()
        # test_response = client.table("profiles").select("id").limit(1).execute()
        # supabase_status = "healthy" if test_response else "unhealthy"
        
        return {
            "status": "healthy",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "version": "3.0.0-deploy-test",
            "environment": os.getenv("ENVIRONMENT", "unknown"),
            "supabase_connection": "disabled-for-deploy-test",
            "demo_user_available": "disabled-for-deploy-test",
            "endpoints": [
                "/api/auth/login",
                "/api/auth/register", 
                "/api/auth/logout",
                "/api/auth/me",
                "/api/auth/health"
            ]
        }
    except Exception as e:
        logger.error(f"ヘルスチェックエラー: {e}")
        return {
            "status": "unhealthy",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "version": "3.0.0-deploy-test",
            "error": str(e)
        }

# Vercel handler
handler = app