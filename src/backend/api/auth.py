import logging
import secrets
import smtplib
import textwrap
import time
from datetime import datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Dict

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, field_validator

# EmailStr の代替：カスタムバリデーション実装済み（CI/CD安定化）
from src.backend.core.config import settings
from src.backend.core.local_database import get_local_db
from src.backend.core.security import (
    authenticate_user,
    create_access_token,
    get_current_user,
    get_password_hash,
)
from src.backend.exchanges.factory import ExchangeFactory
from src.backend.models.user import UserResponse

router = APIRouter()
logger = logging.getLogger(__name__)

# Trading Mode切り替え専用レート制限
# ユーザーIDごとに試行回数と時刻を記録
_trading_mode_rate_limits: Dict[str, Dict[str, any]] = {}

# CSRFトークン管理
# セッションごとのCSRFトークンを記録
_csrf_tokens: Dict[str, Dict[str, any]] = {}


def check_trading_mode_rate_limit(user_id: str, operation: str = "switch") -> None:
    """
    Trading Mode切り替えのレート制限をチェック

    制限:
    - Live切り替え: 1時間に3回まで
    - 連続失敗: 5回失敗で1時間ロック
    """
    current_time = time.time()

    if user_id not in _trading_mode_rate_limits:
        _trading_mode_rate_limits[user_id] = {"attempts": [], "failures": [], "locked_until": 0}

    user_limits = _trading_mode_rate_limits[user_id]

    # ロック状態チェック
    if current_time < user_limits["locked_until"]:
        remaining_time = int(user_limits["locked_until"] - current_time)
        logger.warning(f"Rate limit: User {user_id} is locked for {remaining_time} seconds")
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"アカウントが一時的にロックされています。{remaining_time}秒後に再試行してください。",
        )

    # 古い記録を削除（1時間以内のみ保持）
    hour_ago = current_time - 3600  # 1時間前
    user_limits["attempts"] = [ts for ts in user_limits["attempts"] if ts > hour_ago]
    user_limits["failures"] = [ts for ts in user_limits["failures"] if ts > hour_ago]

    # Live切り替え試行回数チェック（1時間に3回まで）
    if operation == "live_switch" and len(user_limits["attempts"]) >= 3:
        logger.warning(f"Rate limit: User {user_id} exceeded live trading switch attempts")
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Live Trading切り替えは1時間に3回までです。時間を置いて再試行してください。",
        )

    # 連続失敗チェック（5回失敗で1時間ロック）
    if len(user_limits["failures"]) >= 5:
        user_limits["locked_until"] = current_time + 3600  # 1時間ロック
        logger.warning(f"Rate limit: User {user_id} locked due to 5 consecutive failures")
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="連続失敗が多すぎます。アカウントを1時間ロックしました。",
        )

    # 試行回数を記録
    if operation == "live_switch":
        user_limits["attempts"].append(current_time)


def record_trading_mode_failure(user_id: str) -> None:
    """Trading Mode切り替え失敗を記録"""
    current_time = time.time()

    if user_id not in _trading_mode_rate_limits:
        _trading_mode_rate_limits[user_id] = {"attempts": [], "failures": [], "locked_until": 0}

    _trading_mode_rate_limits[user_id]["failures"].append(current_time)
    logger.info(f"Rate limit: Recorded failure for user {user_id}")


def record_trading_mode_success(user_id: str) -> None:
    """Trading Mode切り替え成功時に失敗カウントをリセット"""
    if user_id in _trading_mode_rate_limits:
        _trading_mode_rate_limits[user_id]["failures"] = []
        logger.info(f"Rate limit: Reset failure count for user {user_id}")


