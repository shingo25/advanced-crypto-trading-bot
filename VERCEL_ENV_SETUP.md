# Vercel環境変数設定手順

## 🎯 Phase A個人モード機能の本番環境設定

### 必要な環境変数設定

以下の環境変数をVercel Dashboardまたは CLI で設定してください：

#### 1. バックエンド用環境変数
```
PERSONAL_MODE=true
PERSONAL_MODE_AUTO_LOGIN=true
PERSONAL_MODE_DEFAULT_USER=demo
PERSONAL_MODE_SKIP_LIVE_TRADING_AUTH=false
JWT_SECRET_KEY=your-secure-production-jwt-secret-32-chars
ENVIRONMENT=production
```

#### 2. フロントエンド用環境変数（NEXT_PUBLIC_プレフィックス必須）
```
NEXT_PUBLIC_PERSONAL_MODE=true
NEXT_PUBLIC_PERSONAL_MODE_AUTO_LOGIN=true
```

### 📱 Vercel Dashboard での設定方法

1. **https://vercel.com/dashboard** にアクセス
2. **advanced-crypto-trading-bot** プロジェクトを選択
3. **Settings** タブ → **Environment Variables** をクリック
4. 上記の環境変数を1つずつ追加
   - **Environment**: Production, Preview, Development （すべて選択）

### 💻 Vercel CLI での設定方法

```bash
# 1. プロジェクトディレクトリで実行
cd /Users/arata/Dev/advanced-crypto-trading-bot

# 2. 各環境変数を順次設定
vercel env add PERSONAL_MODE
# → "true" と入力
# → すべての環境を選択

vercel env add PERSONAL_MODE_AUTO_LOGIN
# → "true" と入力

vercel env add PERSONAL_MODE_DEFAULT_USER
# → "demo" と入力

vercel env add PERSONAL_MODE_SKIP_LIVE_TRADING_AUTH
# → "false" と入力

vercel env add JWT_SECRET_KEY
# → "your-secure-production-jwt-secret-32-chars" と入力

vercel env add ENVIRONMENT
# → "production" と入力（Production環境のみ）

vercel env add NEXT_PUBLIC_PERSONAL_MODE
# → "true" と入力

vercel env add NEXT_PUBLIC_PERSONAL_MODE_AUTO_LOGIN
# → "true" と入力
```

### 🔄 再デプロイ実行

環境変数設定後、再デプロイが必要です：

```bash
# PR #34 をマージしてmainブランチをデプロイ
git checkout main
git pull origin main
git push origin main

# または Vercel CLI で直接デプロイ
vercel --prod
```

### ✅ 動作確認

設定完了後、以下のURLで動作確認：

1. **個人モード設定確認**:
   ```
   https://your-vercel-domain.vercel.app/api/auth/personal-mode-info
   ```
   
   期待される結果:
   ```json
   {
     "personal_mode": true,
     "auto_login": true,
     "default_user": "demo",
     "skip_live_trading_auth": false,
     "available_users": ["demo"]
   }
   ```

2. **自動ログイン動作確認**:
   ```
   https://your-vercel-domain.vercel.app/
   ```
   
   期待される動作:
   - ログインページをスキップ
   - ダッシュボードに直接遷移

3. **API全体の動作確認**:
   ```
   https://your-vercel-domain.vercel.app/api/auth/health
   ```

### 🔒 セキュリティ注意事項

- **JWT_SECRET_KEY**: 本番環境では必ず強力なランダム文字列（32文字以上）を使用
- **個人モード**: 信頼できる環境でのみ有効化
- **ENVIRONMENT=production**: 本番環境でのみ設定

### 🐛 トラブルシューティング

- 環境変数が反映されない → 再デプロイを実行
- 自動ログインが動作しない → ブラウザのキャッシュをクリア
- API エラー → `/api/auth/health` でヘルスチェック確認

---

**設定完了後、Vercel URLでの動作確認をお願いします！**