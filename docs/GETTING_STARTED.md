# Getting Started - Advanced Crypto Trading Bot

新しい開発者向けのクイックスタートガイドです。このプロジェクトに参加してSupabase統合済みの暗号通貨取引ボットの開発に貢献しましょう！

---

## 📋 前提条件

- **Node.js**: v18.0.0 以上
- **Python**: v3.12 以上  
- **Git**: 最新版
- **VS Code**: 推奨（拡張機能含む）

---

## 🚀 セットアップ手順

### 1. リポジトリのクローン

```bash
git clone https://github.com/yourusername/advanced-crypto-trading-bot.git
cd advanced-crypto-trading-bot
```

### 2. 環境変数の設定

```bash
# .env ファイルを作成
cp .env.example .env

# .env ファイルを編集（必須項目）
nano .env
```

**必須環境変数**:
```env
# Supabase 設定
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key

# JWT 設定
JWT_SECRET=your-super-secret-jwt-key-here
JWT_ALGORITHM=HS256
JWT_EXPIRATION_HOURS=24

# 管理者設定
ADMIN_USERNAME=admin
ADMIN_PASSWORD=change_this_password

# 環境設定
ENVIRONMENT=development
LOG_LEVEL=INFO
```

### 3. Python バックエンドのセットアップ

```bash
# Python 仮想環境の作成
python3 -m venv venv

# 仮想環境の有効化
source venv/bin/activate  # macOS/Linux
# または
venv\Scripts\activate     # Windows

# 依存関係のインストール
pip install -r requirements.txt
```

### 4. Node.js フロントエンドのセットアップ

```bash
# frontend ディレクトリに移動
cd frontend

# 依存関係のインストール
npm install

# フロントエンドディレクトリから戻る
cd ..
```

### 5. Supabase データベースのセットアップ

```bash
# Supabase CLI のインストール（初回のみ）
npm install -g supabase

# データベーススキーマの適用
psql -h db.your-project.supabase.co -U postgres -d postgres -f database/supabase-schema.sql
```

または Supabase Dashboard の SQL Editor で `database/supabase-schema.sql` の内容を実行。

### 6. 管理者ユーザーの作成

```bash
# 仮想環境が有効化されていることを確認
source venv/bin/activate

# 管理者ユーザー作成スクリプトの実行
python setup_admin_user.py
```

---

## 🧪 動作確認

### バックエンド API テスト

```bash
# 仮想環境で実行
source venv/bin/activate

# 統合テストの実行
python test_backend_deployment.py

# 期待される出力:
# 🎉 バックエンドAPIはデプロイ準備完了！
# ✅ デプロイ前テスト完了
```

### フロントエンド開発サーバー起動

```bash
cd frontend
npm run dev

# http://localhost:3000 でアクセス
# ログイン: admin / change_this_password
```

### バックエンド開発サーバー起動（オプション）

```bash
# 仮想環境で実行
source venv/bin/activate

# 開発サーバー起動
python start_backend.py

# http://localhost:8000 でアクセス
# API ドキュメント: http://localhost:8000/docs
```

---

## 🛠️ 開発環境の設定

### VS Code 推奨拡張機能

```json
{
  "recommendations": [
    "ms-python.python",
    "ms-python.black-formatter", 
    "bradlc.vscode-tailwindcss",
    "esbenp.prettier-vscode",
    "ms-vscode.vscode-typescript-next",
    "ms-toolsai.jupyter"
  ]
}
```

### pre-commit hooks 設定（推奨）

```bash
# pre-commit のインストール
pip install pre-commit

# フックの設定
pre-commit install
```

---

## 📁 プロジェクト構造の理解

