#!/usr/bin/env python3
"""
バックエンドサーバー単独起動スクリプト
"""
import sys
import os
import subprocess

# プロジェクトルートをPATHに追加
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)


def main():
    print("🚀 Crypto Bot バックエンドサーバーを起動中...")

    backend_path = os.path.join(project_root, "backend")

    # 環境変数を設定
    env = os.environ.copy()
    env["PYTHONPATH"] = project_root

    try:
        # uvicornでサーバー起動
        subprocess.run(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "main:app",
                "--reload",
                "--host",
                "0.0.0.0",
                "--port",
                "8000",
            ],
            cwd=backend_path,
            env=env,
        )
    except KeyboardInterrupt:
        print("\n👋 バックエンドサーバーを停止しています...")


if __name__ == "__main__":
    main()
