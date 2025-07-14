from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class User(BaseModel):
    """ユーザーモデル"""
    id: int
    username: str
    password_hash: str
    role: str = "viewer"
    created_at: datetime
    
    class Config:
        from_attributes = True


class UserCreate(BaseModel):
    """ユーザー作成用モデル"""
    username: str
    password: str
    role: str = "viewer"


class UserResponse(BaseModel):
    """ユーザーレスポンス用モデル"""
    id: int
    username: str
    role: str
    created_at: datetime
    
    class Config:
        from_attributes = True


class UserUpdate(BaseModel):
    """ユーザー更新用モデル"""
    username: Optional[str] = None
    password: Optional[str] = None
    role: Optional[str] = None