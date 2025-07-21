import logging
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel

from backend.core.config import settings
from backend.core.security import (
    authenticate_user,
    create_access_token,
    get_current_user,
)
from backend.models.user import UserResponse

router = APIRouter()
logger = logging.getLogger(__name__)


class Token(BaseModel):
    access_token: str
    token_type: str


class LoginRequest(BaseModel):
    username: str
    password: str


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