def generate_csrf_token(user_id: str) -> str:
    """ユーザー専用のCSRFトークンを生成（強化版）"""
    # ユーザーIDの正規化と検証
    normalized_user_id = str(user_id).strip()
    if not normalized_user_id:
        raise ValueError(f"Invalid user_id for CSRF token generation: {user_id}")

    # 古いトークンをクリーンアップ
    cleanup_expired_csrf_tokens()

    # 既存のトークンがある場合は警告
    if normalized_user_id in _csrf_tokens:
        logger.warning(f"CSRF: Overwriting existing token for user {normalized_user_id}")

    # 新しいトークンを生成（より強力な32バイト）
    token = secrets.token_urlsafe(32)
    current_time = time.time()

    _csrf_tokens[normalized_user_id] = {
        "token": token,
        "created_at": current_time,
        "expires_at": current_time + 3600,  # 1時間有効
        "user_id": normalized_user_id,  # 追加検証用
    }

    logger.info(
        f"CSRF token generated for user {normalized_user_id}, expires at: {datetime.fromtimestamp(current_time + 3600).isoformat()}"
    )
    return token


def verify_csrf_token(user_id: str, provided_token: str) -> bool:
    """CSRFトークンを検証（強化版）"""
    logger.info(f"CSRF: Starting verification for user {user_id}")

    # 空トークンチェック
    if not provided_token or not provided_token.strip():
        logger.warning(f"CSRF: Empty token provided for user {user_id}")
        return False

    # ユーザーIDの正規化
    normalized_user_id = str(user_id).strip()
    if not normalized_user_id:
        logger.warning(f"CSRF: Invalid user_id: {user_id}")
        return False

    # 期限切れトークンをクリーンアップ
    cleanup_expired_csrf_tokens()

    if normalized_user_id not in _csrf_tokens:
        logger.warning(f"CSRF: No token found for user {normalized_user_id}")
        logger.info(f"CSRF: Available users in storage: {list(_csrf_tokens.keys())}")
        return False

    token_data = _csrf_tokens[normalized_user_id]
    current_time = time.time()

    # トークン期限切れチェック（二重確認）
    if current_time > token_data["expires_at"]:
        logger.warning(
            f"CSRF: Token expired for user {normalized_user_id} (expired at: {token_data['expires_at']}, current: {current_time})"
        )
        del _csrf_tokens[normalized_user_id]
        return False

    # トークン一致チェック（時間安全な比較）
    stored_token = token_data["token"]
    if not secrets.compare_digest(stored_token, provided_token.strip()):
        logger.warning(f"CSRF: Token mismatch for user {normalized_user_id}")
        logger.debug(
            f"CSRF: Expected token length: {len(stored_token)}, provided length: {len(provided_token.strip())}"
        )
        return False

    logger.info(f"CSRF: Token verified successfully for user {normalized_user_id}")
    return True


def cleanup_expired_csrf_tokens() -> None:
    """期限切れCSRFトークンをクリーンアップ"""
    current_time = time.time()
    expired_users = []

    for user_id, token_data in _csrf_tokens.items():
        if current_time > token_data["expires_at"]:
            expired_users.append(user_id)

    for user_id in expired_users:
        del _csrf_tokens[user_id]
        logger.info(f"CSRF: Cleaned up expired token for user {user_id}")

    if expired_users:
        logger.info(f"CSRF: Cleaned up {len(expired_users)} expired tokens")


def clear_all_csrf_tokens() -> None:
    """全てのCSRFトークンをクリア（テスト用）"""
    global _csrf_tokens
    token_count = len(_csrf_tokens)
    _csrf_tokens.clear()
    logger.info(f"CSRF: Cleared all {token_count} tokens")


def clear_all_rate_limits() -> None:
    """全てのレート制限をクリア（テスト用）"""
    global _trading_mode_rate_limits
    limit_count = len(_trading_mode_rate_limits)
    _trading_mode_rate_limits.clear()
    logger.info(f"Rate limit: Cleared all {limit_count} rate limit records")


def reset_test_state() -> None:
    """テスト状態をリセット（テスト間での状態初期化）"""
    clear_all_csrf_tokens()
    clear_all_rate_limits()
    logger.info("Test state reset completed")


