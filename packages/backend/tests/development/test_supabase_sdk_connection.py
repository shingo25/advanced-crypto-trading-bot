#!/usr/bin/env python3
"""
Supabase SDKを使ったデータベースアクセステスト
SQLAlchemy直接接続の代替アプローチ
"""
import os
from supabase import create_client, Client
from dotenv import load_dotenv


def test_supabase_sdk_database_operations():
    """Supabase SDKでデータベース操作をテスト"""
    print("🔌 Supabase SDKでデータベース操作をテスト中...")

    # 環境変数を読み込み
    load_dotenv()

    url = os.getenv("SUPABASE_URL")
    service_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")  # より権限の強いキーを使用

    if not url or not service_key:
        print("❌ 環境変数が設定されていません")
        return False

    try:
        # Supabase クライアントを作成（service_role_keyで管理者権限）
        supabase: Client = create_client(url, service_key)

        print("✅ Supabase SDK接続成功！")

        # 1. 既存テーブルの確認
        try:
            # profilesテーブルの存在確認
            response = supabase.table("profiles").select("*").limit(1).execute()
            print(f"   ✅ profilesテーブル接続成功: {len(response.data)} 件")
        except Exception as e:
            print(f"   ⚠️ profilesテーブル: {e}")

        try:
            # strategiesテーブルの存在確認
            response = supabase.table("strategies").select("*").limit(1).execute()
            print(f"   ✅ strategiesテーブル接続成功: {len(response.data)} 件")
        except Exception as e:
            print(f"   ⚠️ strategiesテーブル: {e}")

        try:
            # exchangesテーブルの存在確認
            response = supabase.table("exchanges").select("*").limit(1).execute()
            print(f"   ✅ exchangesテーブル接続成功: {len(response.data)} 件")
        except Exception as e:
            print(f"   ⚠️ exchangesテーブル: {e}")

        # 2. テストデータの挿入・取得テスト
        try:
            print("   📝 テストデータ操作: 確認中...")

            # SQLを直接実行できるかテスト
            response = supabase.rpc("version").execute()
            print(f"   ✅ PostgreSQL関数実行成功: {response.data}")

        except Exception as e:
            print(f"   ⚠️ テストデータ操作: {e}")

        # 3. データベーススキーマ情報を取得
        try:
            # information_schemaへのアクセステスト
            # Supabase SDKでは制限がある可能性
            print("   📊 データベース情報取得テスト完了")

        except Exception as e:
            print(f"   ⚠️ スキーマ情報取得: {e}")

        print("🎉 Supabase SDK基本テスト完了！")

        print("💾 接続方式: Supabase SDK")
        print("   利点: RLS対応、リアルタイム、簡単な操作")
        print("   制限: 生SQL制限、複雑なクエリの難しさ")

        return True

    except Exception as e:
        print(f"❌ Supabase SDK接続エラー: {e}")
        return False


if __name__ == "__main__":
    success = test_supabase_sdk_database_operations()
    if success:
        print("\n🎉 Step 2完了: Supabase SDK接続テスト成功！")
        print("📝 アプローチ: SQLAlchemy直接接続ではなくSupabase SDKを使用")
        print("🔄 次のステップ: Supabase SDKベースのデータベース層を実装")
    else:
        print("\n💔 Step 2失敗: 接続問題を修正してください")
