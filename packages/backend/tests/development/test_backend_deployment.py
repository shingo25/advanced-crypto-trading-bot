#!/usr/bin/env python3
"""
バックエンドAPIのデプロイ前テストスクリプト
"""

# 標準ライブラリは最初にインポート
import os
import sys

# Project rootをpathに追加（インポートより前）
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 外部ライブラリをインポート
# プロジェクト内モジュールをインポート
from backend.core.config import settings
from backend.main import app
from dotenv import load_dotenv
from fastapi.testclient import TestClient


def test_app_initialization():
    """アプリケーション初期化のテスト"""
    print("🚀 アプリケーション初期化のテスト...")

    try:
        client = TestClient(app)

        # 基本エンドポイントのテスト
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        print(f"   ✅ ルートエンドポイント: {data['message']}")

        # ヘルスチェックエンドポイントのテスト
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        print("   ✅ ヘルスチェックエンドポイント正常")

        return True

    except Exception as e:
        print(f"   ❌ アプリ初期化エラー: {e}")
        return False


def test_auth_endpoints():
    """認証エンドポイントのテスト"""
    print("\n🔐 認証エンドポイントのテスト...")

    try:
        client = TestClient(app)

        # ログインエンドポイントのテスト
        login_data = {
            "username": settings.ADMIN_USERNAME,
            "password": settings.ADMIN_PASSWORD,
        }

        response = client.post("/auth/login", data=login_data)
        print(f"   📊 ログインレスポンス: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            assert "access_token" in data
            print("   ✅ ログインエンドポイント正常")

            # /auth/me エンドポイントのテスト
            token = data["access_token"]
            headers = {"Authorization": f"Bearer {token}"}

            me_response = client.get("/auth/me", headers=headers)
            if me_response.status_code == 200:
                user_data = me_response.json()
                print(f"   ✅ ユーザー情報取得: {user_data['username']}")
            else:
                print(f"   ⚠️ ユーザー情報取得エラー: {me_response.status_code}")

            return True
        else:
            print(f"   ❌ ログインエラー: {response.status_code}")
            return False

    except Exception as e:
        print(f"   ❌ 認証エンドポイントエラー: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_strategies_endpoints():
    """戦略エンドポイントのテスト"""
    print("\n🎯 戦略エンドポイントのテスト...")

    try:
        client = TestClient(app)

        # まず認証
        login_data = {
            "username": settings.ADMIN_USERNAME,
            "password": settings.ADMIN_PASSWORD,
        }

        login_response = client.post("/auth/login", data=login_data)
        if login_response.status_code != 200:
            print("   ❌ 認証失敗のため戦略テストをスキップ")
            return False

        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 戦略一覧の取得
        response = client.get("/strategies/", headers=headers)
        print(f"   📊 戦略一覧レスポンス: {response.status_code}")

        if response.status_code == 200:
            strategies = response.json()
            print(f"   ✅ 戦略一覧取得成功: {len(strategies)}件")
            return True
        else:
            print(f"   ❌ 戦略一覧取得エラー: {response.status_code}")
            return False

    except Exception as e:
        print(f"   ❌ 戦略エンドポイントエラー: {e}")
        return False


def test_cors_configuration():
    """CORS設定のテスト"""
    print("\n🌐 CORS設定のテスト...")

    try:
        client = TestClient(app)

        # プリフライトリクエストのシミュレーション
        headers = {
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Content-Type,Authorization",
        }

        response = client.options("/auth/login", headers=headers)
        print(f"   📊 OPTIONSレスポンス: {response.status_code}")

        # CORSヘッダーの確認
        cors_headers = {
            key: value for key, value in response.headers.items() if key.lower().startswith("access-control")
        }

        if cors_headers:
            print("   ✅ CORS設定確認:")
            for key, value in cors_headers.items():
                print(f"     {key}: {value}")
        else:
            print("   ⚠️ CORSヘッダーが見つかりません")

        return True

    except Exception as e:
        print(f"   ❌ CORS設定テストエラー: {e}")
        return False


def main():
    """メインテスト関数"""
    print("🧪 バックエンドAPIデプロイ前包括テスト")
    print("=" * 60)

    # 環境変数を読み込み
    load_dotenv()

    # テスト結果を追跡
    test_results = []

    # 1. アプリケーション初期化テスト
    test_results.append(test_app_initialization())

    # 2. 認証エンドポイントテスト
    test_results.append(test_auth_endpoints())

    # 3. 戦略エンドポイントテスト
    test_results.append(test_strategies_endpoints())

    # 4. CORS設定テスト
    test_results.append(test_cors_configuration())

    # 結果サマリー
    print("\n" + "=" * 60)
    print("📊 テスト結果サマリー:")

    passed = sum(test_results)
    total = len(test_results)

    print(f"   成功: {passed}/{total}")
    print(f"   成功率: {(passed/total)*100:.1f}%")

    if passed == total:
        print("🎉 バックエンドAPIはデプロイ準備完了！")
        print("🚀 次のステップ: Vercelにデプロイを実行")
        return True
    else:
        print("⚠️ 一部のテストで問題が発生しました")
        print("   修正が必要な可能性があります")
        return False


if __name__ == "__main__":
    success = main()
    if success:
        print("\n✅ デプロイ前テスト完了")
    else:
        print("\n❌ バックエンドAPIに問題があります")
