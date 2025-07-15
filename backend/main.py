from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
from backend.core.config import settings
from backend.api import auth, strategies
# TODO: Update these modules to use Supabase SDK
# from backend.api import backtest, config, trades
from backend.core.database import init_db
from backend.core.logging import setup_logging

setup_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting crypto bot backend...")
    init_db()
    yield
    logger.info("Shutting down crypto bot backend...")


app = FastAPI(
    title="Crypto Bot API",
    version="1.0.0",
    lifespan=lifespan
)

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
# TODO: Update these modules to use Supabase SDK
# app.include_router(backtest.router, prefix="/backtest", tags=["backtest"])
# app.include_router(config.router, prefix="/config", tags=["config"])
# app.include_router(trades.router, prefix="/trades", tags=["trades"])


@app.get("/")
async def root():
    return {"message": "Crypto Bot API is running"}


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


# Vercel handler
handler = app