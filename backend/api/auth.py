from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from backend.core.security import verify_password, create_access_token, get_current_user
from backend.core.database import db
import logging

router = APIRouter()
logger = logging.getLogger(__name__)


class Token(BaseModel):
    access_token: str
    token_type: str


class User(BaseModel):
    username: str
    role: str


@router.post("/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """ログイン"""
    # ユーザーを検索
    user = db.fetchone(
        "SELECT username, password_hash, role FROM users WHERE username = ?",
        [form_data.username]
    )
    
    if not user or not verify_password(form_data.password, user[1]):
        logger.warning(f"Failed login attempt for username: {form_data.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # トークンを作成
    access_token = create_access_token(
        data={"sub": user[0], "role": user[2]}
    )
    
    logger.info(f"User {user[0]} logged in successfully")
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me", response_model=User)
async def get_current_user_info(current_user: dict = Depends(get_current_user)):
    """現在のユーザー情報を取得"""
    return User(username=current_user["username"], role=current_user["role"])