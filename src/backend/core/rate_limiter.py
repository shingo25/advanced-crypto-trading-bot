"""
レート制限機能
DoS攻撃やAPIの悪用を防ぐためのレート制限を実装
"""

import logging
from typing import Dict, Optional
from datetime import datetime, timedelta

from fastapi import FastAPI, Request, HTTPException
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from .config import settings

logger = logging.getLogger(__name__)


def get_client_ip(request: Request) -> str:
    """
    クライアントIPアドレスを取得
    プロキシやロードバランサー経由での正確なIP取得
    """
    # X-Forwarded-For ヘッダーをチェック（プロキシ経由の場合）
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # 最初のIPアドレスを使用（オリジナルクライアント）
        return forwarded_for.split(",")[0].strip()
    
    # X-Real-IP ヘッダーをチェック
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip
    
    # 通常のリモートアドレス
    return get_remote_address(request)


def get_user_id_or_ip(request: Request) -> str:
    """
    認証されたユーザーIDまたはIPアドレスを取得
    認証済みユーザーはユーザーID、未認証はIPアドレスでレート制限
    """
    # リクエストからユーザー情報を取得を試行
    try:
        # Authorizationヘッダーやセッションからユーザーを特定
        # 実装は認証システムに依存
        user = getattr(request.state, 'user', None)
        if user and hasattr(user, 'id'):
            return f"user:{user.id}"
    except Exception:
        pass
    
    # 認証されていない場合はIPアドレスを使用
    return f"ip:{get_client_ip(request)}"


# レート制限インスタンス作成
limiter = Limiter(
    key_func=get_user_id_or_ip,
    default_limits=[f"{settings.RATE_LIMIT_PER_MINUTE}/minute"]
)


class EnhancedRateLimiter:
    """
    拡張レート制限クラス
    より細かい制御とログ機能を提供
    """
    
    def __init__(self):
        self.failed_attempts: Dict[str, int] = {}
        self.lockout_until: Dict[str, datetime] = {}
    
    def is_locked_out(self, client_id: str) -> bool:
        """
        クライアントがロックアウト中かチェック
        """
        if client_id in self.lockout_until:
            if datetime.now() < self.lockout_until[client_id]:
                return True
            else:
                # ロックアウト期間終了、リセット
                del self.lockout_until[client_id]
                self.failed_attempts.pop(client_id, None)
        return False
    
    def record_failed_attempt(self, client_id: str):
        """
        失敗した試行を記録
        """
        self.failed_attempts[client_id] = self.failed_attempts.get(client_id, 0) + 1
        
        if self.failed_attempts[client_id] >= settings.MAX_LOGIN_ATTEMPTS:
            # ロックアウト適用
            lockout_until = datetime.now() + timedelta(minutes=settings.LOCKOUT_DURATION_MINUTES)
            self.lockout_until[client_id] = lockout_until
            
            logger.warning(
                f"Client {client_id} locked out until {lockout_until} "
                f"after {self.failed_attempts[client_id]} failed attempts"
            )
    
    def record_successful_attempt(self, client_id: str):
        """
        成功した試行を記録（失敗カウンターをリセット）
        """
        self.failed_attempts.pop(client_id, None)
    
    def check_and_record_attempt(self, client_id: str, success: bool):
        """
        試行をチェックして記録
        """
        if self.is_locked_out(client_id):
            raise HTTPException(
                status_code=429,
                detail=f"Too many failed attempts. Locked out until {self.lockout_until[client_id]}"
            )
        
        if success:
            self.record_successful_attempt(client_id)
        else:
            self.record_failed_attempt(client_id)


# グローバルインスタンス
enhanced_limiter = EnhancedRateLimiter()


def setup_rate_limiting(app: FastAPI) -> None:
    """
    FastAPIアプリケーションにレート制限を設定
    """
    # Slowapiの設定
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    
    logger.info("Rate limiting configured")
    logger.info(f"Default limit: {settings.RATE_LIMIT_PER_MINUTE}/minute")
    logger.info(f"Login limit: {settings.RATE_LIMIT_LOGIN_PER_MINUTE}/minute")
    logger.info(f"Order limit: {settings.RATE_LIMIT_ORDER_PER_MINUTE}/minute")


def get_rate_limit_status(client_id: str) -> Dict:
    """
    クライアントのレート制限状況を取得
    """
    return {
        "client_id": client_id,
        "failed_attempts": enhanced_limiter.failed_attempts.get(client_id, 0),
        "is_locked_out": enhanced_limiter.is_locked_out(client_id),
        "lockout_until": enhanced_limiter.lockout_until.get(client_id),
        "max_attempts": settings.MAX_LOGIN_ATTEMPTS,
        "lockout_duration_minutes": settings.LOCKOUT_DURATION_MINUTES
    }


# レート制限デコレータ
def rate_limit(limit: str):
    """
    カスタムレート制限デコレータ
    使用例: @rate_limit("5/minute")
    """
    return limiter.limit(limit)


# 特定エンドポイント用のレート制限関数
def login_rate_limit():
    """ログインエンドポイント用レート制限"""
    return rate_limit(f"{settings.RATE_LIMIT_LOGIN_PER_MINUTE}/minute")


def order_rate_limit():
    """注文エンドポイント用レート制限"""
    return rate_limit(f"{settings.RATE_LIMIT_ORDER_PER_MINUTE}/minute")


def api_rate_limit():
    """一般API用レート制限"""
    return rate_limit(f"{settings.RATE_LIMIT_API_PER_SECOND}/second")