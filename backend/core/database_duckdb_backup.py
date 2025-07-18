import duckdb
from pathlib import Path
import logging
from typing import Optional, List, Dict, Any
from backend.core.config import settings

logger = logging.getLogger(__name__)


class Database:
    def __init__(self):
        self.conn = None
        self.path = settings.DUCKDB_PATH

    def connect(self):
        """データベースに接続"""
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = duckdb.connect(self.path)
        logger.info(f"Connected to DuckDB at {self.path}")

    def close(self):
        """データベース接続を閉じる"""
        if self.conn:
            self.conn.close()
            logger.info("Closed DuckDB connection")

    def execute(self, query: str, params=None):
        """クエリを実行"""
        if not self.conn:
            self.connect()
        return self.conn.execute(query, params)

    def fetchone(self, query: str, params=None):
        """1行取得"""
        result = self.execute(query, params)
        return result.fetchone()

    def fetchall(self, query: str, params=None):
        """全行取得"""
        result = self.execute(query, params)
        return result.fetchall()


db = Database()


def init_db():
    """データベースを初期化"""
    db.connect()

    # テーブル作成
    queries = [
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            username VARCHAR UNIQUE NOT NULL,
            password_hash VARCHAR NOT NULL,
            role VARCHAR DEFAULT 'viewer',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS strategies (
            id INTEGER PRIMARY KEY,
            name VARCHAR UNIQUE NOT NULL,
            enabled BOOLEAN DEFAULT true,
            config JSON,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS trades (
            id INTEGER PRIMARY KEY,
            strategy_id INTEGER REFERENCES strategies(id),
            symbol VARCHAR NOT NULL,
            side VARCHAR NOT NULL,
            price DECIMAL(20, 8),
            amount DECIMAL(20, 8),
            fee DECIMAL(20, 8),
            realized_pnl DECIMAL(20, 8),
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS positions (
            id INTEGER PRIMARY KEY,
            strategy_id INTEGER REFERENCES strategies(id),
            symbol VARCHAR NOT NULL,
            side VARCHAR NOT NULL,
            entry_price DECIMAL(20, 8),
            amount DECIMAL(20, 8),
            unrealized_pnl DECIMAL(20, 8),
            opened_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            closed_at TIMESTAMP
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS backtests (
            id INTEGER PRIMARY KEY,
            strategy_id INTEGER REFERENCES strategies(id),
            start_date DATE,
            end_date DATE,
            initial_capital DECIMAL(20, 8),
            final_capital DECIMAL(20, 8),
            total_trades INTEGER,
            win_rate DECIMAL(5, 2),
            sharpe_ratio DECIMAL(10, 4),
            max_drawdown DECIMAL(5, 2),
            config JSON,
            results JSON,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS config (
            key VARCHAR PRIMARY KEY,
            value JSON,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """,
    ]

    for query in queries:
        db.execute(query)

    # デフォルト管理者ユーザーを作成
    from backend.core.security import get_password_hash

    existing_admin = db.fetchone(
        "SELECT id FROM users WHERE username = ?", [settings.ADMIN_USERNAME]
    )
    if not existing_admin:
        db.execute(
            "INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)",
            [
                settings.ADMIN_USERNAME,
                get_password_hash(settings.ADMIN_PASSWORD),
                "admin",
            ],
        )
        logger.info(f"Created default admin user: {settings.ADMIN_USERNAME}")

    # デフォルト設定を挿入
    default_configs = [
        ("max_dd_pct", settings.MAX_DD_PCT),
        ("max_position_size_pct", settings.MAX_POSITION_SIZE_PCT),
    ]

    for key, value in default_configs:
        db.execute(
            "INSERT OR REPLACE INTO config (key, value) VALUES (?, ?)",
            [key, {"value": value}],
        )

    logger.info("Database initialized successfully")


def get_db() -> Database:
    """データベースセッションを取得"""
    return db


def get_user_by_username(username: str) -> Optional[Dict[str, Any]]:
    """ユーザー名でユーザーを取得"""
    result = db.fetchone(
        "SELECT id, username, password_hash, role, created_at FROM users WHERE username = ?",
        [username],
    )
    if result:
        return {
            "id": result[0],
            "username": result[1],
            "password_hash": result[2],
            "role": result[3],
            "created_at": result[4],
        }
    return None


def get_user_by_id(user_id: int) -> Optional[Dict[str, Any]]:
    """ユーザーIDでユーザーを取得"""
    result = db.fetchone(
        "SELECT id, username, password_hash, role, created_at FROM users WHERE id = ?",
        [user_id],
    )
    if result:
        return {
            "id": result[0],
            "username": result[1],
            "password_hash": result[2],
            "role": result[3],
            "created_at": result[4],
        }
    return None


def create_user(
    username: str, password_hash: str, role: str = "viewer"
) -> Dict[str, Any]:
    """ユーザーを作成"""
    db.execute(
        "INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)",
        [username, password_hash, role],
    )
    return get_user_by_username(username)


def update_user(user_id: int, **kwargs) -> Optional[Dict[str, Any]]:
    """ユーザー情報を更新"""
    if not kwargs:
        return get_user_by_id(user_id)

    set_clause = ", ".join([f"{key} = ?" for key in kwargs.keys()])
    values = list(kwargs.values()) + [user_id]

    db.execute(f"UPDATE users SET {set_clause} WHERE id = ?", values)
    return get_user_by_id(user_id)


def delete_user(user_id: int) -> bool:
    """ユーザーを削除"""
    result = db.execute("DELETE FROM users WHERE id = ?", [user_id])
    return result.rowcount > 0