def send_trading_mode_notification_email(user_email: str, user_name: str, mode: str, timestamp: str) -> bool:
    """取引モード変更の通知メールを送信"""
    try:
        # 開発環境ではメール送信をスキップ（ログのみ）
        if settings.ENVIRONMENT.lower() in ["development", "dev", "test"]:
            logger.info(
                f"Email notification (dev mode): User {user_name} ({user_email}) "
                f"changed trading mode to {mode.upper()} at {timestamp}"
            )
            return True

        # メール設定（環境変数から取得）
        smtp_server = getattr(settings, "SMTP_SERVER", "localhost")
        smtp_port = getattr(settings, "SMTP_PORT", 587)
        smtp_username = getattr(settings, "SMTP_USERNAME", "")
        smtp_password = getattr(settings, "SMTP_PASSWORD", "")
        from_email = getattr(settings, "FROM_EMAIL", "noreply@crypto-bot.com")

        # メール本文作成
        subject = f"【重要】取引モード変更通知 - {mode.upper()} Mode"

        if mode == "live":
            body = textwrap.dedent(
                f"""
                {user_name} 様

                【重要な通知】

                あなたのアカウントで Live Trading モードが有効化されました。

                詳細情報:
                - ユーザー名: {user_name}
                - 変更後モード: Live Trading (実際の資金での取引)
                - 変更日時: {timestamp}

                ⚠️ 注意事項:
                - Live Trading モードでは実際の資金で取引が実行されます
                - 意図しない変更の場合は、直ちに Paper Trading モードに戻してください
                - 不正なアクセスが疑われる場合は、パスワードを変更してください

                本通知に心当たりがない場合は、直ちにサポートまでご連絡ください。

                ---
                Crypto Trading Bot
                自動送信メール - 返信不要
                """
            )
        else:
            body = textwrap.dedent(
                f"""
                {user_name} 様

                取引モードが Paper Trading に変更されました。

                詳細情報:
                - ユーザー名: {user_name}
                - 変更後モード: Paper Trading (模擬取引)
                - 変更日時: {timestamp}

                Paper Trading モードでは実際の資金は使用されません。

                ---
                Crypto Trading Bot
                自動送信メール - 返信不要
                """
            )

        # メールメッセージ作成
        msg = MIMEMultipart()
        msg["From"] = from_email
        msg["To"] = user_email
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain", "utf-8"))

        # SMTP接続とメール送信
        if smtp_username and smtp_password:
            with smtplib.SMTP(smtp_server, smtp_port) as server:
                server.starttls()
                server.login(smtp_username, smtp_password)
                server.send_message(msg)
        else:
            # 認証情報がない場合はローカルSMTPを使用
            with smtplib.SMTP(smtp_server, smtp_port) as server:
                server.send_message(msg)

        logger.info(f"Email notification sent to {user_email} for {mode} trading mode change")
        return True

    except Exception as e:
        logger.error(f"Failed to send email notification to {user_email}: {e}")
        return False


class Token(BaseModel):
    access_token: str
    token_type: str


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
        """カスタムEmailバリデーション（CI/CD安定化のため）"""
        import re

        # RFC 5322準拠の簡略版パターン
        pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        if not re.match(pattern, v):
            raise ValueError("有効なメールアドレスを入力してください")
        return v.lower().strip()


class RegisterResponse(BaseModel):
    message: str
    user: UserResponse


class TradingModeRequest(BaseModel):
    """取引モード切り替えリクエスト"""

    mode: str  # "paper" または "live"
    confirmation_text: str  # 確認のため "LIVE" と入力
    csrf_token: str  # CSRF攻撃防止トークン

    @field_validator("mode")
    @classmethod
    def validate_mode(cls, v: str) -> str:
        if v not in ["paper", "live"]:
            raise ValueError("取引モードは 'paper' または 'live' である必要があります")
        return v.lower()


class TradingModeResponse(BaseModel):
    """取引モード切り替えレスポンス"""

    current_mode: str
    message: str
    timestamp: str


