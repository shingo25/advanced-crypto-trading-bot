#!/usr/bin/env python3
"""
Supabase Auth統合後の認証システムをテストするスクリプト
"""
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from backend.core.security import authenticate_user, create_access_token
from backend.core.config import settings
from dotenv import load_dotenv
import asyncio


async def test_supabase_authentication():
    """Supabase Auth統合認証のテスト"""
    print("🔐 Supabase Auth統合認証のテスト中...")

    try:
        # 正しいクレデンシャルでの認証テスト
        print(
            f"   🔑 管理者認証テスト: {settings.ADMIN_USERNAME} / {settings.ADMIN_PASSWORD}"
        )

        user = await authenticate_user(settings.ADMIN_USERNAME, settings.ADMIN_PASSWORD)

        if user:
            print("   ✅ 管理者認証成功！")
            print(f"   📊 ユーザーID: {user['id']}")
            print(f"   📊 ユーザー名: {user['username']}")
            print(f"   📊 ロール: {user['role']}")
            print(f"   📊 作成日時: {user.get('created_at', 'N/A')}")

            # JWTトークン作成テスト
            print("\n🎫 JWTトークン作成テスト...")
            token = create_access_token(
                data={"sub": user["username"], "role": user["role"]}
            )
            print(f"   ✅ JWTトークン作成成功: {token[:50]}...")

            return True
        else:
            print("   ❌ 管理者認証失敗")
            return False

    except Exception as e:
        print(f"   ❌ 認証テストエラー: {e}")
        import traceback

        traceback.print_exc()
        return False


async def test_invalid_authentication():
    """無効な認証のテスト"""
    print("\n🚫 無効な認証のテスト中...")

    try:
        # 間違ったパスワードでの認証テスト
        user = await authenticate_user(settings.ADMIN_USERNAME, "wrong_password")

        if not user:
            print("   ✅ 間違ったパスワードは正しく拒否されました")
        else:
            print("   ❌ 間違ったパスワードが受け入れられました（問題）")

        # 存在しないユーザーでの認証テスト
        user = await authenticate_user("nonexistent_user", "any_password")

        if not user:
            print("   ✅ 存在しないユーザーは正しく拒否されました")
            return True
        else:
            print("   ❌ 存在しないユーザーが受け入れられました（問題）")
            return False

    except Exception as e:
        print(f"   ❌ 無効認証テストエラー: {e}")
        return False


async def test_auth_api_simulation():
    """auth.py APIの動作をシミュレート"""
    print("\n🌐 API認証フローのシミュレーション...")

    try:
        # ログインAPIのシミュレーション
        username = settings.ADMIN_USERNAME
        password = settings.ADMIN_PASSWORD

        print(f"   📡 ログインリクエスト: {username}")

        # authenticate_user を呼び出し（APIと同じ流れ）
        user = await authenticate_user(username, password)

        if user:
            # JWTトークン作成（APIと同じ流れ）
            from datetime import timedelta

            access_token_expires = timedelta(hours=settings.JWT_EXPIRATION_HOURS)
            access_token = create_access_token(
                data={"sub": user["username"], "role": user["role"]},
                expires_delta=access_token_expires,
            )

            print("   ✅ APIログインフロー成功")
            print("   📊 レスポンス情報:")
            print(f"     - access_token: {access_token[:30]}...")
            print("     - token_type: bearer")
            print(f"     - user_id: {user['id']}")
            print(f"     - username: {user['username']}")
            print(f"     - role: {user['role']}")

            return True
        else:
            print("   ❌ APIログインフロー失敗")
            return False

    except Exception as e:
        print(f"   ❌ APIシミュレーションエラー: {e}")
        return False


async def main():
    """メインテスト関数"""
    print("🧪 Supabase Auth統合後の認証システム包括テスト")
    print("=" * 60)

    # 環境変数を読み込み
    load_dotenv()

    # テスト結果を追跡
    test_results = []

    # 1. Supabase認証テスト
    test_results.append(await test_supabase_authentication())

    # 2. 無効認証テスト
    test_results.append(await test_invalid_authentication())

    # 3. API認証フローシミュレーション
    test_results.append(await test_auth_api_simulation())

    # 結果サマリー
    print("\n" + "=" * 60)
    print("📊 テスト結果サマリー:")

    passed = sum(test_results)
    total = len(test_results)

    print(f"   成功: {passed}/{total}")
    print(f"   成功率: {(passed/total)*100:.1f}%")

    if passed == total:
        print("🎉 Phase1-1.5 認証API更新が完了しました！")
        print("🔄 次のステップ: strategies.py の更新に進む準備完了")
        return True
    else:
        print("⚠️ 一部のテストで問題が発生しました")
        print("   修正が必要な可能性があります")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    if success:
        print("\n✅ Supabase Auth認証テスト完了")
    else:
        print("\n❌ 認証システムに重大な問題があります")
