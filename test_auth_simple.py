#!/usr/bin/env python3
"""
Simple auth API のテスト用起動スクリプト
"""
import uvicorn

if __name__ == "__main__":
    print("🚀 Starting Simple Auth API Test Server...")
    print("📡 Demo user: username=demo, password=demo")
    print("🔗 Test URLs:")
    print("   - POST http://localhost:8001/login")
    print("   - POST http://localhost:8001/register")
    print("   - GET  http://localhost:8001/health")
    
    uvicorn.run(
        "api.auth_simple:app",
        host="0.0.0.0",
        port=8001,
        reload=True,
        log_level="info"
    )