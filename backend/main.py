from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
from backend.core.config import settings
from backend.api import (
    auth,
    strategies,
    market_data,
    performance,
    portfolio,
    risk,
    alerts,
)

# TODO: Update these modules to use Supabase SDK
from backend.api import backtest  # ✓ Supabase SDK implemented
# from backend.api import config, trades

# WebSocket system
from backend.websocket import router as websocket_router

# Streaming system
from backend.streaming import router as streaming_router, price_stream_manager
from backend.core.database import init_db
from backend.core.logging import setup_logging

setup_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting crypto bot backend...")
    init_db()

    # 価格配信システムを開始
    try:
        await price_stream_manager.start()
        logger.info("Price streaming system started")
    except Exception as e:
        logger.error(f"Failed to start price streaming: {e}")

    yield

    # 価格配信システムを停止
    try:
        await price_stream_manager.stop()
        logger.info("Price streaming system stopped")
    except Exception as e:
        logger.error(f"Failed to stop price streaming: {e}")

    logger.info("Shutting down crypto bot backend...")


app = FastAPI(title="Crypto Bot API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
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
    return {"status": "healthy"}


# Vercel handler
handler = app
