# 🏗️ crypto-bot ディレクトリ構造最適化計画

**作成日**: 2025-07-30
**バージョン**: v1.0
**策定者**: Claude Code + Gemini AI 協業

---

## 📋 概要

crypto-botプロジェクトを企業グレードモノレポ構造に最適化し、将来のマイクロサービス化とスケーラビリティに対応する包括的なディレクトリ再編計画です。

## 🎯 目標

- **企業グレードモノレポ構造**の実現
- **一発CI/CD成功**の保証
- **将来のマイクロサービス化**への対応
- **開発者体験向上**とメンテナンス性改善

---

## 🔥 Gemini AI 戦略提言

### 推奨アーキテクチャ: packages/ アプローチ

```
crypto-bot/
├── packages/
│   ├── backend/              # Python FastAPI パッケージ
│   │   ├── src/
│   │   │   └── crypto_bot/   # メインPythonパッケージ
│   │   │       ├── api/      # APIエンドポイント
│   │   │       ├── core/     # 共通機能
│   │   │       ├── exchanges/# 取引所アダプター
│   │   │       └── ...
│   │   ├── tests/            # バックエンドテスト
│   │   └── pyproject.toml    # Python設定
│   ├── frontend/             # Next.js パッケージ
│   │   ├── src/              # React/Next.js ソース
│   │   ├── tests/            # フロントエンドテスト
│   │   └── package.json
│   └── shared/               # 共通型定義・定数
│       ├── types/            # TypeScript型定義
│       └── constants/        # 共通定数
├── api/                      # Vercel serverless functions
├── .github/workflows/        # CI/CD設定
├── config/                   # 環境別設定
├── docs/                     # ドキュメント
└── scripts/                  # ビルド・デプロイスクリプト
```

### Gemini推奨理由

1. **関心の分離**: backend/frontend完全分離
2. **スケーラビリティ**: 新サービス追加が容易
3. **CI/CD最適化**: パッケージ単位でのビルドが可能
4. **開発者体験**: モジュラー構造による作業効率向上

---

## 📊 現状分析結果（Serena分析）

### 問題点特定

#### 構造的問題
- **重複ディレクトリ**: `backend/`と`src/backend/`が共存
- **フロントエンド重複**: `frontend/frontend/`の二重ネスト
- **混在アーキテクチャ**: モノリス + マイクロサービスの混在

#### 依存関係の問題
- **88個のファイル**で相対importや`from backend`パターンを使用
- **Vercel設定**が現在の構造に強く依存
- **CI/CD設定**が既存パスを前提とした構成

### 更新が必要なファイル群

#### CI/CD設定ファイル
- `.github/workflows/ci.yml`: パス参照をpackages/構造に更新
- `docker-compose.yml`: ボリュームマウントパス更新
- `Dockerfile.backend`, `Dockerfile.frontend`: COPYパス更新

#### デプロイメント設定
- `vercel.json`: `outputDirectory`, `src`パス更新
- `scripts/vercel-build.sh`: ビルドパス更新

#### 開発環境設定
- `pyproject.toml`: パッケージ構造対応
- `package.json`: workspaces設定追加
- `pytest.ini`: テストパス更新

---

## 🚀 段階的実装プラン

### Phase 1: 準備作業（リスク最小化）

```bash
# 1. 新しいディレクトリ構造作成
mkdir -p packages/{backend,frontend,shared}
mkdir -p packages/backend/{src/crypto_bot,tests}
mkdir -p packages/frontend/{src,tests,public}
mkdir -p packages/shared/{types,constants,schemas}

# 2. バックアップ作成
git checkout -b backup/pre-monorepo-migration
git add . && git commit -m "backup: pre-monorepo migration state"
```

### Phase 2: バックエンド移行

```bash
# 1. バックエンドファイル移動
git mv src/backend/* packages/backend/src/crypto_bot/
git mv tests/ packages/backend/tests/

# 2. インポートパス更新
python scripts/update_imports.py --source-dir packages/backend/src/crypto_bot/
```

### Phase 3: フロントエンド移行

```bash
# 1. フロントエンドファイル整理
git mv frontend/src/* packages/frontend/src/
git mv frontend/public/* packages/frontend/public/
git mv frontend/package.json packages/frontend/
```

