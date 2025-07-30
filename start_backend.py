#!/usr/bin/env python3
"""
Advanced Crypto Trading Bot - Backend Server Startup
"""
import os
import sys

# プロジェクトルートをPythonパスに追加
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

if __name__ == "__main__":
    import uvicorn

    from backend.core.local_database import init_local_db

    print("🚀 Starting Advanced Crypto Trading Bot Backend...")

    # データベース初期化
    print("📊 Initializing database...")
    try:
        init_local_db()
        print("✅ Database initialized successfully")
    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
        sys.exit(1)

    # バックエンドサーバー起動
    print("🔄 Starting FastAPI server...")
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True, log_level="info")
