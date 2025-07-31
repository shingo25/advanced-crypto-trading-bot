#!/usr/bin/env python3
"""
Supabase Authに管理者ユーザーを作成するスクリプト
"""
import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from backend.core.config import settings
from backend.core.supabase_db import get_supabase_connection
from dotenv import load_dotenv


def create_admin_user():
    """Supabase Authに管理者ユーザーを作成（Service Roleを使用）"""
    print("🔧 Supabase Authに管理者ユーザーを作成中...")

    try:
        # Service Role Keyを使用してSupabaseクライアントを作成
        from supabase import create_client

        url = settings.SUPABASE_URL
        service_role_key = settings.SUPABASE_SERVICE_ROLE_KEY
        admin_client = create_client(url, service_role_key)

        # 管理者ユーザーのメールアドレスとパスワード
        admin_email = f"{settings.ADMIN_USERNAME}@example.com"
        admin_password = settings.ADMIN_PASSWORD

        print(f"   📧 メールアドレス: {admin_email}")
        print(f"   🔐 パスワード: {admin_password}")

        # Admin APIを使用してユーザーを作成（メール確認をスキップ）
        response = admin_client.auth.admin.create_user(
            {
                "email": admin_email,
                "password": admin_password,
                "email_confirm": True,  # メール確認をスキップ
                "user_metadata": {"username": settings.ADMIN_USERNAME, "role": "admin"},
            }
        )

        if response.user:
            user_id = response.user.id
            print("   ✅ Supabase Authユーザー作成成功")
            print(f"   📊 ユーザーID: {user_id}")
            print(f"   📧 メール: {response.user.email}")

            # profilesテーブルに対応するプロファイルを作成
            from backend.models.user import get_profiles_model

            profiles_model = get_profiles_model()

            profile = profiles_model.create_profile(user_id=user_id, username=settings.ADMIN_USERNAME)

            if profile:
                print(f"   ✅ プロファイル作成成功: {profile['username']}")
            else:
                print("   ⚠️ プロファイル作成に失敗")

            return True

        else:
            print("   ❌ Supabase Authユーザー作成に失敗")
            if hasattr(response, "error") and response.error:
                print(f"   エラー: {response.error}")
            return False

    except Exception as e:
        print(f"   ❌ 管理者ユーザー作成エラー: {e}")
        import traceback

        traceback.print_exc()
        return False


def check_existing_user():
    """既存の管理者ユーザーをチェック"""
    print("\n🔍 既存の管理者ユーザーをチェック中...")

    try:
        connection = get_supabase_connection()
        client = connection.client

        admin_email = f"{settings.ADMIN_USERNAME}@example.com"

        # メールアドレスでサインインを試行
        response = client.auth.sign_in_with_password({"email": admin_email, "password": settings.ADMIN_PASSWORD})

        if response.user:
            print("   ✅ 既存の管理者ユーザーが見つかりました")
            print(f"   📊 ユーザーID: {response.user.id}")
            print(f"   📧 メール: {response.user.email}")

            # サインアウト
            client.auth.sign_out()
            return True
        else:
            print("   ❌ 既存の管理者ユーザーが見つかりません")
            return False

    except Exception as e:
        print(f"   ⚠️ 既存ユーザーチェックエラー: {e}")
        return False


def main():
    """メイン実行関数"""
    print("🧪 Supabase Auth管理者ユーザーセットアップ")
    print("=" * 50)

    # 環境変数を読み込み
    load_dotenv()

    # 既存ユーザーをチェック
    existing_user = check_existing_user()

    if existing_user:
        print("\n🎉 管理者ユーザーは既に存在します")
        print("次のステップ: 認証APIの更新に進むことができます")
        return True
    else:
        print("\n🔧 新しい管理者ユーザーを作成します...")
        success = create_admin_user()

        if success:
            print("\n🎉 管理者ユーザーのセットアップが完了しました！")
            print("次のステップ: 認証APIの更新に進むことができます")
            return True
        else:
            print("\n❌ 管理者ユーザーのセットアップに失敗しました")
            return False


if __name__ == "__main__":
    success = main()
    if success:
        print("\n✅ セットアップ完了")
    else:
        print("\n❌ セットアップに失敗しました")
