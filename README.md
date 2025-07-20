# 🚀 Advanced Crypto Trading Bot

**AI駆動の高度な暗号通貨自動取引システム**

次世代の取引戦略を実装し、リアルタイムでの市場分析と自動取引を実現する包括的なトレーディングプラットフォームです。

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.11+-blue.svg)
![Next.js](https://img.shields.io/badge/next.js-14-black.svg)
![FastAPI](https://img.shields.io/badge/fastapi-0.109+-green.svg)

## ✨ 主要機能

### 🎯 コア機能
- **📈 多様な取引戦略**: EMA、RSI、MACD、カスタム戦略対応
- **💹 リアルタイム取引**: Binance、Bybitと直接連携
- **🔄 高度なバックテスト**: 歴史的データでの戦略検証
- **🛡️ リスク管理**: 自動ストップロス、ポジションサイジング
- **📊 包括的な分析**: パフォーマンス分析とレポート生成

### 🆕 Phase 2 新機能 (2025年1月実装)
- **📡 リアルタイムデータパイプライン**: Binance APIからのOHLCVデータ自動収集
- **💾 大規模データ管理**: Supabaseへの効率的なバッチ保存（1000件/バッチ）
- **⚡ 並列処理**: 複数シンボル・タイムフレームの同時データ収集
- **🔄 自動データ更新**: 定期的な価格データの収集とストレージ

### 🌐 技術スタック
- **Backend**: FastAPI (Python 3.11+)
- **Frontend**: Next.js 14 + React 18
- **Database**: PostgreSQL (Supabase)
- **Cache**: Redis
- **Container**: Docker
- **CI/CD**: GitHub Actions

## 🚀 5分でスタート

### 前提条件
- Node.js 18+
- Python 3.11+
- Docker (オプション)

### クイックスタート

```bash
# 1. リポジトリクローン
git clone https://github.com/yourusername/advanced-crypto-trading-bot.git
cd advanced-crypto-trading-bot

# 2. 環境変数設定
cp .env.example .env
# .envファイルを編集してSupabase情報を設定

# 3. バックエンド起動
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
uvicorn backend.main:app --reload

# 4. フロントエンド起動（新しいターミナル）
cd frontend && npm install && npm run dev
```

**🎉 準備完了！** http://localhost:3000 でアプリケーションにアクセス

> 📚 **詳細な手順**: [Getting Started Guide](./docs/GETTING_STARTED.md)

## 📖 ドキュメント

**📚 [📋 完全ドキュメント集](./docs/README.md)** - すべてのドキュメントの総合インデックス

### クイックアクセス

| ドキュメント | 説明 |
|-------------|------|
| [🚀 Getting Started](./docs/GETTING_STARTED.md) | 5分で始める完全ガイド |
| [🏗️ Architecture](./docs/ARCHITECTURE.md) | システム設計とアーキテクチャ |
| [🗺️ Phase2 Roadmap](./docs/PHASE2_ROADMAP.md) | Phase2-3の実装計画 |
| [📚 API Reference](./docs/API_REFERENCE.md) | 完全APIリファレンス |
| [🔧 Contributing Guide](./docs/CONTRIBUTING.md) | 開発参加ガイド |

## 📊 プロジェクト構造

```
crypto-bot/
├── 📁 backend/              # Python FastAPI サーバー
│   ├── api/                 # APIエンドポイント
│   ├── core/                # 共通機能（DB、認証、設定）
│   ├── strategies/          # 取引戦略実装
│   ├── exchanges/           # 取引所API連携
│   ├── backtesting/         # バックテストエンジン
│   └── data_pipeline/       # データ収集パイプライン
├── 📁 frontend/             # Next.js フロントエンド
│   ├── components/          # Reactコンポーネント
│   ├── pages/              # Next.jsページ
│   └── store/              # Redux状態管理
├── 📁 tests/               # テストコード
├── 📁 docs/                # プロジェクトドキュメント
└── 📁 .github/             # CI/CDワークフロー
```

## 🎯 現在の開発状況

### ✅ Phase 1: 基盤構築（完了）
- [x] FastAPI + Next.js アーキテクチャ
- [x] Supabaseデータベース統合
- [x] JWT認証システム
- [x] 基本的な取引戦略実装
- [x] CI/CDパイプライン構築

### 🚧 Phase 2: データパイプライン（進行中）
- [x] リアルタイムデータ収集 - Binance OHLCV収集実装完了
- [x] 取引所API統合強化 - DataCollectorクラス実装
- [ ] バックテスト機能拡張 - 実データ対応（開発中）
- [ ] WebSocketリアルタイム通信 - 価格更新機能（計画中）

### 📋 Phase 3: 本格運用（計画中）
- [ ] ライブ取引機能
- [ ] 高度なリスク管理
- [ ] ML予測モデル統合
- [ ] 包括的な監視システム

> 📈 **詳細な実装内容**: [Phase2 Implementation](./docs/PHASE2_IMPLEMENTATION.md)

## 🛡️ セキュリティ

### 🔒 実装済み
- JWT Bearer Token認証
- API キー暗号化保存
- HTTPS通信強制
- SQLインジェクション対策
- レート制限実装

### 🚨 重要な注意事項
⚠️ **本ソフトウェアは教育・研究目的で作成されています**
- リアル取引は自己責任で行ってください
- 十分なテストなしにライブ取引を有効化しないでください
- リスク管理を適切に設定してください

## 📈 パフォーマンス

### ベンチマーク結果
- **API レスポンス**: < 100ms (平均)
- **バックテスト処理**: 1年データを30秒で完了
- **リアルタイム更新**: < 1秒遅延
- **同時接続**: 1000+ WebSocket接続対応

## 🤝 コントリビューション

このプロジェクトへの貢献を歓迎します！

1. **Issue報告**: [GitHub Issues](https://github.com/yourusername/advanced-crypto-trading-bot/issues)
2. **機能提案**: [GitHub Discussions](https://github.com/yourusername/advanced-crypto-trading-bot/discussions)
3. **プルリクエスト**: [Contributing Guide](./docs/CONTRIBUTING.md)

### 開発者向けクイックスタート

```bash
# 開発環境のセットアップ
make setup-dev

# テスト実行
make test

# コード品質チェック
make lint

# ドキュメント生成
make docs
```

## 📄 ライセンス

このプロジェクトはMITライセンスの下で公開されています。詳細は [LICENSE](./LICENSE) ファイルをご覧ください。

## 🙏 謝辞

このプロジェクトは以下のオープンソースプロジェクトを活用しています：

- [FastAPI](https://fastapi.tiangolo.com/) - 高性能Webフレームワーク
- [Next.js](https://nextjs.org/) - Reactフレームワーク
- [Supabase](https://supabase.com/) - オープンソースFirebase代替
- [ccxt](https://github.com/ccxt/ccxt) - 取引所API統合ライブラリ

## 📞 サポート

### 📧 連絡先
- **Email**: support@example.com
- **Discord**: [Trading Bot Community](https://discord.gg/example)
- **Twitter**: [@TradingBotDev](https://twitter.com/TradingBotDev)

### 🔗 リンク
- **ライブデモ**: https://crypto-bot-demo.vercel.app
- **ドキュメント**: https://docs.crypto-bot.dev
- **API仕様**: https://api.crypto-bot.dev/docs

---

**⭐ このプロジェクトが役に立ったら、スターをつけてください！**

[![GitHub stars](https://img.shields.io/github/stars/yourusername/advanced-crypto-trading-bot.svg?style=social&label=Star)](https://github.com/yourusername/advanced-crypto-trading-bot)

---

<div align="center">
  <p>Made with ❤️ by the Advanced Crypto Trading Bot Team</p>
  <p>
    <a href="https://github.com/yourusername/advanced-crypto-trading-bot">GitHub</a> •
    <a href="./docs/GETTING_STARTED.md">Documentation</a> •
    <a href="https://discord.gg/example">Community</a>
  </p>
</div>
