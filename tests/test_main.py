"""
テスト用のmain.py（データベース初期化なし）
APIエンドポイントの構造をテストするため
"""

# テスト用の簡易化されたルーター
from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware

# テスト用のヘルスチェックルーター
health_router = APIRouter()


@health_router.get("/health")
async def test_health():
    return {"status": "healthy", "message": "Test API is running"}


@health_router.get("/ohlcv")
async def test_ohlcv():
    return {"message": "OHLCV endpoint is available (test mode)"}


@health_router.get("/symbols")
async def test_symbols():
    return {"symbols": ["BTCUSDT", "ETHUSDT"]}


# FastAPIアプリケーション作成
app = FastAPI(title="Crypto Bot API Test", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# テストルーターを登録
app.include_router(health_router, prefix="/api/market-data", tags=["test-market-data"])

# Performance test router
performance_router = APIRouter()


@performance_router.get("/health")
async def test_performance_health():
    return {"status": "healthy", "message": "Performance API is running"}


@performance_router.get("/history")
async def test_performance_history():
    return {"message": "Performance history endpoint (test mode)"}


@performance_router.get("/summary")
async def test_performance_summary():
    return {"message": "Performance summary endpoint (test mode)"}


app.include_router(performance_router, prefix="/api/performance", tags=["test-performance"])


@app.get("/")
async def root():
    return {"message": "Crypto Bot Test API is running"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
