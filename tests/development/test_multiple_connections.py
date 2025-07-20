#!/usr/bin/env python3
"""
複数のPostgreSQL URL候補でSQLAlchemy接続をテストするスクリプト
"""
import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv


def test_multiple_connections():
    """複数のURL候補でSQLAlchemy接続をテスト"""
    print("🔌 複数のURL候補でSQLAlchemy接続をテスト中...")

    # 環境変数を読み込み
    load_dotenv()

    supabase_url = os.getenv("SUPABASE_URL")
    service_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

    if not supabase_url or not service_key:
        print("❌ 環境変数が設定されていません")
        return False

    project_id = supabase_url.split("//")[1].split(".")[0]

    # 候補URL一覧
    url_candidates = [
        # Direct connection
        f"postgresql://postgres:{service_key}@db.{project_id}.supabase.co:5432/postgres",
        # Connection pooling (various regions)
        f"postgresql://postgres.{project_id}:{service_key}@aws-0-ap-northeast-1.pooler.supabase.com:6543/postgres",
        f"postgresql://postgres.{project_id}:{service_key}@aws-0-us-east-1.pooler.supabase.com:6543/postgres",
        f"postgresql://postgres.{project_id}:{service_key}@aws-0-us-west-1.pooler.supabase.com:6543/postgres",
        f"postgresql://postgres.{project_id}:{service_key}@aws-0-eu-west-1.pooler.supabase.com:6543/postgres",
    ]

    for i, db_url in enumerate(url_candidates, 1):
        print(f"\n🔗 候補 {i}: {db_url.replace(service_key, '***')}")

        try:
            # SQLAlchemyエンジンを作成
            engine = create_engine(db_url, pool_timeout=10, pool_recycle=3600)

            # 接続テスト
            with engine.connect() as connection:
                # 簡単なクエリを実行
                result = connection.execute(
                    text("SELECT current_database(), current_user, version()")
                )
                row = result.fetchone()

                print("✅ 接続成功！")
                print(f"   データベース: {row[0]}")
                print(f"   ユーザー: {row[1]}")
                print(f"   PostgreSQLバージョン: {row[2].split(',')[0]}")

                # 成功したURLを保存
                with open("successful_db_url.txt", "w") as f:
                    f.write(db_url)

                print("🎉 成功したURLを successful_db_url.txt に保存しました")
                return True, db_url

        except Exception as e:
            print(f"❌ 接続失敗: {str(e)[:100]}...")
            continue

    print("\n💔 すべての候補で接続に失敗しました")
    return False, None


if __name__ == "__main__":
    success, working_url = test_multiple_connections()
    if success:
        print("\n🎉 Step 2完了: SQLAlchemy接続テスト成功！")
        print(
            f"💾 動作するURL: {working_url.replace(os.getenv('SUPABASE_SERVICE_ROLE_KEY'), '***')}"
        )
    else:
        print("\n💔 Step 2失敗: すべての接続候補が失敗しました")
