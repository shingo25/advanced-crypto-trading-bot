"""
統合Crypto Bot API - Vercel対応メインアプリケーション
すべての認証・API機能を統合したFastAPIアプリケーション
"""

import logging
import os
from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# FastAPIアプリケーション作成
app = FastAPI(title="Crypto Bot API", version="4.0.0", description="統合Crypto Bot API - 認証・取引・データ管理")

# CORS設定 - Vercel環境対応
allowed_origins = (
    ["*"]
    if os.getenv("ENVIRONMENT") == "development"
    else [
        "https://*.vercel.app",
        "https://advanced-crypto-trading-bot.vercel.app",
        "https://crypto-bot-frontend.vercel.app",
    ]
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["Content-Type", "Authorization", "X-Requested-With"],
)

# 個人モード対応認証エンドポイントを直接追加（Vercel Functions対応）
try:
    # 最小限の動作確認エンドポイント
    @app.get("/api/auth/ping")
    async def auth_ping():
        """最小限の動作確認 - Vercel対応"""
        return {"status": "ok", "message": "pong", "source": "index.py"}
    
    # 個人モード情報エンドポイント
    @app.get("/api/auth/personal-mode-info")
    async def auth_personal_mode_info():
        """個人モード設定情報を取得"""
        import os
        return {
            "personal_mode": os.getenv("PERSONAL_MODE", "false").lower() == "true",
            "auto_login": os.getenv("PERSONAL_MODE_AUTO_LOGIN", "false").lower() == "true",
            "default_user": os.getenv("PERSONAL_MODE_DEFAULT_USER", "demo"),
            "environment_debug": {
                "PERSONAL_MODE_RAW": os.getenv("PERSONAL_MODE", "not_set"),
                "PERSONAL_MODE_AUTO_LOGIN_RAW": os.getenv("PERSONAL_MODE_AUTO_LOGIN", "not_set"),
                "ENVIRONMENT": os.getenv("ENVIRONMENT", "not_set"),
                "VERCEL": os.getenv("VERCEL", "not_set"),
            }
        }
    
    logger.info("個人モード認証エンドポイント直接統合完了")
    
except Exception as e:
    logger.error(f"個人モード認証エンドポイント統合失敗: {e}")


# ヘルスチェック（基本機能）
@app.get("/")
async def root():
    """ルートエンドポイント"""
    return {
        "message": "Crypto Bot API v4.0.0 - 統合認証システム",
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "features": ["Supabase認証", "デモユーザー(demo/demo)", "新規アカウント作成", "JWT認証"],
    }


@app.get("/api/health")
async def health_check():
    """詳細ヘルスチェック"""
    try:
        # 環境変数チェック
        jwt_secret = os.getenv("JWT_SECRET_KEY", "")
        supabase_url = os.getenv("SUPABASE_URL", "")
        supabase_key = os.getenv("SUPABASE_ANON_KEY", "")

        health_status = {
            "status": "healthy",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "version": "4.0.0",
            "environment": os.getenv("ENVIRONMENT", "unknown"),
            "configuration": {
                "jwt_configured": bool(jwt_secret),
                "supabase_url_configured": bool(supabase_url),
                "supabase_key_configured": bool(supabase_key),
            },
            "endpoints": ["/api/auth/login", "/api/auth/register", "/api/auth/logout", "/api/auth/me", "/api/health"],
        }

        # 設定不備の警告
        if not all([jwt_secret, supabase_url, supabase_key]):
            health_status["warnings"] = []
            if not jwt_secret:
                health_status["warnings"].append("JWT_SECRET_KEY not configured")
            if not supabase_url:
                health_status["warnings"].append("SUPABASE_URL not configured")
            if not supabase_key:
                health_status["warnings"].append("SUPABASE_ANON_KEY not configured")

        return health_status

    except Exception as e:
        logger.error(f"ヘルスチェックエラー: {e}")
        return {
            "status": "unhealthy",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "version": "4.0.0",
            "error": str(e),
        }


# Vercel handler
handler = app
