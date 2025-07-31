# 開発ガイド

## はじめに

このドキュメントは、crypto-botプロジェクトの開発者向けガイドです。

## 開発環境のセットアップ

### 1. 必要な依存関係のインストール

```bash
# Python依存関係
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Node.js依存関係
cd frontend
npm install
```

### 2. Pre-commitフックのセットアップ

```bash
# pre-commitのインストール
pipx install pre-commit

# pre-commitフックの有効化
pre-commit install

# 全ファイルに対してチェック実行
pre-commit run --all-files
```

## コード品質基準

### Python (Backend)
- **Ruff**: リンティングとフォーマット
- **MyPy**: 型チェック
- **Bandit**: セキュリティ分析
- **pytest**: テスト実行

### TypeScript/JavaScript (Frontend)
- **ESLint**: リンティング
- **Prettier**: フォーマット
- **TypeScript**: 型チェック
- **Jest**: テスト実行

## CI/CDパイプライン

### GitHub Actions
- 🔒 **Security Scan**: TruffleHog、git-secrets
- 🐍 **Backend Tests**: Ruff、MyPy、Bandit、pytest
- 🎨 **Frontend Tests**: ESLint、Prettier、TypeScript、Jest、npm audit
- 🐳 **Docker Build**: Docker Compose
- 🌐 **E2E Tests**: エンドツーエンドテスト
- 📈 **Code Quality**: SonarCloud
- 🚀 **Deployment Check**: デプロイ準備確認

### ブランチ保護
- `main`ブランチは直接pushを禁止
- Pull Request必須
- CI/CDパイプラインの成功が必要

## Pre-commitフックの効果

### 自動実行される処理
1. **コードフォーマット**: Ruffが自動的にPythonコードをフォーマット
2. **リンティング**: コード品質問題を自動修正
3. **ファイル整合性**: 末尾空白の除去、改行確認
4. **YAML検証**: 設定ファイルの検証
5. **大きなファイル**: 大きなファイルの検出
6. **マージ競合**: マージ競合の検出

### 開発者体験の向上
- コミット前に自動的にコード品質を確保
- CI/CDでのエラーを事前に防止
- チーム全体のコード品質を均一化

## トラブルシューティング

### Pre-commitフックのスキップ
```bash
# 緊急時のみ使用
git commit -m "commit message" --no-verify
```

### CI/CDエラーの解決
1. ローカルで再現: `pre-commit run --all-files`
2. 問題を修正
3. 再度コミット・プッシュ

## 参考資料
- [Ruff Documentation](https://docs.astral.sh/ruff/)
- [MyPy Documentation](https://mypy.readthedocs.io/)
- [Pre-commit Documentation](https://pre-commit.com/)