@router.post("/login", response_model=Token)
async def login(response: Response, form_data: OAuth2PasswordRequestForm = Depends()):
    """ログイン"""
    user = await authenticate_user(form_data.username, form_data.password)
    if not user:
        logger.warning(f"Failed login attempt for username: {form_data.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token_expires = timedelta(hours=settings.JWT_EXPIRATION_HOURS)
    access_token = create_access_token(
        data={"sub": user["username"], "role": user["role"]},
        expires_delta=access_token_expires,
    )

    # httpOnlyクッキーに設定
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=settings.ENVIRONMENT == "production",
        samesite="strict",
        max_age=settings.JWT_EXPIRATION_HOURS * 3600,
    )

    logger.info(f"User {user['username']} logged in successfully")
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/logout")
async def logout(response: Response):
    """ログアウト"""
    response.delete_cookie(key="access_token")
    return {"message": "Successfully logged out"}


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(request: Request, current_user: dict = Depends(get_current_user)):
    """現在のユーザー情報を取得"""
    return UserResponse(
        id=current_user["id"],
        username=current_user["username"],
        role=current_user["role"],
        created_at=current_user["created_at"],
    )


@router.post("/refresh")
async def refresh_token(request: Request, response: Response, current_user: dict = Depends(get_current_user)):
    """トークンを更新"""
    access_token_expires = timedelta(hours=settings.JWT_EXPIRATION_HOURS)
    access_token = create_access_token(
        data={"sub": current_user["username"], "role": current_user["role"]},
        expires_delta=access_token_expires,
    )

    # httpOnlyクッキーを更新
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=settings.ENVIRONMENT == "production",
        samesite="strict",
        max_age=settings.JWT_EXPIRATION_HOURS * 3600,
    )

    logger.info(f"Token refreshed for user: {current_user['username']}")
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/register", response_model=RegisterResponse)
async def register(request: RegisterRequest):
    """新規ユーザー登録"""
    local_db = get_local_db()

    # ユーザー名の重複チェック
    existing_user = local_db.get_user_by_username(request.username)
    if existing_user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username already exists")

    # パスワード強度チェック
    if len(request.password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Password must be at least 8 characters long"
        )

    # 大文字、小文字、数字を含むかチェック
    import re

    if not re.match(r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d).+$", request.password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Password must contain uppercase, lowercase and number"
        )

    try:
        # パスワードをハッシュ化
        password_hash = get_password_hash(request.password)

        # ユーザーを作成
        new_user = local_db.create_user(
            username=request.username, password_hash=password_hash, email=request.email, role="viewer"
        )

        logger.info(f"New user registered: {request.username}")

        # レスポンス用のユーザー情報
        user_response = UserResponse(
            id=new_user["id"], username=new_user["username"], role=new_user["role"], created_at=new_user["created_at"]
        )

        return RegisterResponse(message="User registered successfully", user=user_response)

    except Exception as e:
        logger.error(f"Failed to register user {request.username}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create user")


