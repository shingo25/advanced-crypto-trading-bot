# 🚀 Vercel本番環境セットアップガイド

## 📋 概要

このガイドでは、暗号通貨取引ボットをVercel本番環境で動作させるための完全なセットアップ手順を説明します。

---

## 🎯 設定完了後の機能

✅ **フルスタック動作**: フロントエンド + バックエンドAPI
✅ **リアルタイム取引**: デモモード・本番モード切り替え可能
✅ **35個のAPI**: Phase3機能すべて利用可能
✅ **セキュリティ強化**: 本番レベルのセキュリティ対策
✅ **自動スケーリング**: Vercelの自動スケーリング機能

---

## 🔧 1. Vercel設定ファイル更新

**すでに完了済み**: `vercel.json`が更新されています

```json
{
  "version": 2,
  "functions": {
    "backend/main.py": {
      "runtime": "python3.9",
      "maxDuration": 30
    }
  },
  "rewrites": [
    {
      "source": "/api/(.*)",
      "destination": "/backend/main.py"
    }
  ]
}
```

---

## 🌐 2. Vercelダッシュボード設定手順

### Step 1: プロジェクト設定

1. [Vercel Dashboard](https://vercel.com/dashboard)にログイン
2. プロジェクトを選択
3. **Settings** → **Environment Variables**に移動

### Step 2: 必須環境変数の設定

以下の環境変数を**すべて**設定してください：

#### 🔐 セキュリティ設定

```bash
# JWT認証（必須）
JWT_SECRET_KEY=<openssl rand -hex 32で生成>
ENCRYPTION_KEY=<openssl rand -hex 32で生成>

# CORS設定
ALLOWED_ORIGINS=https://your-vercel-app.vercel.app
```

#### 🗄️ データベース設定

```bash
# Supabase（必須）
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your-supabase-anon-key
SUPABASE_SERVICE_KEY=your-supabase-service-role-key
DATABASE_URL=postgresql://postgres:[PASSWORD]@[HOST]:[PORT]/postgres

# Redis（推奨）
REDIS_URL=redis://your-redis-provider.com:6379
```

#### 📊 取引設定

```bash
# 取引モード
ENABLE_REAL_TRADING=false  # 最初はfalse、テスト完了後にtrue
TRADING_MODE=demo
DEFAULT_INITIAL_CAPITAL=100000.0

# Binance API（本番取引時）
BINANCE_API_KEY=your-binance-api-key
BINANCE_SECRET_KEY=your-binance-secret-key
BINANCE_TESTNET=true  # 最初はtrue、本番時にfalse
```

#### 🔒 セキュリティ強化

```bash
# レート制限
RATE_LIMIT_ENABLED=true
MAX_REQUESTS_PER_MINUTE=60

# 運用設定
ENVIRONMENT=production
LOG_LEVEL=INFO
```

### Step 3: フロントエンド環境変数

```bash
# APIエンドポイント
NEXT_PUBLIC_API_URL=https://your-vercel-app.vercel.app
NEXT_PUBLIC_WS_URL=wss://your-vercel-app.vercel.app
```

---

## 🗃️ 3. データベースセットアップ

### Supabase設定

1. [Supabase Dashboard](https://supabase.com/dashboard)でプロジェクト作成
2. **Settings** → **Database** → **Connection string**をコピー
3. Vercelの環境変数に設定

### Redis設定（推奨）

1. [Upstash](https://upstash.com/) または [Railway](https://railway.app/)でRedisインスタンス作成
2. 接続URLをVercelの環境変数に設定

---

## 🔐 4. セキュリティキー生成

以下のコマンドで安全なキーを生成：

```bash
# JWT秘密鍵生成
openssl rand -hex 32

# 暗号化キー生成
openssl rand -hex 32
```

**⚠️ 重要**: 生成されたキーは安全に保管し、Vercelの環境変数に設定してください。

---

## 🚀 5. デプロイ手順

### Step 1: 環境変数設定確認

- [ ] JWT_SECRET_KEY設定済み
- [ ] SUPABASE_URL設定済み
- [ ] ALLOWED_ORIGINS設定済み
- [ ] ENABLE_REAL_TRADING=false設定済み

### Step 2: デプロイ実行

```bash
# Vercel CLIの場合
npx vercel --prod

# GitHubプッシュの場合（自動デプロイ）
git push origin main
```

### Step 3: デプロイ確認

1. **フロントエンド**: `https://your-app.vercel.app`にアクセス
2. **バックエンドAPI**: `https://your-app.vercel.app/api/health`にアクセス
3. **認証テスト**: ログイン機能を確認

---

## 🧪 6. 動作確認チェックリスト

### 基本機能確認

- [ ] フロントエンド表示 ✅
- [ ] ログイン・ログアウト ✅
- [ ] ダッシュボード表示 ✅
- [ ] API応答 ✅

### Phase3機能確認

- [ ] 戦略管理（RSI、MACD、Bollinger）✅
- [ ] ポートフォリオ管理 ✅
- [ ] リスク管理 ✅
- [ ] アラートシステム ✅

### セキュリティ確認

- [ ] JWT認証動作 ✅
- [ ] CORS設定適用 ✅
- [ ] レート制限動作 ✅
- [ ] セキュリティヘッダー適用 ✅

---

## 🎛️ 7. 本番取引の有効化

**⚠️ 十分なテスト完了後のみ実行**

### Step 1: 取引所API設定

1. Binance/ByBitでAPI キー生成
2. テストネット環境でテスト実行
3. 正常動作確認後、本番API設定

### Step 2: 環境変数更新

```bash
# 本番取引有効化
ENABLE_REAL_TRADING=true
TRADING_MODE=live
BINANCE_TESTNET=false
```

### Step 3: リスク管理確認

- [ ] ストップロス機能確認
- [ ] ポジションサイズ制限確認
- [ ] リスク管理システム確認

---

## 🚨 8. トラブルシューティング

### よくある問題と解決法

#### 問題1: APIが動作しない

**原因**: 環境変数が未設定
**解決**: Vercelダッシュボードで必須環境変数を確認

#### 問題2: ログインできない

**原因**: JWT_SECRET_KEYが未設定または間違い
**解決**: 正しいJWT_SECRET_KEYを設定してリデプロイ

#### 問題3: データベース接続エラー

**原因**: Supabase設定が間違い
**解決**: SUPABASE_URLとキーを再確認

#### 問題4: CORS エラー

**原因**: ALLOWED_ORIGINSが間違い
**解決**: 正しいVercelドメインを設定

### ログ確認方法

```bash
# Vercel CLI でログ確認
npx vercel logs

# Vercel Dashboard
Functions → View Function Logs
```

---

## 📈 9. パフォーマンス最適化

### 推奨設定

```bash
# 本番環境最適化
ENVIRONMENT=production
LOG_LEVEL=INFO
ENABLE_PERFORMANCE_MONITORING=true
```

### モニタリング

- Vercel Analytics有効化
- Sentry エラー追跡設定（オプション）
- データベースパフォーマンス監視

---

## 🔄 10. 継続的メンテナンス

### 定期確認項目

- [ ] セキュリティキーローテーション（月1回）
- [ ] バックアップ確認（週1回）
- [ ] パフォーマンス確認（日1回）
- [ ] ログ確認（日1回）

### アップデート手順

1. 開発環境でテスト
2. Staging環境での検証
3. 本番環境への段階的デプロイ

---

## 📞 サポート

### 問題が発生した場合

1. このガイドのトラブルシューティングを確認
2. Vercelログを確認
3. 設定値を再確認
4. 必要に応じて開発チームに連絡

---

**🎊 設定完了後**: 本格的な暗号通貨自動取引システムとして利用可能になります！

**最終更新**: 2025年7月20日
