# Supabase セットアップガイド 🚀

crypto-botプロジェクトのSupabase統合のための設定手順です。

## ステップ 1: Supabaseプロジェクトの作成 ✅

- Supabaseプロジェクトが既に作成済み

## ステップ 2: データベーススキーマの作成 ✅

- `database/supabase-schema.sql`ファイルが既に準備済み
- プロファイル、取引所、戦略、取引履歴、ポジション、バックテスト結果、設定の7つのテーブル
- Row Level Security (RLS) 設定済み

## ステップ 3: API キーの設定 🔄 **← 現在ここ**

### 3.1 SupabaseダッシュボードでAPIキーを取得

1. [Supabaseダッシュボード](https://supabase.com/dashboard)にログイン
2. 作成した `crypto-bot` プロジェクトを選択
3. 左側メニューの **Settings** (⚙️) をクリック
4. **API** セクションを選択
5. 以下をコピー：
   - **Project URL**
   - **anon** (public) key → `SUPABASE_ANON_KEY`
   - **service_role** (secret) key → `SUPABASE_SERVICE_ROLE_KEY`

### 3.2 ローカル環境設定

`.env`ファイルに以下を設定：

```bash
# Database - Supabase
SUPABASE_URL="あなたのProject URL"
SUPABASE_ANON_KEY="あなたのanon key"
SUPABASE_SERVICE_ROLE_KEY="あなたのservice_role key"
```

### 3.3 Vercel環境変数設定

1. [Vercelダッシュボード](https://vercel.com/)でプロジェクトを選択
2. **Settings** → **Environment Variables**
3. 以下の3つの変数を追加（全環境: Production, Preview, Development）：
   - `SUPABASE_URL`
   - `SUPABASE_ANON_KEY`
   - `SUPABASE_SERVICE_ROLE_KEY`

## ステップ 4: 接続テスト

```bash
python test_supabase_connection.py
```

## ステップ 5: Row Level Security の設定

データベーススキーマが既に RLS 設定を含んでいるため、そのままSQL文を実行するだけです。

## セキュリティ注意事項 🔒

- **service_role key**: 絶対にフロントエンドコードに含めない
- **anon key**: フロントエンドで安全に使用可能（RLSで保護済み）
- `.env`ファイルはGitに含めない（`.gitignore`で除外済み）

## 次のステップ

1. ✅ プロジェクト作成
2. ✅ スキーマ準備
3. 🔄 API設定 (現在)
4. ⏳ 接続テスト
5. ⏳ RLS設定
6. ⏳ Vercelデプロイ
