import duckdb
from pathlib import Path
import logging
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
        """
    ]
    
    for query in queries:
        db.execute(query)
    
    # デフォルト管理者ユーザーを作成
    from backend.core.security import get_password_hash
    
    existing_admin = db.fetchone("SELECT id FROM users WHERE username = ?", [settings.ADMIN_USERNAME])
    if not existing_admin:
        db.execute(
            "INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)",
            [settings.ADMIN_USERNAME, get_password_hash(settings.ADMIN_PASSWORD), "admin"]
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
            [key, {"value": value}]
        )
    
    logger.info("Database initialized successfully")