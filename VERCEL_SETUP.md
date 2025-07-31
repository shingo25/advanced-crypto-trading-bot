# Vercel環境設定ガイド

## 必須環境変数の設定

Vercel Dashboardで以下の環境変数を設定してください：

### 1. JWT認証設定
```bash
# 秘密鍵（32文字以上のランダム文字列）
JWT_SECRET_KEY=your-secure-random-32-char-secret-key-here

# JWT設定
JWT_ALGORITHM=HS256
JWT_EXPIRATION=86400
```

### 2. 環境設定
```bash
ENVIRONMENT=production
NODE_ENV=production
```

### 3. Vercel CLI での設定方法
```bash
# JWT秘密鍵を安全に設定
vercel env add JWT_SECRET_KEY production
# 入力: your-secure-random-32-char-secret-key-here
```

## テスト手順

### 1. ヘルスチェック
```bash
curl https://your-app.vercel.app/api/auth/health
```

### 2. demo/demo ログインテスト
```bash
curl -X POST https://your-app.vercel.app/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"demo","password":"demo"}'
```

### 3. 新規アカウント作成テスト
```bash
curl -X POST https://your-app.vercel.app/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"testuser","email":"test@example.com","password":"testpass123"}'
```

## トラブルシューティング

### よくある問題
1. **404 エラー**: APIルーティング設定を確認
2. **認証エラー**: JWT_SECRET_KEY の設定を確認
3. **CORS エラー**: 許可されたオリジンを確認

### デバッグ情報の確認
ヘルスチェックエンドポイントで以下の情報を確認できます：
- 環境設定
- エンドポイント一覧
- デモユーザーの可用性
