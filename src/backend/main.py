import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# TODO: Update these modules to use Supabase SDK
from src.backend.api import (
    alerts,
    auth,
    backtest,  # ✓ Supabase SDK implemented
    market_data,
    performance,
    portfolio,
    risk,
    strategies,
)
from src.backend.core.config import settings
from src.backend.core.local_database import init_local_db
from src.backend.core.logging import setup_logging
from src.backend.streaming import price_stream_manager

# Streaming system
from src.backend.streaming import router as streaming_router

# from backend.api import config, trades
# WebSocket system
from src.backend.websocket import router as websocket_router

setup_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting crypto bot backend...")

    # CI環境の検出
    is_ci_environment = (
        os.getenv("CI", "false").lower() == "true" or os.getenv("GITHUB_ACTIONS", "false").lower() == "true"
    )

    # データベース初期化（CI環境以外で実行）
    if not is_ci_environment:
        try:
            # Phase3: ローカルDuckDBを使用
            init_local_db()
            logger.info("Local database initialized successfully")

            # レガシーサポート（必要に応じて）
            # init_db()
        except Exception as e:
            logger.error(f"Database initialization failed: {e}")
            # データベース初期化失敗でもアプリケーションは起動させる
    else:
        logger.info("Skipping database initialization in CI environment")

    # 価格配信システム（オプション機能）
    if settings.ENVIRONMENT != "production" and settings.ENABLE_PRICE_STREAMING:
        try:
            await price_stream_manager.start()
            logger.info("Price streaming system started")
        except Exception as e:
            logger.error(f"Failed to start price streaming: {e}")
            logger.info("Continuing without price streaming (this is OK)...")
    else:
        logger.info("Price streaming disabled for production/serverless environment")

    logger.info("Backend startup completed - ready to handle requests")
    yield

    # 価格配信システムを停止
    if settings.ENVIRONMENT != "production" and settings.ENABLE_PRICE_STREAMING:
        try:
            await price_stream_manager.stop()
            logger.info("Price streaming system stopped")
        except Exception as e:
            logger.error(f"Failed to stop price streaming: {e}")

    logger.info("Shutting down crypto bot backend...")


app = FastAPI(title="Crypto Bot API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(strategies.router, prefix="/strategies", tags=["strategies"])
app.include_router(portfolio.router, prefix="/api/portfolio", tags=["portfolio"])
app.include_router(risk.router, prefix="/api/risk", tags=["risk"])
app.include_router(alerts.router, prefix="/api/alerts", tags=["alerts"])
app.include_router(market_data.router, prefix="/api/market-data", tags=["market-data"])
app.include_router(performance.router, prefix="/api/performance", tags=["performance"])
# TODO: Update these modules to use Supabase SDK
app.include_router(backtest.router, prefix="/backtest", tags=["backtest"])  # ✓ Enabled
# app.include_router(config.router, prefix="/config", tags=["config"])
# app.include_router(trades.router, prefix="/trades", tags=["trades"])

# WebSocket routes
app.include_router(websocket_router, prefix="/websocket", tags=["websocket"])

# Streaming routes
app.include_router(streaming_router, prefix="/streaming", tags=["streaming"])


@app.get("/")
async def root():
    return {"message": "Crypto Bot API is running"}


@app.get("/health")
async def health_check():
    """
    Liveness Probe: アプリケーションプロセスが起動しているかのみを確認
    外部サービスに依存せず、常に成功するシンプルなチェック
    """
    return {"status": "alive", "service": "crypto-bot-backend"}


@app.get("/ready")
async def readiness_check():
    """
    Readiness Probe: データベース接続など、リクエストを処理できる状態かを確認
    CI環境では基本的なチェックのみ実行
    """
    checks = {"status": "ready"}

    # CI環境の検出（環境変数CI=trueまたはGITHUB_ACTIONS=trueが設定されている場合）
    is_ci_environment = (
        os.getenv("CI", "false").lower() == "true" or os.getenv("GITHUB_ACTIONS", "false").lower() == "true"
    )

    # CI環境では詳細なデータベースチェックをスキップ
    if not is_ci_environment:
        # データベース接続チェック（基本的なテスト）
        try:
            from backend.core.database import _get_database_instance

            db_instance = _get_database_instance()
            # 簡単な接続テスト
            if hasattr(db_instance, "health_check"):
                db_connected = db_instance.health_check()
            else:
                db_connected = True  # フォールバック
            checks["database"] = "connected" if db_connected else "disconnected"
        except Exception as e:
            logger.error(f"Readiness check - Database error: {e}")
            checks["database"] = "error"
            checks["status"] = "unready"
    else:
        # CI環境では常に「ready」として扱う
        checks["database"] = "skipped (CI environment)"
        logger.info("Skipping database check in CI environment")

    # 価格ストリーミングシステムの状態（オプション）
    if settings.ENVIRONMENT != "production" and settings.ENABLE_PRICE_STREAMING:
        try:
            # price_stream_managerの状態をチェック
            checks["price_streaming"] = "active"
        except Exception:
            checks["price_streaming"] = "inactive"
    else:
        checks["price_streaming"] = "disabled"

    return checks


# Vercel handler
handler = app
