# 🚀 Getting Started - 5分で始める Advanced Crypto Trading Bot

このガイドでは、プロジェクトのセットアップから初回起動まで、最短で完了できる手順を説明します。

## 📋 前提条件

- **Node.js** v18以上
- **Python** 3.11以上
- **Git**
- **Supabase** アカウント（無料）
- **Vercel** アカウント（オプション）

## 🛠️ クイックスタート

### 1. リポジトリのクローン

```bash
git clone https://github.com/yourusername/advanced-crypto-trading-bot.git
cd advanced-crypto-trading-bot
```

### 2. 環境変数の設定

```bash
# .env.exampleをコピー
cp .env.example .env

# エディタで.envを開いて、以下を設定
# - SUPABASE_URL
# - SUPABASE_SERVICE_ROLE_KEY
# - JWT_SECRET (ランダムな文字列)
```

> 💡 **Supabase設定の詳細**: [SUPABASE_SETUP.md](./SUPABASE_SETUP.md)を参照

### 3. バックエンドのセットアップ

```bash
# Python仮想環境の作成
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 依存関係のインストール
pip install -r requirements.txt

# データベースの初期化
python -m backend.scripts.init_db

# バックエンドサーバーの起動
uvicorn backend.main:app --reload --port 8000
```

### 4. フロントエンドのセットアップ

新しいターミナルで：

```bash
# フロントエンドディレクトリへ移動
cd frontend

# 依存関係のインストール
npm install

# 開発サーバーの起動
npm run dev
```

### 5. アプリケーションへのアクセス

- **フロントエンド**: http://localhost:3000
- **バックエンドAPI**: http://localhost:8000
- **APIドキュメント**: http://localhost:8000/docs

## 🧪 動作確認

1. ブラウザで http://localhost:3000 を開く
2. 新規ユーザー登録を行う
3. ダッシュボードが表示されれば成功！

## 🐳 Docker を使った起動（オプション）

```bash
# Docker Composeで全サービスを起動
docker-compose up -d

# ログの確認
docker-compose logs -f
```

## 🚨 トラブルシューティング

### よくある問題と解決方法

1. **「ModuleNotFoundError: No module named 'pandas'」**

   ```bash
   pip install -r requirements.txt  # 依存関係の再インストール
   ```

2. **「SUPABASE_URLが設定されていません」**
   - `.env`ファイルが正しく設定されているか確認
   - 環境変数が読み込まれているか確認: `echo $SUPABASE_URL`

3. **ポート競合エラー**
   ```bash
   # 使用中のポートを確認
   lsof -i :3000  # Mac/Linux
   netstat -ano | findstr :3000  # Windows
   ```

## 📚 次のステップ

- **開発ガイド**: [DEVELOPMENT_GUIDE.md](./DEVELOPMENT_GUIDE.md)
- **アーキテクチャ**: [ARCHITECTURE.md](./ARCHITECTURE.md)
- **実装ロードマップ**: [ROADMAP.md](./ROADMAP.md)
- **APIリファレンス**: [API_REFERENCE.md](./API_REFERENCE.md)

## 💬 ヘルプとサポート

- **Issue**: [GitHub Issues](https://github.com/yourusername/advanced-crypto-trading-bot/issues)
- **Discussion**: [GitHub Discussions](https://github.com/yourusername/advanced-crypto-trading-bot/discussions)

---

準備完了！ 🎉 これで開発を始められます。
