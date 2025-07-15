#!/usr/bin/env python3
"""
デモ用サーバー起動スクリプト
"""
import sys
import os
import subprocess
import threading
import time

# プロジェクトルートをPATHに追加
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

def start_backend():
    """バックエンドサーバーを起動"""
    print("🚀 バックエンドサーバーを起動中...")
    backend_path = os.path.join(project_root, "backend")
    os.chdir(backend_path)
    
    # 必要な依存関係のみインストール
    subprocess.run([
        sys.executable, "-m", "pip", "install", 
        "fastapi", "uvicorn", "python-dotenv", "pydantic", "pydantic-settings",
        "python-jose[cryptography]", "passlib[bcrypt]", "supabase"
    ], check=False)
    
    # 環境変数を設定
    env = os.environ.copy()
    env["PYTHONPATH"] = project_root
    
    # uvicornでサーバー起動
    subprocess.run([
        sys.executable, "-m", "uvicorn", "main:app", 
        "--reload", "--host", "0.0.0.0", "--port", "8000"
    ], env=env)

def start_frontend():
    """フロントエンドサーバーを起動"""
    print("🎨 フロントエンドサーバーを起動中...")
    frontend_path = os.path.join(project_root, "frontend")
    os.chdir(frontend_path)
    
    # npm依存関係をインストール
    subprocess.run(["npm", "install"], check=False)
    
    # 開発サーバー起動
    subprocess.run(["npm", "run", "dev"])

def main():
    print("🤖 Crypto Bot デモサーバーを起動します...")
    print("📁 プロジェクトルート:", project_root)
    
    # バックエンドをバックグラウンドで起動
    backend_thread = threading.Thread(target=start_backend, daemon=True)
    backend_thread.start()
    
    # 少し待ってからフロントエンド起動
    time.sleep(3)
    
    # フロントエンドを起動（メインスレッド）
    try:
        start_frontend()
    except KeyboardInterrupt:
        print("\n👋 サーバーを停止しています...")

if __name__ == "__main__":
    main()