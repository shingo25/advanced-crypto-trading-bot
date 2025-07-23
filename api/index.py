"""
Vercel Hello World Test - 最小限のFastAPI
"""

from fastapi import FastAPI

app = FastAPI()

@app.get("/")
async def hello():
    return {"message": "Hello World from Vercel!", "status": "success"}

@app.get("/test")
async def test():
    return {"test": "working", "version": "hello-world"}

# Vercel handler
handler = app
