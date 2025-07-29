import secrets
import os
from typing import List
from pathlib import Path

from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# .envファイルを明示的に読み込み（セキュリティ強化）
env_path = Path(__file__).parent.parent.parent.parent / ".env"
if env_path.exists():
    load_dotenv(env_path)
else:
    # CI/CD環境や本番環境ではシステム環境変数を使用
    load_dotenv()


class Settings(BaseSettings):
    # Application
    APP_NAME: str = "Crypto Bot"
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"

    # Security
    JWT_SECRET: str = secrets.token_urlsafe(32)
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_HOURS: int = 24

    # セキュリティ強化: パスワードポリシー
    MIN_PASSWORD_LENGTH: int = 12
    REQUIRE_SPECIAL_CHARS: bool = True
    SESSION_TIMEOUT_MINUTES: int = 30
    MAX_LOGIN_ATTEMPTS: int = 5
    LOCKOUT_DURATION_MINUTES: int = 15

    # Admin
    ADMIN_USERNAME: str = "admin"
    ADMIN_PASSWORD: str = "change_this_password"

    # Database
    DUCKDB_PATH: str = "./data/crypto_bot.duckdb"

    # Supabase
    SUPABASE_URL: str = ""
    SUPABASE_ANON_KEY: str = ""
    SUPABASE_SERVICE_ROLE_KEY: str = ""

    # API Keys
    BINANCE_API_KEY: str = ""
    BINANCE_SECRET: str = ""
    BYBIT_API_KEY: str = ""
    BYBIT_SECRET: str = ""
    BITGET_API_KEY: str = ""
    BITGET_SECRET: str = ""
    HYPERLIQUID_ADDRESS: str = ""  # Ethereum address
    HYPERLIQUID_PRIVATE_KEY: str = ""  # Private key with 0x prefix
    BACKPACK_API_KEY: str = ""
    BACKPACK_SECRET: str = ""
    GLASSNODE_KEY: str = ""
    CRYPTOQUANT_KEY: str = ""

    # Risk Management
    MAX_DD_PCT: float = 5.0
    MAX_POSITION_SIZE_PCT: float = 10.0

    # Rate Limiting (セキュリティ強化)
    RATE_LIMIT_PER_MINUTE: int = 100
    RATE_LIMIT_LOGIN_PER_MINUTE: int = 5
    RATE_LIMIT_ORDER_PER_MINUTE: int = 10
    RATE_LIMIT_API_PER_SECOND: int = 10

    # Streaming System
    ENABLE_PRICE_STREAMING: bool = True

    # CORS
    ALLOWED_ORIGINS: str = (
        "http://localhost:3000,http://localhost:8000,https://*.vercel.app,https://crypto-bot-frontend.vercel.app"
    )

    @property
    def allowed_origins_list(self) -> List[str]:
        """Convert comma-separated ALLOWED_ORIGINS to list"""
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",") if origin.strip()]

    # Notifications
    NTFY_TOPIC: str = "crypto-bot-alerts"
    NTFY_SERVER: str = "https://ntfy.sh"

    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"  # Ignore extra environment variables

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # セキュリティ検証
        self._validate_security_settings()

    def _validate_security_settings(self):
        """セキュリティ設定の検証"""
        # JWT_SECRETの強度チェック
        if len(self.JWT_SECRET) < 32:
            raise ValueError("JWT_SECRET must be at least 32 characters long")

        # 管理者パスワードのセキュリティチェック
        if self.ADMIN_PASSWORD == "change_this_password":
            if self.ENVIRONMENT == "production":
                raise ValueError("Default admin password must be changed in production")

        # APIキーの存在チェック（Live Trading時）
        if self.ENVIRONMENT == "production":
            required_keys = [(self.BINANCE_API_KEY, "BINANCE_API_KEY"), (self.BINANCE_SECRET, "BINANCE_SECRET")]

            missing_keys = [name for key, name in required_keys if not key]
            if missing_keys:
                print(f"Warning: Missing API keys for production: {', '.join(missing_keys)}")

    @property
    def is_development(self) -> bool:
        """開発環境かどうか"""
        return self.ENVIRONMENT == "development"

    @property
    def is_production(self) -> bool:
        """本番環境かどうか"""
        return self.ENVIRONMENT == "production"


# シングルトンパターンで設定を初期化
settings = Settings()
