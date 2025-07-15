from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from backend.core.config import settings
from backend.core.database import get_db, get_user_by_username, get_user_by_id, Database
from backend.core.supabase_db import get_supabase_connection

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
    request: Request, 
    db: Database = Depends(get_db),
    token: Optional[str] = Depends(oauth2_scheme)
) -> Dict[str, Any]:
    """現在のユーザーを取得し、データベースで検証"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    # BearerトークンかhttpOnlyクッキーから取得
    if not token:
        token = request.cookies.get("access_token")
    
    if not token:
        raise credentials_exception
    
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    # データベースでユーザーの存在を確認
    user = get_user_by_username(username)
    if user is None:
        raise credentials_exception
    
    return user


async def require_admin(current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    """管理者権限を要求"""
    if current_user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user


async def authenticate_user(username: str, password: str) -> Optional[Dict[str, Any]]:
    """ユーザー認証（Supabase Auth使用）"""
    try:
        connection = get_supabase_connection()
        client = connection.client
        
        # ユーザー名からメールアドレスを構築
        # 注意: 実際の実装では、ユーザー名とメールの対応付けをDBに保存することを推奨
        email = f"{username}@example.com"
        
        # Supabase Authで認証
        response = client.auth.sign_in_with_password({
            "email": email,
            "password": password
        })
        
        if response.user:
            user_id = response.user.id
            user_email = response.user.email
            user_metadata = response.user.user_metadata or {}
            
            # profilesテーブルからユーザー情報を取得
            user_profile = get_user_by_id(user_id)
            
            if user_profile:
                # サインアウト（セッションをクリア）
                client.auth.sign_out()
                return user_profile
            else:
                # プロファイルが見つからない場合、基本情報を返す
                client.auth.sign_out()
                return {
                    "id": user_id,
                    "username": user_metadata.get("username", username),
                    "role": user_metadata.get("role", "viewer"),
                    "password_hash": "",  # 互換性のため
                    "created_at": response.user.created_at
                }
        else:
            return None
            
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Authentication error for {username}: {e}")
        return None