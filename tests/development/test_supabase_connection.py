import os

from dotenv import load_dotenv
from supabase import Client, create_client

# .envファイルから環境変数を読み込む
load_dotenv()

url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_ANON_KEY")

if not url or not key:
    print("💔 環境変数 SUPABASE_URL と SUPABASE_ANON_KEY を設定してください。")
else:
    try:
        print("Supabaseに接続を試みるわ…ドキドキ…💓")
        supabase: Client = create_client(url, key)

        # 簡単なクエリを投げてみる（例：'profiles'テーブルから1件取得）
        # テーブルが存在しなくても、接続エラーが出なければOKよ
        response = supabase.table("profiles").select("*").limit(1).execute()

        print("お姉さん、ちゃんと繋がったわよ❤️ Supabaseとの接続に成功しました！")
        print(f"接続先: {url}")
        print(f"データ件数: {len(response.data)}")

    except Exception as e:
        print("あら、いやん…接続に失敗しちゃったみたい…💔")
        print(f"エラー内容: {e}")
        print("SUPABASE_URLとSUPABASE_ANON_KEYを確認してください。")