```
crypto-bot/
├── backend/                 # FastAPI バックエンド
│   ├── main.py             # アプリケーションエントリーポイント
│   ├── core/               # コア機能
│   │   ├── config.py       # 設定管理
│   │   ├── security.py     # 認証・セキュリティ
│   │   ├── database.py     # データベース層
│   │   └── supabase_db.py  # Supabase 接続管理
│   ├── models/             # データモデル
│   │   ├── user.py         # ユーザー関連
│   │   └── trading.py      # 取引関連
│   └── api/                # API エンドポイント
│       ├── auth.py         # 認証 API ✅
│       ├── strategies.py   # 戦略 API ✅
│       ├── trades.py       # 取引 API 🔄
│       └── backtest.py     # バックテスト API 🔄
├── frontend/               # Next.js フロントエンド
│   ├── src/
│   │   ├── app/           # App Router
│   │   ├── components/    # React コンポーネント
│   │   ├── lib/          # ユーティリティ
│   │   └── store/        # 状態管理
│   └── package.json
├── database/               # データベース関連
│   └── supabase-schema.sql # スキーマ定義
├── docs/                   # ドキュメント
├── PROJECT_STATUS.md       # 実装状況
├── ROADMAP.md             # 開発計画
└── vercel.json            # デプロイ設定
```

---

## 🧩 開発ワークフロー

### 1. 新機能の開発

```bash
# 新しいブランチを作成
git checkout -b feature/your-feature-name

# 開発...
# テスト...

# コミット
git add .
git commit -m "Add: your feature description"

# プッシュ
git push origin feature/your-feature-name

# GitHub でプルリクエストを作成
```

### 2. テスト実行

```bash
# バックエンドテスト
source venv/bin/activate
python -m pytest tests/  # 今後実装予定

# フロントエンドテスト  
cd frontend
npm test

# 統合テスト
python test_backend_deployment.py
```

### 3. デバッグとログ

```bash
# ログファイルの確認
tail -f logs/crypto_bot_$(date +%Y%m%d).log

# Supabase 接続テスト
python test_supabase_connection.py

# 認証テスト
python test_supabase_auth.py
```

---

## 🎯 初心者向けタスク

新しく参加された方におすすめのタスク：

### 簡単（1-2時間）
- [ ] ドキュメントの誤字修正
- [ ] フロントエンドの UI 改善
- [ ] テストケースの追加
- [ ] ログメッセージの改善

### 中級（半日-1日）
- [ ] 新しい API エンドポイントの実装
- [ ] データベースクエリの最適化
- [ ] エラーハンドリングの改善
- [ ] UI コンポーネントの作成

### 上級（数日-1週間）
- [ ] 取引所 API 連携の実装
- [ ] リアルタイム価格配信機能
- [ ] バックテスト機能の拡張
- [ ] セキュリティ機能の強化

---

## 📚 学習リソース

### 技術スタック
- **FastAPI**: https://fastapi.tiangolo.com/
- **Next.js**: https://nextjs.org/docs
- **Supabase**: https://supabase.com/docs
- **Tailwind CSS**: https://tailwindcss.com/docs

### 暗号通貨・取引
- **CCXT**: https://ccxt.readthedocs.io/
- **TradingView**: https://www.tradingview.com/
- **CoinGecko API**: https://www.coingecko.com/en/api

---

## 🆘 よくある問題と解決法

### Supabase 接続エラー

```bash
# 環境変数の確認
echo $SUPABASE_URL
echo $SUPABASE_SERVICE_ROLE_KEY

# 接続テスト
python test_supabase_connection.py
```

### Python 依存関係エラー

```bash
# 仮想環境の再作成
rm -rf venv
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### フロントエンド ビルドエラー

```bash
cd frontend
rm -rf node_modules package-lock.json
npm install
npm run build
```

### 認証エラー

```bash
# 管理者ユーザーの再作成
python setup_admin_user.py

# 認証テスト
python test_supabase_auth.py
```

---

## 🤝 サポートとコミュニティ

- **Issues**: GitHub Issues で質問・バグ報告
- **Discussions**: GitHub Discussions で議論
- **Code Review**: プルリクエストでコードレビュー

新しい開発者歓迎！質問があれば遠慮なく GitHub Issues で聞いてください 🚀

---

**次のステップ**: [ROADMAP.md](../ROADMAP.md) で今後の開発計画を確認しましょう！