# 🚀 Personal Crypto Trading Bot

**個人利用最適化された暗号通貨取引分析プラットフォーム**

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.9+-blue.svg)
![Next.js](https://img.shields.io/badge/next.js-15.4.3-black.svg)
![FastAPI](https://img.shields.io/badge/fastapi-latest-green.svg)
![Vercel](https://img.shields.io/badge/deployment-vercel-black.svg)

現代的な技術スタックで構築された、個人利用に最適化された暗号通貨取引分析ツール。認証機能を排除し、シンプルで高速な個人用ダッシュボードを提供します。

## 🎯 特徴

- **🔐 認証フリー**: 個人利用に最適化、面倒な認証手続き不要
- **⚡ 高速表示**: Next.js 15 + Static Export による瞬時のページロード
- **🎨 モダンUI**: Material-UI v7 による美しい暗号通貨ダッシュボード
- **☁️ Serverless Ready**: Vercel完全対応、ワンクリックデプロイ
- **🏗️ 現代的アーキテクチャ**: src/レイアウト + 型安全なTypeScript
- **🧪 高品質**: 包括的テストスイート + CI/CDパイプライン

## 🛠️ 技術スタック

### Frontend
- **Next.js 15.4.3** - React フレームワーク (Static Export)
- **TypeScript** - 型安全な開発
- **Material-UI v7** - デザインシステム
- **Zustand** - 軽量状態管理

### Backend
- **FastAPI** - Python Web フレームワーク
- **Mangum** - Vercel Serverless Functions対応
- **pytest** - テストフレームワーク

### Infrastructure
- **Vercel** - デプロイプラットフォーム
- **GitHub Actions** - CI/CDパイプライン
- **Docker** - ローカル開発環境

## 📁 プロジェクト構造

```
/
├── src/
│   ├── backend/              # Python FastAPI backend
│   │   ├── api/             # API endpoints
│   │   ├── core/            # Core utilities
│   │   └── models/          # Data models
│   └── vercel_api/          # Vercel Serverless Functions
│       ├── index.py         # Main API handler
│       └── health.py        # Health check
├── frontend/                 # Next.js application
│   ├── src/
│   │   ├── app/             # App Router pages
│   │   ├── components/      # React components
│   │   └── store/           # Zustand stores
│   └── public/              # Static assets
├── requirements/             # Python dependencies
│   ├── requirements.txt     # Base dependencies
│   ├── requirements-ci.txt  # CI environment
│   └── requirements-dev.txt # Development
├── tests/                   # Test suite
├── docs/                    # Documentation
└── config/                  # Configuration files
```

## 🚀 セットアップ

### 前提条件

- **Node.js** 20.x以上
- **Python** 3.9以上
- **npm** または **yarn**

### 1. リポジトリのクローン

```bash
git clone https://github.com/your-username/advanced-crypto-trading-bot.git
cd advanced-crypto-trading-bot
```

### 2. フロントエンド環境構築

```bash
cd frontend
npm install
npm run dev
```

フロントエンドが `http://localhost:3000` で起動します。

### 3. バックエンド環境構築

```bash
# Python仮想環境作成
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 依存関係インストール
pip install -r requirements/requirements-dev.txt
```

### 4. 環境変数設定

```bash
cp .env.example .env
# .envファイルを編集（必要に応じて）
```

## 💻 開発コマンド

### フロントエンド

```bash
cd frontend

# 開発サーバー起動
npm run dev

# ビルド
npm run build

# コード整形
npm run format

# Linter実行
npm run lint

# テスト実行
npm test
```

### バックエンド

```bash
# テスト実行
pytest

# カバレッジ付きテスト
pytest --cov=src.backend

# コード整形
ruff format src/backend/

# Linter実行
ruff check src/backend/
```

### Docker

```bash
# 全サービス起動
docker-compose up -d

# ログ確認
docker-compose logs -f

# サービス停止
docker-compose down
```

## 🌐 デプロイ

### Vercel デプロイ

1. **Vercelアカウント連携**
   ```bash
   npx vercel
   ```

2. **環境変数設定**
   Vercel Dashboardで以下を設定：
   ```
   ENVIRONMENT=production
   ```

3. **自動デプロイ**
   - mainブランチへのプッシュで自動デプロイ
   - Pull Request作成でプレビューデプロイ

### 手動デプロイ

```bash
# フロントエンドビルド
cd frontend && npm run build

# Vercel CLI でデプロイ
npx vercel --prod
```

## 📊 機能概要

### ダッシュボード
- 🎯 **ポートフォリオ概要**: 保有資産の一目瞭然の表示
- 📈 **パフォーマンスチャート**: 時系列での成績可視化
- 💹 **価格情報**: 主要暗号通貨のリアルタイム価格
- 📊 **取引履歴**: 過去の取引記録の詳細表示

### API エンドポイント
- `GET /api/` - システム情報
- `GET /api/health` - ヘルスチェック
- `GET /api/prices` - 暗号通貨価格情報
- `GET /api/portfolio` - ポートフォリオ情報
- `GET /api/trades` - 取引履歴

### 特徴的な実装
- **認証フリー設計**: 個人利用での利便性を最大化
- **モックデータ対応**: 外部API不要で即座にデモ動作
- **レスポンシブデザイン**: デスクトップ・モバイル完全対応
- **型安全性**: TypeScript + Python型ヒントによる堅牢性

## 🧪 テスト

### テスト実行

```bash
# フロントエンドテスト
cd frontend && npm test

# バックエンドテスト
pytest

# 全テスト実行（CI/CDと同じ）
pytest tests/ -v --cov=src.backend
```

### テストカバレッジ

- **Backend**: 10%以上（pytest-cov）
- **Frontend**: Jest + React Testing Library
- **CI/CD**: GitHub Actions で自動実行

## 📚 ドキュメント

- [📖 API Reference](docs/API_REFERENCE.md) - API仕様書
- [🏗️ Architecture](docs/ARCHITECTURE.md) - システム設計
- [🚀 Development Guide](docs/DEVELOPMENT.md) - 開発ガイド
- [📊 Database Schema](docs/DATABASE_SCHEMA.md) - データベース設計

## 🔧 トラブルシューティング

### よくある問題

**Q: フロントエンドが起動しない**
```bash
cd frontend
rm -rf node_modules package-lock.json
npm install
```

**Q: バックエンドテストが失敗する**
```bash
pip install -r requirements/requirements-test.txt
pytest --verbose
```

**Q: Vercelデプロイが失敗する**
- `vercel.json`のパス設定を確認
- 環境変数が正しく設定されているか確認

## 🤝 貢献

1. このリポジトリをフォーク
2. フィーチャーブランチを作成 (`git checkout -b feature/amazing-feature`)
3. 変更をコミット (`git commit -m 'Add amazing feature'`)
4. ブランチにプッシュ (`git push origin feature/amazing-feature`)
5. Pull Requestを作成

## 📄 ライセンス

このプロジェクトは [MIT License](LICENSE) の下で公開されています。

---

**🚀 Ready to explore crypto trading? Start with `npm run dev` and happy coding!**