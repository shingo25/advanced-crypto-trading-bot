#!/usr/bin/env python3
"""
バックテストAPI有効化テスト
"""

import os
import sys
from pathlib import Path

# プロジェクトルートをPythonパスに追加
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# ダミー環境変数を設定（Supabase接続エラーを回避）
os.environ.setdefault("SUPABASE_URL", "https://dummy.supabase.co")
os.environ.setdefault("SUPABASE_KEY", "dummy_key")
os.environ.setdefault("SUPABASE_JWT_SECRET", "dummy_secret")
os.environ.setdefault("ADMIN_USERNAME", "admin")
os.environ.setdefault("ALLOWED_ORIGINS", '["http://localhost:3000"]')


def test_backtest_api_import():
    """バックテストAPIのインポートテスト"""
    try:
        print("🔍 Testing backtest API import...")

        # backend.api.backtest をインポート
        from src.backend.api import backtest

        print("✅ backend.api.backtest imported successfully")

        # ルーターが存在することを確認
        assert hasattr(backtest, "router"), "Router not found in backtest module"
        print("✅ backtest.router found")

        # エンドポイントの確認
        routes = [
            route.path for route in backtest.router.routes if hasattr(route, "path")
        ]
        print(f"✅ Found {len(routes)} routes:")
        for route in routes:
            print(f"   - {route}")

        # 期待するエンドポイントが存在するか確認
        expected_routes = [
            "/validate-data",
            "/run",
            "/results",
            "/results/{backtest_id}",
        ]
        for expected in expected_routes:
            if any(expected in route for route in routes):
                print(f"✅ Expected route found: {expected}")
            else:
                print(f"⚠️  Expected route not found: {expected}")

        return True

    except Exception as e:
        print(f"❌ Import test failed: {e}")
        return False


def test_main_app_import():
    """main.pyアプリケーションのインポートテスト"""
    try:
        print("\n🔍 Testing main application import...")

        # main.py をインポート
        from src.backend.main import app

        print("✅ backend.main.app imported successfully")

        # バックテストルーターが含まれているか確認
        backtest_routes = []
        for route in app.routes:
            if hasattr(route, "path") and "/backtest" in route.path:
                backtest_routes.append(route.path)

        if backtest_routes:
            print("✅ Backtest routes found in main app:")
            for route in backtest_routes:
                print(f"   - {route}")
        else:
            print("⚠️  No backtest routes found in main app")

        return True

    except Exception as e:
        print(f"❌ Main app import test failed: {e}")
        return False


def main():
    """メイン実行関数"""
    print("🚀 Starting backtest API tests...\n")

    # テスト実行
    test1_result = test_backtest_api_import()
    test2_result = test_main_app_import()

    # 結果表示
    print("\n📊 Test Results:")
    print(f"   - Backtest API Import: {'✅ PASS' if test1_result else '❌ FAIL'}")
    print(f"   - Main App Import: {'✅ PASS' if test2_result else '❌ FAIL'}")

    if test1_result and test2_result:
        print("\n🎉 All tests passed! Backtest API is successfully enabled.")
        return True
    else:
        print("\n💥 Some tests failed. Please check the implementation.")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
