"""
DuckDBベースのローカルデータベース（Phase3用簡易実装）
"""

import logging
import os
import uuid
from datetime import datetime
from typing import Any, Dict, Optional

import duckdb

logger = logging.getLogger(__name__)


class LocalDatabase:
    """DuckDBベースのローカルデータベース"""

    def __init__(self, db_path: str = "crypto_bot.db"):
        self.db_path = db_path
        self.connection = None
        self._init_database()

    def _init_database(self):
        """データベースを初期化"""
        try:
            self.connection = duckdb.connect(self.db_path)
            self._create_tables()
            logger.info(f"Local database initialized: {self.db_path}")
        except Exception as e:
            logger.error(f"Failed to initialize local database: {e}")
            raise

    def _create_tables(self):
        """テーブルを作成"""
        try:
            # ユーザーテーブル
            self.connection.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id VARCHAR PRIMARY KEY,
                    username VARCHAR UNIQUE NOT NULL,
                    email VARCHAR,
                    password_hash VARCHAR NOT NULL,
                    role VARCHAR DEFAULT 'viewer',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """
            )

            # セッションテーブル（オプション）
            self.connection.execute(
                """
                CREATE TABLE IF NOT EXISTS user_sessions (
                    id VARCHAR PRIMARY KEY,
                    user_id VARCHAR NOT NULL,
                    token_hash VARCHAR NOT NULL,
                    expires_at TIMESTAMP NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            """
            )

            logger.info("Database tables created successfully")

        except Exception as e:
            logger.error(f"Failed to create tables: {e}")
            raise

    def create_user(self, username: str, password_hash: str, email: str = None, role: str = "viewer") -> Dict[str, Any]:
        """ユーザーを作成"""
        try:
            user_id = str(uuid.uuid4())
            now = datetime.now()

            self.connection.execute(
                """
                INSERT INTO users (id, username, email, password_hash, role, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
                (user_id, username, email, password_hash, role, now, now),
            )

            return {
                "id": user_id,
                "username": username,
                "email": email,
                "password_hash": password_hash,
                "role": role,
                "created_at": now,
            }

        except Exception as e:
            logger.error(f"Failed to create user {username}: {e}")
            raise

    def get_user_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        """ユーザー名でユーザーを取得"""
        try:
            result = self.connection.execute(
                "SELECT id, username, email, password_hash, role, created_at FROM users WHERE username = ?", (username,)
            ).fetchone()

            if result:
                return {
                    "id": result[0],
                    "username": result[1],
                    "email": result[2],
                    "password_hash": result[3],
                    "role": result[4],
                    "created_at": result[5],
                }
            return None

        except Exception as e:
            logger.error(f"Failed to get user by username {username}: {e}")
            return None

    def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """ユーザーIDでユーザーを取得"""
        try:
            result = self.connection.execute(
                "SELECT id, username, email, password_hash, role, created_at FROM users WHERE id = ?", (user_id,)
            ).fetchone()

            if result:
                return {
                    "id": result[0],
                    "username": result[1],
                    "email": result[2],
                    "password_hash": result[3],
                    "role": result[4],
                    "created_at": result[5],
                }
            return None

        except Exception as e:
            logger.error(f"Failed to get user by ID {user_id}: {e}")
            return None

    def update_user(self, user_id: str, **kwargs) -> Optional[Dict[str, Any]]:
        """ユーザー情報を更新"""
        try:
            if not kwargs:
                return self.get_user_by_id(user_id)

            # 更新可能なフィールドを定義（SQL injection対策）
            allowed_fields = ["username", "email", "password_hash", "role"]
            update_fields = {k: v for k, v in kwargs.items() if k in allowed_fields}

            if not update_fields:
                return self.get_user_by_id(user_id)

            # 安全なUPDATEクエリを構築（プリペアドステートメント使用）
            # フィールド名はホワイトリストで検証済み
            set_clause = ", ".join([f"{field} = ?" for field in update_fields.keys()])
            values = list(update_fields.values())
            values.append(datetime.now())  # updated_at
            values.append(user_id)  # WHERE条件

            # プリペアドステートメントでSQL injection を防止
            # フィールド名はホワイトリストで検証済み、プリペアドステートメント使用
            query = f"UPDATE users SET {set_clause}, updated_at = ? WHERE id = ?"  # nosec B608

            self.connection.execute(query, values)

            return self.get_user_by_id(user_id)

        except Exception as e:
            logger.error(f"Failed to update user {user_id}: {e}")
            return None

    def delete_user(self, user_id: str) -> bool:
        """ユーザーを削除"""
        try:
            # 関連セッションも削除
            self.connection.execute("DELETE FROM user_sessions WHERE user_id = ?", (user_id,))

            # ユーザーを削除
            result = self.connection.execute("DELETE FROM users WHERE id = ?", (user_id,))

            return result.rowcount > 0

        except Exception as e:
            logger.error(f"Failed to delete user {user_id}: {e}")
            return False

    def close(self):
        """データベース接続を閉じる"""
        if self.connection:
            self.connection.close()
            self.connection = None
            logger.info("Database connection closed")


# グローバルインスタンス
_local_db_instance: Optional[LocalDatabase] = None


def get_local_db() -> LocalDatabase:
    """ローカルデータベースインスタンスを取得"""
    global _local_db_instance
    if _local_db_instance is None:
        db_path = os.path.join(os.getcwd(), "data", "crypto_bot.db")
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        _local_db_instance = LocalDatabase(db_path)
    return _local_db_instance


def init_local_db():
    """ローカルデータベースを初期化し、デモユーザーを作成"""
    try:
        db = get_local_db()

        # デモユーザーが存在しない場合は作成
        demo_user = db.get_user_by_username("demo")
        if not demo_user:
            from src.backend.core.security import get_password_hash

            password_hash = get_password_hash("demo")
            db.create_user(username="demo", password_hash=password_hash, email="demo@example.com", role="viewer")
            logger.info("Demo user created successfully")

        # 管理者ユーザーをチェック
        from src.backend.core.config import settings

        admin_user = db.get_user_by_username(settings.ADMIN_USERNAME)
        if not admin_user:
            from src.backend.core.security import get_password_hash

            password_hash = get_password_hash(settings.ADMIN_PASSWORD)
            db.create_user(
                username=settings.ADMIN_USERNAME, password_hash=password_hash, email="admin@example.com", role="admin"
            )
            logger.info(f"Admin user created: {settings.ADMIN_USERNAME}")

        logger.info("Local database initialization completed")

    except Exception as e:
        logger.error(f"Failed to initialize local database: {e}")
        raise
