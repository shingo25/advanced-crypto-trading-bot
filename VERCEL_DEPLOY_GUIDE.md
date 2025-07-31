# Vercel デプロイガイド

## 概要
このプロジェクトは、Next.jsフロントエンドとPython FastAPI バックエンドからなるモノレポ構成です。Vercelでの正しいデプロイ方法を説明します。

## プロジェクト構造
```
/
├── frontend/           # Next.js アプリケーション（App Router）
│   ├── src/app/       # ページとレイアウト
│   ├── package.json   # フロントエンド依存関係
│   └── next.config.js # Next.js設定
├── api/               # Python FastAPI
│   └── index.py       # 統合API
├── vercel.json        # Vercel設定
└── README.md
```

## Vercel設定手順

### 1. プロジェクト設定（Vercel UI）
Vercelダッシュボードで以下を設定：

1. **Settings** → **General** に移動
2. **Root Directory** を `frontend` に設定
3. **Framework Preset** を `Next.js` に設定
4. **Build Command** は `npm run build` のまま
5. **Output Directory** は `.next` のまま

### 2. 環境変数設定
Vercelダッシュボードで以下の環境変数を設定：

```bash
ENVIRONMENT=production
JWT_SECRET_KEY=prod-jwt-secret-key-vercel-crypto-trading-bot-32-chars-long
JWT_ALGORITHM=HS256
JWT_EXPIRATION=86400
USE_REAL_DATA=true
RATE_LIMIT_ENABLED=true
MAX_REQUESTS_PER_MINUTE=60
ENABLE_PRICE_STREAMING=false
```

### 3. デプロイ
1. GitHubリポジトリをVercelに接続
2. `main` ブランチからデプロイ
3. 自動デプロイが有効になることを確認

## 技術的詳細

### Next.js設定（frontend/next.config.js）
- `output: 'standalone'` - Vercel Functions対応
- `trailingSlash: true` - SEO最適化
- App Router使用（src/app/）

### API設定（vercel.json）
- Python 3.11ランタイム使用
- `/api/*` → `api/index.py` リライト設定
- CORS設定済み

### 認証システム
- JWT + httpOnly クッキー認証
- デモユーザー: `demo/demo`
- 自動ログイン機能搭載

## デバッグ方法

### 1. ビルドログ確認
Vercelダッシュボード → Deployments → 該当デプロイ → View Build Logs

### 2. 404エラーの対処法
- Root Directoryが `frontend` に設定されているか確認
- Next.jsのApp Routerが正しく設定されているか確認
- `src/app/page.tsx` が存在するか確認

### 3. API接続テスト
- `https://your-domain.vercel.app/api/health` でAPI疎通確認
- 認証テスト: `https://your-domain.vercel.app/api/auth/login`

## よくある問題

### Q: 404エラーが表示される
**A:** Root Directoryが正しく設定されていない可能性があります。Vercel UIで `frontend` に設定してください。

### Q: APIが動作しない
**A:** 環境変数が正しく設定されているか、`api/index.py` が正しくデプロイされているか確認してください。

### Q: 認証が機能しない
**A:** JWT_SECRET_KEYが設定されているか、httpOnlyクッキーが正しく設定されているか確認してください。

## 本番URL例
- フロントエンド: `https://your-project.vercel.app/`
- API: `https://your-project.vercel.app/api/health`
- ダッシュボード: `https://your-project.vercel.app/dashboard`

## サポート
問題が発生した場合は、Vercelのビルドログとブラウザのコンソールログを確認してください。