### Phase 4: 設定ファイル更新

- `vercel.json` パス更新
- CI/CD設定更新
- Docker設定更新
- テスト設定更新

---

## ⚠️ リスク管理戦略

### 高リスク項目と対策

1. **インポートパス変更** (88ファイル)
   - **対策**: 自動化スクリプトによる一括更新
   - **検証**: 段階的テスト実行

2. **CI/CD破綻**
   - **対策**: ローカルでのCI/CD再現テスト
   - **検証**: プレビューデプロイでの事前確認

3. **Vercelデプロイ失敗**
   - **対策**: 設定変更の段階的適用
   - **検証**: プレビューデプロイでの検証

### ロールバック戦略

```bash
# 緊急時のロールバック手順
git checkout backup/pre-monorepo-migration
git checkout -b rollback/monorepo-migration-$(date +%Y%m%d-%H%M%S)
# 必要に応じて選択的な修正を適用
```

---

## 🔧 技術的実装詳細

### workspaces設定（ルートpackage.json）

```json
{
  "name": "crypto-bot-monorepo",
  "private": true,
  "workspaces": [
    "packages/*"
  ],
  "scripts": {
    "dev": "npm run dev --workspace=packages/frontend",
    "build": "npm run build --workspaces",
    "test": "npm run test --workspaces"
  }
}
```

### バックエンドpyproject.toml

```toml
[project]
name = "crypto-bot-backend"
version = "3.0.0"

[tool.setuptools.packages.find]
where = ["src"]

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["src"]
```

### CI/CD更新例

```yaml
# .github/workflows/ci.yml (例)
- name: 🎨 Code formatting check (Ruff)
  run: ruff format packages/backend/src/crypto_bot/ --check

- name: 🧪 Run unit tests
  run: |
    export PYTHONPATH=$PYTHONPATH:$(pwd)/packages/backend/src
    python -m pytest packages/backend/tests/
```

---

## 📊 期待される効果

### 開発効率向上

- **モジュラー開発**: パッケージ単位での独立した開発
- **並行開発**: フロントエンド・バックエンドの同時開発
- **テスト効率**: パッケージ単位でのテスト実行

### 運用・保守性向上

- **スケーラビリティ**: 新パッケージの追加が容易
- **CI/CD効率化**: 変更されたパッケージのみビルド
- **依存関係管理**: パッケージ間の明確な境界

### 将来対応

- **マイクロサービス化**: 段階的な分離が可能
- **チーム拡張**: パッケージ単位でのチーム担当
- **技術選択の柔軟性**: パッケージごとの技術スタック

---

## 📅 実装スケジュール

| 段階 | 期間 | 主要作業 | 成果物 |
|------|------|----------|--------|
| Phase 1 | 1日 | 準備・バックアップ | 新ディレクトリ構造 |
| Phase 2 | 1日 | バックエンド移行 | packages/backend完成 |
| Phase 3 | 1日 | フロントエンド移行 | packages/frontend完成 |
| Phase 4 | 1日 | 設定更新・検証 | CI/CD対応完了 |

**総実装期間**: 4日間（検証・調整含む）

---

## ✅ 完了基準

### 技術的完了基準

- [ ] すべてのテストがpackages/構造でパス
- [ ] CI/CDパイプラインが正常動作
- [ ] Vercelデプロイが成功
- [ ] importエラーが0件

### 品質基準

- [ ] テストカバレッジ90%以上維持
- [ ] ビルド時間20%以上短縮
- [ ] 開発者体験の向上確認

---

## 🤝 次のアクション

1. **実装承認**: プラン内容の最終確認
2. **バックアップ作成**: 現在の状態の完全保存
3. **段階的実行**: Phase 1から順次実施
4. **継続的検証**: 各段階でのテスト実行

---

**🎯 この計画により、crypto-botは企業グレードのモノレポ構造を獲得し、スケーラブルで保守性の高いプロジェクトへと進化します。**

---

**🤖 Generated with [Claude Code](https://claude.ai/code) + Gemini AI 協業**

**策定完了**: 2025-07-30
**実装準備**: 完了 ✅
**次回実装予定**: ユーザー指示により開始
