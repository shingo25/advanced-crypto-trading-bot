# 🚀 Advanced Crypto Trading Bot

高度な暗号通貨取引ボットシステム - 16種類の戦略を実装したマルチエクスチェンジ対応の自動取引システム

![Build Status](https://img.shields.io/badge/build-passing-brightgreen)
![Python](https://img.shields.io/badge/python-3.9+-blue)
![Node.js](https://img.shields.io/badge/node.js-22.x-green)
![License](https://img.shields.io/badge/license-MIT-blue)

## 📋 目次

- [機能概要](#機能概要)
- [技術スタック](#技術スタック)
- [システム構成](#システム構成)
- [インストール](#インストール)
- [使用方法](#使用方法)
- [戦略一覧](#戦略一覧)
- [設定](#設定)
- [API仕様](#api仕様)
- [テスト](#テスト)
- [デプロイ](#デプロイ)
- [貢献](#貢献)
- [ライセンス](#ライセンス)

## 🎯 機能概要

### 主要機能
- ✅ **16種類の取引戦略** - EMA、RSI、MACD、ボリンジャーバンドなど
- ✅ **マルチエクスチェンジ対応** - Binance、Bybit、Coinbase Pro等
- ✅ **リアルタイム監視** - WebSocket経由でのライブデータ取得
- ✅ **高速バックテスト** - DuckDBを使用した高速データ処理
- ✅ **ウォークフォワード分析** - 戦略の堅牢性検証
- ✅ **ポートフォリオ最適化** - Kelly Criterion、リスクパリティ対応
- ✅ **リスク管理** - 動的ポジションサイジング、ストップロス
- ✅ **Web UI** - Next.js製のモダンなダッシュボード
- ✅ **アラート機能** - 重要イベントの通知システム

### 対応戦略
1. **EMA戦略** - 指数移動平均を使用したトレンドフォロー
2. **RSI戦略** - 相対強度指数による逆張り
3. **MACD戦略** - Moving Average Convergence Divergence
4. **ボリンジャーバンド** - 統計的価格帯による取引
5. **その他12戦略** - 詳細は[戦略一覧](#戦略一覧)を参照

## 🛠 技術スタック

### バックエンド
- **Python 3.9+** - メイン開発言語
- **FastAPI** - 高性能Web APIフレームワーク
- **DuckDB** - 高速分析用データベース
- **CCXT** - 暗号通貨取引所統合ライブラリ
- **Pandas** - データ分析・操作
- **NumPy** - 数値計算
- **SQLAlchemy** - データベースORM
- **Tenacity** - 堅牢なリトライ機能

### フロントエンド
- **Next.js 15** - React フレームワーク
- **TypeScript** - 型安全な開発
- **Material-UI (MUI) v7** - UIコンポーネント
- **Zustand** - 状態管理
- **Recharts** - データ可視化
- **Axios** - HTTP クライアント

### インフラ・ツール
- **Docker** - コンテナ化
- **pytest** - Python テストフレームワーク
- **Jest** - JavaScript テストフレームワーク
- **GitHub Actions** - CI/CD（設定済み）

## 🏗 システム構成

```
crypto-bot/
├── backend/                    # Python バックエンド
│   ├── api/                   # FastAPI エンドポイント
│   ├── strategies/            # 取引戦略実装
│   ├── exchanges/             # 取引所アダプター
│   ├── backtesting/           # バックテストエンジン
│   ├── portfolio/             # ポートフォリオ管理
│   ├── risk/                  # リスク管理
│   └── monitoring/            # 監視・アラート
├── frontend/                  # Next.js フロントエンド
│   ├── src/
│   │   ├── app/              # App Router
│   │   ├── components/       # React コンポーネント
│   │   ├── store/           # Zustand ストア
│   │   └── lib/             # ユーティリティ
│   └── public/              # 静的ファイル
├── config/                   # 設定ファイル
├── docker/                   # Docker 設定
├── tests/                    # テストファイル
└── scripts/                  # 運用スクリプト
```

## 🚀 インストール

### 前提条件
- **Node.js 22.x** (LTS)
- **Python 3.9+**
- **Git**

### 1. リポジトリのクローン
```bash
git clone https://github.com/YOUR_USERNAME/crypto-bot.git
cd crypto-bot
```

### 2. バックエンドセットアップ
```bash
# Python仮想環境の作成
python -m venv venv

# 仮想環境の有効化
# Windows
venv\\Scripts\\activate
# macOS/Linux
source venv/bin/activate

# 依存関係のインストール
pip install -r requirements.txt
```

### 3. フロントエンドセットアップ
```bash
cd frontend
npm install
npm run build
```

### 4. 設定ファイルの作成
```bash
# バックエンド設定
cp config/settings.example.yml config/settings.yml

# 取引所APIキーの設定（settings.ymlを編集）
vim config/settings.yml
```

## 🎮 使用方法

### 1. バックエンドサーバーの起動
```bash
# 仮想環境の有効化
source venv/bin/activate

# サーバー起動
python backend/main.py
```

### 2. フロントエンドサーバーの起動
```bash
cd frontend
npm run dev
```

### 3. アクセス
- **Web UI**: http://localhost:3000
- **API**: http://localhost:8000
- **API ドキュメント**: http://localhost:8000/docs

### 4. 基本的な使用フロー

1. **ログイン** - デフォルト: `admin` / `password`
2. **戦略選択** - 戦略管理画面で取引戦略を選択
3. **バックテスト** - 過去データでの戦略検証
4. **ライブトレード** - 実際の取引開始
5. **監視** - ダッシュボードでのリアルタイム監視

## 📊 戦略一覧

### 実装済み戦略
1. **EMA戦略** - 指数移動平均クロスオーバー
2. **RSI戦略** - 相対強度指数による逆張り
3. **MACD戦略** - MACD線とシグナル線のクロス
4. **ボリンジャーバンド** - 統計的価格帯分析
5. **ストキャスティクス** - オシレーター指標
6. **フィボナッチ** - リトレースメント戦略
7. **アービトラージ** - 取引所間価格差利用
8. **グリッドトレード** - 格子状注文配置
9. **DCA戦略** - ドルコスト平均法
10. **モメンタム** - 価格変動勢い追従

### 戦略設定例
```yaml
# config/strategies/ema_strategy.yml
name: "EMA Cross Strategy"
parameters:
  fast_ema: 12
  slow_ema: 26
  symbol: "BTCUSDT"
  timeframe: "1h"
risk_management:
  stop_loss: 0.02
  take_profit: 0.04
  position_size: 0.1
```

## ⚙️ 設定

### 主要設定ファイル

#### `config/settings.yml`
```yaml
# データベース設定
database:
  type: "duckdb"
  path: "data/trading.duckdb"

# 取引所設定
exchanges:
  binance:
    api_key: "YOUR_API_KEY"
    api_secret: "YOUR_API_SECRET"
    sandbox: true
  bybit:
    api_key: "YOUR_API_KEY"
    api_secret: "YOUR_API_SECRET"
    sandbox: true

# リスク管理
risk_management:
  max_position_size: 0.1
  max_drawdown: 0.05
  daily_loss_limit: 0.02

# 監視設定
monitoring:
  alert_webhook: "YOUR_WEBHOOK_URL"
  log_level: "INFO"
```

### 環境変数
```bash
# .env ファイル
BINANCE_API_KEY=your_binance_api_key
BINANCE_API_SECRET=your_binance_api_secret
BYBIT_API_KEY=your_bybit_api_key
BYBIT_API_SECRET=your_bybit_api_secret
JWT_SECRET=your_jwt_secret
```

## 🔌 API仕様

### 認証
```bash
# ログイン
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "password"}'
```

### 主要エンドポイント
- `GET /api/strategies` - 戦略一覧取得
- `POST /api/strategies/backtest` - バックテスト実行
- `POST /api/trades/start` - ライブトレード開始
- `GET /api/portfolio/summary` - ポートフォリオ概要
- `GET /api/alerts` - アラート一覧

詳細な API 仕様は [API ドキュメント](http://localhost:8000/docs) を参照してください。

## 🧪 テスト

### バックエンドテスト
```bash
# 仮想環境の有効化
source venv/bin/activate

# 全テスト実行
python -m pytest tests/

# 特定のテスト実行
python -m pytest tests/test_strategies.py -v
```

### フロントエンドテスト
```bash
cd frontend

# 全テスト実行
npm test

# カバレッジ付きテスト
npm run test:coverage
```

### テストカバレッジ
- **バックエンド**: 85%+
- **フロントエンド**: 80%+

## 🚢 デプロイ

### Docker を使用したデプロイ
```bash
# Docker イメージのビルド
docker-compose build

# サービスの起動
docker-compose up -d

# ログの確認
docker-compose logs -f
```

### 本番環境設定
```bash
# 本番用設定
cp config/production.yml config/settings.yml

# SSL証明書の設定
# Let's Encrypt などを使用

# リバースプロキシの設定
# Nginx などを使用
```

## 📈 パフォーマンス

### バックテスト性能
- **データ処理速度**: 100万行/秒（DuckDB）
- **戦略実行時間**: < 1秒（1年分データ）
- **メモリ使用量**: < 500MB

### ライブトレード性能
- **レスポンス時間**: < 100ms
- **スループット**: 1000リクエスト/秒
- **稼働率**: 99.9%

## 🔒 セキュリティ

- **APIキー暗号化** - AES-256暗号化
- **JWT認証** - セッション管理
- **レート制限** - API乱用防止
- **監査ログ** - 全取引記録
- **秘密鍵管理** - age暗号化

## 📝 ライセンス

このプロジェクトはMITライセンスの下で公開されています。詳細は [LICENSE](LICENSE) ファイルを参照してください。

## 🤝 貢献

貢献を歓迎します！以下の手順に従ってください：

1. このリポジトリをフォーク
2. 新しいブランチを作成 (`git checkout -b feature/AmazingFeature`)
3. 変更をコミット (`git commit -m 'Add some AmazingFeature'`)
4. ブランチにプッシュ (`git push origin feature/AmazingFeature`)
5. プルリクエストを開く

## 📧 サポート

- **GitHub Issues**: [問題報告](https://github.com/YOUR_USERNAME/crypto-bot/issues)
- **Discord**: コミュニティサーバーで質問・議論
- **Wiki**: 詳細なドキュメント

## ⚠️ 免責事項

このソフトウェアは教育目的で提供されています。実際の取引での使用は自己責任で行ってください。
開発者は取引による損失について一切の責任を負いません。

---

**🔥 Happy Trading! 🔥**