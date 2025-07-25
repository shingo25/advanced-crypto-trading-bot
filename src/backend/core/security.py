from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext

from src.backend.core.config import settings
from src.backend.core.database import Database
from src.backend.core.local_database import get_local_db

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """パスワードを検証"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """パスワードをハッシュ化"""
    return pwd_context.hash(password)


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """JWTトークンを作成"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(hours=settings.JWT_EXPIRATION_HOURS)

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
    return encoded_jwt


def decode_token(token: str) -> Dict[str, Any]:
    """JWTトークンをデコード"""
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


def get_token_from_request(request: Request, token: Optional[str] = Depends(oauth2_scheme)) -> Optional[str]:
    """リクエストからトークンを取得（BearerヘッダーまたはhttpOnlyクッキー）"""
    if token:
        return token

    # httpOnlyクッキーからトークンを取得
    cookie_token = request.cookies.get("access_token")
    if cookie_token:
        return cookie_token

    return None


async def get_current_user(
    request: Request = None,
    db: Database = None,
    token: Optional[str] = None,
) -> Dict[str, Any]:
    """現在のユーザーを取得（個人用途ボット - 認証無効化）

    個人用途のため認証機能を無効化し、固定ユーザーを返す
    """
    # 個人用途ボット用の固定ユーザー情報
    return {
        "id": "personal-user",
        "username": "personal-bot-user",
        "email": "user@personal-bot.local",
        "role": "admin",
        "is_active": True,
        "created_at": "2024-01-01T00:00:00Z",
    }


async def require_admin(
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """管理者権限を要求"""
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return current_user


async def authenticate_user(username: str, password: str) -> Optional[Dict[str, Any]]:
    """ユーザー認証（ローカルDuckDB使用）"""
    try:
        # ローカルデータベースからユーザーを取得
        local_db = get_local_db()
        user = local_db.get_user_by_username(username)

        if user and verify_password(password, user["password_hash"]):
            return user
        else:
            return None

    except Exception as e:
        import logging

        logger = logging.getLogger(__name__)
        logger.error(f"Authentication error for {username}: {e}")
        return None
