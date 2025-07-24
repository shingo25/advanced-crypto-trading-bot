import logging
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Response, status
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
from src.backend.models.user import UserResponse

router = APIRouter()
logger = logging.getLogger(__name__)


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
async def get_current_user_info(current_user: dict = Depends(get_current_user)):
    """現在のユーザー情報を取得"""
    return UserResponse(
        id=current_user["id"],
        username=current_user["username"],
        role=current_user["role"],
        created_at=current_user["created_at"],
    )


@router.post("/refresh")
async def refresh_token(response: Response, current_user: dict = Depends(get_current_user)):
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
