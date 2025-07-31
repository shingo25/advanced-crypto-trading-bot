# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- 企業レベル開発運用体制の構築
- GitHub Issue/PR テンプレート
- セキュリティポリシー (SECURITY.md)
- コードオーナーシップ (CODEOWNERS)
- エディタ設定統一 (.editorconfig)

## [1.0.0] - 2025-07-15

### Added
- **Phase 1 完了**: データベース基盤構築
- Supabase PostgreSQL 統合
- JWT認証システム (httpOnly cookies)
- FastAPI バックエンドAPI
- Next.js フロントエンドアプリケーション
- Vercel 本番環境デプロイ
- 包括的プロジェクトドキュメンテーション

#### Backend Features
- 戦略管理 API (`/api/strategies/`)
- 認証 API (`/api/auth/`)
- Supabase SDK統合
- Row Level Security (RLS)
- 7テーブル完全スキーマ

#### Frontend Features
- Next.js 15 + TypeScript
- Material-UI コンポーネント
- Zustand 状態管理
- レスポンシブデザイン
- 認証フロー実装

#### Infrastructure
- Vercel Functions (Python 3.12)
- Supabase Database hosting
- 環境変数管理
- CI/CD デプロイパイプライン

### Security
- API キー暗号化保存
- CORS設定
- 入力値検証
- XSS/SQLインジェクション対策

### Documentation
- PROJECT_STATUS.md - 実装状況記録
- ROADMAP.md - 開発計画
- docs/GETTING_STARTED.md - 環境構築ガイド
- docs/ARCHITECTURE.md - システム設計
- docs/API_REFERENCE.md - API仕様書
- docs/DATABASE_SCHEMA.md - データベース設計
- CONTRIBUTING.md - 開発ガイドライン

### Changed
- DuckDB から Supabase PostgreSQL に移行
- 開発環境から本番環境へのデプロイ完了

### Technical Details
- **Backend**: FastAPI + Supabase SDK
- **Frontend**: Next.js 15 + TypeScript
- **Database**: Supabase PostgreSQL
- **Hosting**: Vercel (Frontend + Functions)
- **Authentication**: Supabase Auth + JWT

---

## バージョニング規則

- **Major (X.0.0)**: 破壊的変更
- **Minor (0.X.0)**: 新機能追加（後方互換性あり）
- **Patch (0.0.X)**: バグ修正

## 変更カテゴリ

- **Added**: 新機能
- **Changed**: 既存機能の変更
- **Deprecated**: 非推奨機能
- **Removed**: 削除された機能
- **Fixed**: バグ修正
- **Security**: セキュリティ関連の変更
