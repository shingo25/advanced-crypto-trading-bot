#!/usr/bin/env python3
"""
SQLAlchemyでSupabase接続をテストするスクリプト
"""
import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv


def test_supabase_connection():
    """SQLAlchemyでSupabase接続をテスト"""
    print("🔌 SQLAlchemyでSupabase接続をテスト中...")

    # 環境変数を読み込み
    load_dotenv()

    # Supabase接続情報を取得
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_service_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

    if not supabase_url or not supabase_service_key:
        print("❌ SUPABASE_URLまたはSUPABASE_SERVICE_ROLE_KEYが設定されていません")
        return False

    # Supabase URLからPostgreSQL接続URLを構築
    # https://huuimmgmxtqigbjfpudo.supabase.co → direct connection
    project_id = supabase_url.split("//")[1].split(".")[0]

    # Direct connection (より確実)
    db_url = f"postgresql://postgres:{supabase_service_key}@db.{project_id}.supabase.co:5432/postgres"

    print(
        f"🔗 接続URL: postgresql://postgres:***@db.{project_id}.supabase.co:5432/postgres"
    )

    try:
        # SQLAlchemyエンジンを作成
        engine = create_engine(db_url, echo=True)  # echoで実行SQLを表示

        # 接続テスト
        with engine.connect() as connection:
            # 簡単なクエリを実行
            result = connection.execute(
                text("SELECT current_database(), current_user, version()")
            )
            row = result.fetchone()

            print("✅ Supabase接続成功！")
            print(f"   データベース: {row[0]}")
            print(f"   ユーザー: {row[1]}")
            print(f"   PostgreSQLバージョン: {row[2].split(',')[0]}")

            # 既存のテーブルを確認
            result = connection.execute(
                text(
                    """
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                ORDER BY table_name
            """
                )
            )
            tables = [row[0] for row in result.fetchall()]

            print(f"   既存のテーブル数: {len(tables)}")
            if tables:
                print(f"   テーブル: {', '.join(tables)}")

            return True

    except Exception as e:
        print(f"❌ 接続エラー: {e}")
        return False


if __name__ == "__main__":
    success = test_supabase_connection()
    if success:
        print("🎉 Step 2完了: SQLAlchemy接続テスト成功！")
    else:
        print("💔 Step 2失敗: 接続問題を修正してください")
