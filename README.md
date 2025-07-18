# 🚀 Advanced Crypto Trading Bot

高度な暗号通貨取引ボットシステム - Supabase統合、Vercelデプロイ対応の次世代自動取引プラットフォーム

![Build Status](https://img.shields.io/badge/build-passing-brightgreen)
![Python](https://img.shields.io/badge/python-3.12+-blue)
![Node.js](https://img.shields.io/badge/node.js-18.x-green)
![Supabase](https://img.shields.io/badge/supabase-enabled-green)
![Vercel](https://img.shields.io/badge/vercel-deployed-black)
![License](https://img.shields.io/badge/license-MIT-blue)

## 📋 目次

- [📚 プロジェクトドキュメント](#-プロジェクトドキュメント)
- [機能概要](#機能概要)
- [技術スタック](#技術スタック)
- [クイックスタート](#クイックスタート)
- [システム構成](#システム構成)
- [戦略一覧](#戦略一覧)
- [デプロイ](#デプロイ)
- [貢献](#貢献)
- [ライセンス](#ライセンス)

## 📚 プロジェクトドキュメント

このプロジェクトの詳細情報は以下のドキュメントで確認できます：

| ドキュメント | 内容 | 場所 |
|-------------|------|------|
| 📊 **プロジェクト状況** | 現在の実装状況、完了したフェーズ、テスト結果 | [PROJECT_STATUS.md](./PROJECT_STATUS.md) |
| 🗺️ **ロードマップ** | 次にやるべきこと、優先順位、将来計画 | [ROADMAP.md](./ROADMAP.md) |
| 🚀 **環境構築ガイド** | 新規開発者向けセットアップ手順 | [docs/GETTING_STARTED.md](./docs/GETTING_STARTED.md) |
| 🏗️ **システム設計** | アーキテクチャ、技術選択、設計思想 | [docs/ARCHITECTURE.md](./docs/ARCHITECTURE.md) |
| 📡 **API仕様書** | エンドポイント一覧、認証、サンプルコード | [docs/API_REFERENCE.md](./docs/API_REFERENCE.md) |
| 🗄️ **データベース設計** | テーブル構造、RLS、インデックス戦略 | [docs/DATABASE_SCHEMA.md](./docs/DATABASE_SCHEMA.md) |
| 👥 **開発ガイドライン** | 開発手順、コーディング規約、PR作成方法 | [CONTRIBUTING.md](./CONTRIBUTING.md) |

> 💡 **開発を始める前に**: まず [PROJECT_STATUS.md](./PROJECT_STATUS.md) で現状を把握し、[ROADMAP.md](./ROADMAP.md) で次のタスクを確認してください。

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
- **Python 3.12+** - メイン開発言語
- **FastAPI** - 高性能Web APIフレームワーク
- **Supabase PostgreSQL** - 本番データベース (DuckDBから移行済み)
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

## 🚀 クイックスタート

### 最速で始める方法

```bash
# 1. リポジトリをクローン
git clone https://github.com/YOUR_USERNAME/advanced-crypto-trading-bot.git
cd advanced-crypto-trading-bot

# 2. ドキュメントを確認
cat PROJECT_STATUS.md  # 現在の状況を把握
cat ROADMAP.md         # 次にやることを確認

# 3. 詳細な環境構築は以下を参照
cat docs/GETTING_STARTED.md
```

> 💡 **新規開発者の方**: 詳細なセットアップ手順は [docs/GETTING_STARTED.md](./docs/GETTING_STARTED.md) をご覧ください。

### 現在のデプロイ状況

- **フロントエンド**: Vercel にデプロイ済み (`https://crypto-m1u2wjova-shingo-arais-projects.vercel.app`)
- **バックエンドAPI**: Vercel Functions にデプロイ済み  
- **データベース**: Supabase PostgreSQL 運用中
- **認証**: Supabase Auth + JWT 実装済み
- **CI/CD**: GitHub Actions による自動テスト・セキュリティスキャン実装済み


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


## 🚢 デプロイ

現在は **Vercel** + **Supabase** でデプロイ済みです。

- **フロントエンド**: Vercel Static Hosting
- **バックエンドAPI**: Vercel Functions  
- **データベース**: Supabase PostgreSQL
- **認証**: Supabase Auth

詳細なデプロイ手順は [docs/GETTING_STARTED.md](./docs/GETTING_STARTED.md) を参照してください。

## 🤝 貢献

プロジェクトへの貢献を歓迎します！

詳細な開発手順・コーディング規約は [CONTRIBUTING.md](./CONTRIBUTING.md) をご覧ください。

## 📞 サポート

- **GitHub Issues**: バグ報告・機能要望
- **ドキュメント**: 各種 .md ファイルで詳細説明

## ⚠️ 免責事項

このソフトウェアは教育・研究目的で提供されています。実際の取引での使用は自己責任で行ってください。

---

**🔥 Happy Trading! 🔥**