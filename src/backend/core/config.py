import secrets
from typing import List

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Application
    APP_NAME: str = "Crypto Bot"
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"

    # Security
    JWT_SECRET: str = secrets.token_urlsafe(32)
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_HOURS: int = 24

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
    GLASSNODE_KEY: str = ""
    CRYPTOQUANT_KEY: str = ""

    # Risk Management
    MAX_DD_PCT: float = 5.0
    MAX_POSITION_SIZE_PCT: float = 10.0

    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 100

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


settings = Settings()
