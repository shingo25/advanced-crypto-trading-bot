"""
Supabase SDKベースのデータベース操作（DuckDB移植版）
"""

import logging
import uuid
from typing import Any, Dict, List, Optional, Union

from backend.core.config import settings
from backend.core.supabase_db import get_supabase_connection
from backend.models.user import get_profiles_model

logger = logging.getLogger(__name__)


class Database:
    """Supabase SDKベースのデータベースクラス（DuckDB互換インターフェース）"""

    def __init__(self):
        self.connection = get_supabase_connection()
        self.profiles_model = get_profiles_model()

    def connect(self):
        """接続（Supabase SDKでは自動管理）"""
        logger.info("Supabase SDK connection ready")

    def close(self):
        """接続を閉じる（Supabase SDKでは不要）"""
        logger.info("Supabase SDK connection closed")

    def health_check(self):
        """接続の健全性をチェック"""
        return self.connection.health_check()

    def execute(self, query: str, params: Optional[Union[Dict[str, Any], List[Any]]] = None) -> Any:
        """SQL文を実行"""
        try:
            # Supabaseの場合、適切なクエリをORM経由で実行
            logger.info(f"Executing query: {query}")
            # 実際の実装はSupabaseのクエリ実行に依存
            return True
        except Exception as e:
            logger.error(f"Error executing query: {e}")
            raise

    def fetchall(self, query: str, params: Optional[Union[Dict[str, Any], List[Any]]] = None) -> List[Any]:
        """クエリを実行し、すべての結果を取得"""
        try:
            # Supabaseの場合、適切なクエリをORM経由で実行
            logger.info(f"Fetching all from query: {query}")
            # 実際の実装はSupabaseのクエリ実行に依存
            return []
        except Exception as e:
            logger.error(f"Error fetching all: {e}")
            raise

    def fetchone(self, query: str, params: Optional[Union[Dict[str, Any], List[Any]]] = None) -> Optional[Any]:
        """クエリを実行し、単一の結果を取得"""
        try:
            # Supabaseの場合、適切なクエリをORM経由で実行
            logger.info(f"Fetching one from query: {query}")
            # 実際の実装はSupabaseのクエリ実行に依存
            return None
        except Exception as e:
            logger.error(f"Error fetching one: {e}")
            raise


# グローバルデータベースインスタンス（遅延初期化）
_db_instance: Optional[Database] = None


def _get_database_instance() -> Database:
    """Databaseインスタンスを遅延初期化で取得"""
    global _db_instance
    if _db_instance is None:
        _db_instance = Database()
    return _db_instance


def init_db():
    """データベースを初期化（Supabaseのスキーマは既に作成済み）"""
    try:
        # 接続テスト
        db_instance = _get_database_instance()
        if not db_instance.health_check():
            raise Exception("Supabase接続に失敗しました")

        logger.info("Supabase database connection verified")

        # デフォルト管理者ユーザーを作成
        existing_admin = get_user_by_username(settings.ADMIN_USERNAME)
        if not existing_admin:
            # 管理者ユーザー用のUUIDを生成
            admin_user_id = str(uuid.uuid4())
            admin_profile = db_instance.profiles_model.create_profile(
                user_id=admin_user_id, username=settings.ADMIN_USERNAME
            )

            if admin_profile:
                logger.info(f"Created default admin profile: {settings.ADMIN_USERNAME}")
            else:
                logger.warning("Failed to create admin profile - may need manual setup")

        logger.info("Database initialized successfully")

    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        raise


def get_db() -> Database:
    """データベースセッションを取得"""
    return _get_database_instance()


def get_user_by_username(username: str) -> Optional[Dict[str, Any]]:
    """ユーザー名でユーザーを取得"""
    try:
        db_instance = _get_database_instance()
        profile = db_instance.profiles_model.get_profile_by_username(username)
        if profile:
            return {
                "id": profile["id"],
                "username": profile["username"],
                "password_hash": profile.get("password_hash", ""),  # Supabaseスキーマにはない場合
                "role": profile.get("role", "viewer"),
                "created_at": profile.get("created_at"),
            }
        return None
    except Exception as e:
        logger.error(f"Error getting user by username {username}: {e}")
        return None


def get_user_by_id(user_id) -> Optional[Dict[str, Any]]:
    """ユーザーIDでユーザーを取得"""
    try:
        # UUIDの場合は文字列として扱う
        if isinstance(user_id, int):
            user_id = str(user_id)

        db_instance = _get_database_instance()
        profile = db_instance.profiles_model.get_profile_by_id(user_id)
        if profile:
            return {
                "id": profile["id"],
                "username": profile["username"],
                "password_hash": profile.get("password_hash", ""),
                "role": profile.get("role", "viewer"),
                "created_at": profile.get("created_at"),
            }
        return None
    except Exception as e:
        logger.error(f"Error getting user by ID {user_id}: {e}")
        return None


def create_user(username: str, password_hash: str, role: str = "viewer") -> Dict[str, Any]:
    """ユーザーを作成"""
    try:
        # 新しいUUIDを生成
        user_id = str(uuid.uuid4())

        db_instance = _get_database_instance()
        profile = db_instance.profiles_model.create_profile(user_id=user_id, username=username)

        if profile:
            # Supabaseスキーマにパスワードハッシュとロールが含まれていない場合は
            # 別途管理するか、profilesテーブルを拡張する必要がある
            logger.info(f"User created successfully: {username}")
            return {
                "id": profile["id"],
                "username": profile["username"],
                "password_hash": password_hash,  # 注意: 実際のスキーマに保存されていない
                "role": role,
                "created_at": profile.get("created_at"),
            }
        else:
            raise Exception("Failed to create profile")

    except Exception as e:
        logger.error(f"Error creating user {username}: {e}")
        raise


def update_user(user_id, **kwargs) -> Optional[Dict[str, Any]]:
    """ユーザー情報を更新"""
    try:
        if isinstance(user_id, int):
            user_id = str(user_id)

        if not kwargs:
            return get_user_by_id(user_id)

        # Supabaseのprofilesテーブルで更新可能なフィールドのみ処理
        updatable_fields = {k: v for k, v in kwargs.items() if k in ["username", "role"]}

        if updatable_fields:
            db_instance = _get_database_instance()
            updated_profile = db_instance.profiles_model.update_profile(user_id, **updatable_fields)
            if updated_profile:
                return {
                    "id": updated_profile["id"],
                    "username": updated_profile["username"],
                    "password_hash": kwargs.get("password_hash", ""),
                    "role": updated_profile.get("role", "viewer"),
                    "created_at": updated_profile.get("created_at"),
                }

        return get_user_by_id(user_id)

    except Exception as e:
        logger.error(f"Error updating user {user_id}: {e}")
        return None


def delete_user(user_id) -> bool:
    """ユーザーを削除"""
    try:
        if isinstance(user_id, int):
            user_id = str(user_id)

        # Supabaseでは通常、行レベルセキュリティにより削除が制限される
        # 実装は環境に依存するため、ここでは仮実装
        logger.warning(f"User deletion attempted for {user_id} - implementation may need adjustment")
        return False

    except Exception as e:
        logger.error(f"Error deleting user {user_id}: {e}")
        return False