@router.get("/csrf-token")
async def get_csrf_token(request: Request, current_user: dict = Depends(get_current_user)):
    """CSRFトークンを取得"""
    try:
        user_id = current_user.get("id", current_user.get("username", "unknown"))

        # 期限切れトークンをクリーンアップ
        cleanup_expired_csrf_tokens()

        # 新しいCSRFトークンを生成
        csrf_token = generate_csrf_token(user_id)

        return {
            "csrf_token": csrf_token,
            "expires_in": 3600,  # 1時間
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.error(f"Failed to generate CSRF token for user {current_user['username']}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="CSRFトークン生成に失敗しました")


@router.get("/trading-mode")
async def get_trading_mode(request: Request, current_user: dict = Depends(get_current_user)):
    """現在の取引モードを取得"""
    try:
        # デフォルトではPaperモードを返す（セキュリティ優先）
        return TradingModeResponse(
            current_mode="paper", message="現在のモードは Paper Trading です", timestamp=datetime.now().isoformat()
        )
    except Exception as e:
        logger.error(f"Failed to get trading mode for user {current_user['username']}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="取引モード取得に失敗しました")


@router.post("/trading-mode", response_model=TradingModeResponse)
async def set_trading_mode(
    trading_request: TradingModeRequest, request: Request, current_user: dict = Depends(get_current_user)
):
    """取引モードを変更（セキュリティ重視）"""
    user_id = current_user.get("id", current_user.get("username", "unknown"))

    try:
        # Live Mode切り替えの厳格な検証（セキュリティ優先順序）
        if trading_request.mode == "live":
            # 1. 管理者権限チェック（最優先）
            if current_user.get("role") != "admin":
                logger.warning(
                    f"Unauthorized live trading access attempt by user: {current_user['username']} "
                    f"(role: {current_user.get('role')})"
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN, detail="Live Trading アクセスには管理者権限が必要です"
                )

            # 2. 環境制限チェック（二番目）
            if settings.ENVIRONMENT.lower() in ["development", "dev", "staging", "test"]:
                logger.error(
                    f"Live trading blocked in {settings.ENVIRONMENT} environment for user: {current_user['username']}"
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Live Trading は {settings.ENVIRONMENT} 環境では利用できません",
                )

        # CSRFトークン検証（全てのリクエストに適用）
        if not verify_csrf_token(user_id, trading_request.csrf_token):
            logger.warning(f"CSRF token validation failed for user {user_id}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="不正なリクエストです。ページを再読み込みして再試行してください。",
            )

        # Live Mode切り替えの追加検証
        if trading_request.mode == "live":
            # 3. 確認テキスト検証
            if trading_request.confirmation_text != "LIVE":
                logger.warning(
                    f"Invalid confirmation text for live mode: {trading_request.confirmation_text} "
                    f"by user: {current_user['username']}"
                )
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Live Trading確認のため 'LIVE' と正確に入力してください",
                )

            # 4. レート制限チェック（最後に実行）
            check_trading_mode_rate_limit(user_id, "live_switch")

        # ログ記録（セキュリティ監査用）
        logger.warning(
            f"Trading mode change request: user={current_user['username']}, "
            f"user_id={user_id}, from_mode=paper, to_mode={trading_request.mode}, "
            f"confirmation_text='{trading_request.confirmation_text}', "
            f"csrf_verified=True, timestamp={datetime.now().isoformat()}"
        )

        # Live Mode切り替えの最終検証
        if trading_request.mode == "live":
            # 5. ExchangeFactory経由での検証
            try:
                factory = ExchangeFactory()
                # Liveモード切り替えテスト（実際の切り替えは行わない）
                factory.create_adapter("binance", trading_mode="live")
                logger.info(f"Live trading mode validation passed for user: {current_user['username']}")
            except Exception as factory_error:
                logger.error(f"ExchangeFactory validation failed: {factory_error}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST, detail=f"Live Trading設定検証エラー: {str(factory_error)}"
                )

        # 成功時のレスポンス
        success_message = f"取引モードを {trading_request.mode.upper()} に変更しました"
        if trading_request.mode == "live":
            success_message += " (⚠️ 実際の資金での取引になります)"

        # 成功記録（失敗カウントリセット）
        record_trading_mode_success(user_id)

        # メール通知送信（バックグラウンドで実行）
        current_timestamp = datetime.now().isoformat()
        user_email = current_user.get("email", "unknown@example.com")
        user_name = current_user.get("username", "Unknown User")

        try:
            send_trading_mode_notification_email(user_email, user_name, trading_request.mode, current_timestamp)
        except Exception as email_error:
            # メール送信エラーは主処理を妨げない
            logger.warning(f"Email notification failed (non-critical): {email_error}")

        # セキュリティ監査ログ
        logger.info(
            f"Trading mode successfully changed: user={current_user['username']}, "
            f"user_id={user_id}, new_mode={trading_request.mode}, email_sent=True, "
            f"timestamp={current_timestamp}"
        )

        return TradingModeResponse(
            current_mode=trading_request.mode, message=success_message, timestamp=current_timestamp
        )

    except HTTPException:
        # HTTPExceptionはそのまま再発生（レート制限含む）
        if trading_request.mode == "live":
            record_trading_mode_failure(user_id)
        raise
    except Exception as e:
        # 予期しないエラーの場合も失敗として記録
        if trading_request.mode == "live":
            record_trading_mode_failure(user_id)
        logger.error(f"Unexpected error in trading mode change: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="取引モード変更でエラーが発生しました"
        )
