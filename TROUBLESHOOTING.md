# 🔧 トラブルシューティングガイド

## 個人モード自動ログインが動作しない場合

### 1. 環境変数の確認

Vercel Dashboardで以下の環境変数が設定されているか確認：

**必須の環境変数**:
- `PERSONAL_MODE` = `true`
- `PERSONAL_MODE_AUTO_LOGIN` = `true`
- `NEXT_PUBLIC_PERSONAL_MODE` = `true`
- `NEXT_PUBLIC_PERSONAL_MODE_AUTO_LOGIN` = `true`
- `JWT_SECRET_KEY` = (32文字以上のランダム文字列)

### 2. デプロイメントの再実行

環境変数を設定/変更した後は、必ず再デプロイが必要です：

**Vercel Dashboard から**:
1. Deployments タブ
2. 最新のデプロイメントの "..." メニュー
3. "Redeploy" をクリック
4. "Use existing Build Cache" のチェックを**外す**

### 3. ブラウザキャッシュのクリア

**Chrome/Edge**:
- Ctrl+Shift+R (Windows) / Cmd+Shift+R (Mac)
- または Developer Tools → Network → "Disable cache" にチェック

### 4. APIエンドポイントの直接確認

```bash
# cURLで確認
curl https://your-domain.vercel.app/api/auth/personal-mode-info

# ブラウザで確認
https://your-domain.vercel.app/api/auth/personal-mode-info
```

### 5. コンソールエラーの確認

ブラウザのDeveloper Tools → Console でエラーを確認：
- CORS エラー → 環境変数 `ALLOWED_ORIGINS` の確認
- 401 Unauthorized → JWT_SECRET_KEY の設定確認
- Network Error → APIエンドポイントの存在確認

### 6. Vercel Function ログの確認

Vercel Dashboard → Functions タブでエラーログを確認：
- `api/auth_simple.py` のログを確認
- エラーメッセージから原因を特定

### 7. 環境変数のスコープ確認

Vercel Dashboardで環境変数が正しいスコープに設定されているか確認：
- Production ✓
- Preview ✓
- Development ✓

### 8. .env ファイルの同期

ローカル開発環境の場合：
```bash
vercel env pull .env.local
```

## それでも解決しない場合

1. **GitHub Issue を作成**: 
   https://github.com/shingo25/advanced-crypto-trading-bot/issues

2. **以下の情報を提供**:
   - エラーメッセージ（Console、Network）
   - `/api/auth/health` の出力
   - `/api/auth/personal-mode-info` の出力
   - ブラウザとバージョン
   - Vercel デプロイメントURL

3. **一時的な回避策**:
   - 通常のログイン（demo/demo）を使用
   - 環境変数 `PERSONAL_MODE=false` に設定して通常モードで運用