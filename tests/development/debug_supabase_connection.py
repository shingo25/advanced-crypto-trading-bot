#!/usr/bin/env python3
"""
Supabase接続のデバッグスクリプト
"""
import os

from dotenv import load_dotenv
from supabase import Client, create_client


def debug_supabase():
    """Supabase接続の詳細情報を取得"""
    print("🔍 Supabase接続情報をデバッグ中...")

    # 環境変数を読み込み
    load_dotenv()

    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_ANON_KEY")
    service_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

    print(f"📍 SUPABASE_URL: {url}")
    print(f"🔑 ANON_KEY: {key[:20]}..." if key else "🔑 ANON_KEY: None")
    print(f"🔒 SERVICE_KEY: {service_key[:20]}..." if service_key else "🔒 SERVICE_KEY: None")

    try:
        # Supabase SDKで接続テスト
        supabase: Client = create_client(url, key)

        # 簡単なクエリを実行してみる
        response = supabase.table("profiles").select("*").limit(1).execute()

        print("✅ Supabase SDK接続成功！")
        print(f"   レスポンス: {response}")

        # プロジェクト情報を推測
        project_id = url.split("//")[1].split(".")[0]
        print(f"   プロジェクトID: {project_id}")

        # 可能なPostgreSQL URLパターンを表示
        possible_urls = [
            f"postgresql://postgres:{service_key}@db.{project_id}.supabase.co:5432/postgres",
            f"postgresql://postgres.{project_id}:{service_key}@aws-0-ap-northeast-1.pooler.supabase.com:6543/postgres",
            f"postgresql://postgres.{project_id}:{service_key}@aws-0-us-east-1.pooler.supabase.com:6543/postgres",
            f"postgresql://postgres.{project_id}:{service_key}@aws-0-us-west-1.pooler.supabase.com:6543/postgres",
        ]

        print("\n🔗 試行可能なPostgreSQL URL:")
        for i, url_pattern in enumerate(possible_urls, 1):
            masked_url = url_pattern.replace(service_key, "***")
            print(f"   {i}. {masked_url}")

        return True, possible_urls

    except Exception as e:
        print(f"❌ Supabase SDK接続エラー: {e}")
        return False, []


if __name__ == "__main__":
    success, urls = debug_supabase()
    if success:
        print("\n🎯 次のステップ: 上記のURL候補でSQLAlchemy接続をテストします")
    else:
        print("\n💔 Supabase基本接続に問題があります")
