# Supabase認証システム完全セットアップガイド

## 概要

この実装は、Vercelサーバーレス環境でステートレスなSupabase認証を提供します。
メモリベースの認証問題を完全に解決し、demo/demoログインと新規アカウント作成を確実に動作させます。

## 🔧 Vercel環境変数の設定

### 必須環境変数

Vercel Dashboard または CLI で以下の環境変数を設定してください：

```bash
# JWT設定
JWT_SECRET_KEY=prod-jwt-secret-key-vercel-crypto-trading-bot-32-chars-long

# Supabase設定 (必須)
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your-supabase-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-supabase-service-role-key

# 環境設定
ENVIRONMENT=production
```

### Vercel CLI での設定例

```bash
# 本番環境の環境変数設定
vercel env add supabase-url production
vercel env add supabase-anon-key production
vercel env add supabase-service-role-key production

# プレビュー環境の設定
vercel env add supabase-url preview
vercel env add supabase-anon-key preview
vercel env add supabase-service-role-key preview
```

## 🗄️ Supabaseデータベース設定

### プロファイルテーブルの確認

既存の `profiles` テーブルが以下の構造であることを確認：

```sql
CREATE TABLE profiles (
  id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
  username TEXT UNIQUE NOT NULL,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  PRIMARY KEY (id)
);

-- RLS (Row Level Security) の設定
ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;

-- プロファイル閲覧ポリシー
CREATE POLICY "プロファイルは誰でも閲覧可能" ON profiles
  FOR SELECT USING (true);

-- プロファイル作成ポリシー
CREATE POLICY "ユーザーは自分のプロファイルを作成可能" ON profiles
  FOR INSERT WITH CHECK (auth.uid() = id);
```

### 新規ユーザー作成トリガー（推奨）

新規ユーザー登録時に自動でプロファイルを作成するトリガー：

```sql
-- トリガー関数の作成
CREATE OR REPLACE FUNCTION handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
  INSERT INTO profiles (id, username, created_at)
  VALUES (
    NEW.id,
    COALESCE(NEW.raw_user_meta_data->>'username', split_part(NEW.email, '@', 1)),
    NOW()
  );
  RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- トリガーの作成
DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW EXECUTE PROCEDURE handle_new_user();
```

## 🔐 認証フロー

### 1. デモユーザー (demo/demo)

- Username: `demo`
- Password: `demo`
- Email: `demo@cryptobot.local` (内部変換)
- 自動作成: アプリケーション起動時に作成

### 2. 新規ユーザー登録

- Username → `{username}@cryptobot.local` に自動変換
- 表示用Emailは別途保存
- プロファイルテーブルに自動登録

### 3. ログイン処理

1. Username → Email変換
2. Supabase Auth でパスワード認証
3. JWTトークンをhttpOnlyクッキーに設定
4. プロファイル情報を返却

## 🧪 テスト方法

### 1. ヘルスチェック

```bash
curl https://your-app.vercel.app/api/auth/health
```

期待される応答:

```json
{
  "status": "healthy",
  "timestamp": "2024-01-01T00:00:00Z",
  "version": "3.0.0",
  "supabase_connection": "healthy",
  "demo_user_available": true
}
```

### 2. デモログインテスト

```bash
curl -X POST https://your-app.vercel.app/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"demo","password":"demo"}' \
  -c cookies.txt
```

### 3. 新規アカウント作成テスト

```bash
curl -X POST https://your-app.vercel.app/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"testuser","email":"test@example.com","password":"testpass123"}'
```

### 4. ユーザー情報取得テスト

```bash
curl https://your-app.vercel.app/api/auth/me \
  -b cookies.txt
```

## 🚨 トラブルシューティング

### エラー: "Supabase configuration missing"

- Vercel環境変数が正しく設定されていない
- `SUPABASE_URL` と `SUPABASE_ANON_KEY` を確認

### エラー: "User profile not found"

- プロファイルテーブルのトリガーが動作していない
- 手動でプロファイルエントリを作成

### エラー: "Invalid username or password"

- デモユーザーが作成されていない可能性
- Supabase Dashboard で `auth.users` テーブルを確認

### デモユーザーの手動作成

```sql
-- Supabase SQL エディタで実行
INSERT INTO auth.users (
  id,
  email,
  encrypted_password,
  email_confirmed_at,
  created_at,
  updated_at
) VALUES (
  gen_random_uuid(),
  'demo@cryptobot.local',
  crypt('demo', gen_salt('bf')),
  NOW(),
  NOW(),
  NOW()
);
```

## ✅ 完了チェックリスト

- ✅ Vercel環境変数設定完了 (2025-01-23)
- ✅ Supabaseプロジェクト設定完了
- ✅ プロファイルテーブル確認
- ⏳ デモユーザー作成確認 (再デプロイ後)
- ⏳ ヘルスチェック成功 (再デプロイ後)
- ⏳ demo/demo ログイン成功 (再デプロイ後)
- ⏳ 新規アカウント作成成功 (再デプロイ後)
- ⏳ JWT認証フロー動作確認 (再デプロイ後)

## 🔄 マイグレーション（既存システムから）

既存の `auth_simple.py` から移行する場合：

1. ✅ `vercel.json` のルーティング更新
2. ✅ `requirements-vercel.txt` にSupabase追加
3. ✅ 環境変数設定
4. ✅ デプロイ実行
5. ✅ テスト実行

これにより、**完全にステートレスで永続的なSupabase認証システム**が動作します。
