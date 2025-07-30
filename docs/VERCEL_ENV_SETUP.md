# Vercel環境変数設定ガイド

## プロジェクトはすでにVercelにリンク済みです！

プロジェクト名: `crypto-bot`
オーナー: `shingo-arais-projects`

## 環境変数の設定手順

### 1. Vercelダッシュボードにアクセス

1. [https://vercel.com/dashboard](https://vercel.com/dashboard) にログイン
2. `crypto-bot` プロジェクトをクリック

### 2. 環境変数の設定

1. 上部メニューの **Settings** タブをクリック
2. 左側メニューの **Environment Variables** をクリック
3. 以下の変数を1つずつ追加：

#### 必須の環境変数

| 変数名                      | 値                                                                 | 環境                                          |
| --------------------------- | ------------------------------------------------------------------ | --------------------------------------------- |
| `SUPABASE_URL`              | `https://huuimmgmxtqigbjfpudo.supabase.co`                         | ✅ Production<br>✅ Preview<br>✅ Development |
| `SUPABASE_ANON_KEY`         | `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...` (現在の.envファイルの値) | ✅ Production<br>✅ Preview<br>✅ Development |
| `SUPABASE_SERVICE_ROLE_KEY` | **Supabaseダッシュボードから取得必要**                             | ✅ Production<br>✅ Preview<br>✅ Development |
| `JWT_SECRET`                | 強力なランダム文字列を生成                                         | ✅ Production<br>✅ Preview<br>✅ Development |
| `ENVIRONMENT`               | `production`                                                       | ✅ Production のみ                            |
| `LOG_LEVEL`                 | `INFO`                                                             | ✅ Production<br>✅ Preview<br>✅ Development |

### 3. SERVICE_ROLE_KEYの取得

**重要**: 現在の.envファイルのSERVICE_ROLE_KEYはanon keyと同じになっています。正しいservice_role keyを取得してください：

1. [Supabaseダッシュボード](https://supabase.com/dashboard) にアクセス
2. プロジェクトを選択
3. **Settings** → **API**
4. **service_role** (secret) の値をコピー（anon keyとは異なるはずです）

### 4. JWT_SECRETの生成

ターミナルで以下を実行して強力なJWT_SECRETを生成：

```bash
openssl rand -base64 32
```

### 5. 設定の確認

すべての環境変数を追加したら、Vercelダッシュボードで確認：

- 各変数が正しく設定されているか
- すべての環境（Production, Preview, Development）にチェックが入っているか

## 次のステップ

### 1. Supabaseでスキーマを実行

1. [Supabaseダッシュボード](https://supabase.com/dashboard) にアクセス
2. プロジェクトを選択
3. 左側メニューの **SQL Editor** をクリック
4. `database/supabase-schema.sql` の内容をコピーペースト
5. **Run** ボタンをクリックして実行

### 2. 接続テスト

環境変数の設定が完了したら、ローカルで接続テストを実行：

```bash
source venv/bin/activate  # 仮想環境を有効化
python test_supabase_connection.py
```

### 3. Vercelにデプロイ

成功したら、Vercelにデプロイ：

```bash
vercel --prod
```
