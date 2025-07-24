"""
最小限のVercel FastAPI - テスト用
"""

from fastapi import FastAPI
from mangum import Mangum

app = FastAPI()

@app.get("/")
def read_root():
    return {"status": "ok", "message": "Minimal test working"}

@app.get("/health")  
def health():
    return {"status": "healthy", "service": "crypto-bot-api"}

# Vercel handler - Mangumを使用してASGI → AWS Lambda互換に変換
handler = Mangum(app)