"""
FastAPIを使った最小限のVercel関数
"""

from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def read_root():
    return {"status": "healthy", "message": "Minimal FastAPI working"}

# Vercel handler
handler = app