# Contributing Guide - Advanced Crypto Trading Bot

このプロジェクトに貢献していただき、ありがとうございます！本ガイドでは、効果的で一貫した開発を行うためのルールと手順を説明します。

---

## 🎯 貢献の種類

私たちは以下のような貢献を歓迎します：

### 📝 ドキュメント
- API ドキュメントの改善
- README やガイドの更新
- コードコメントの追加・改善
- チュートリアルの作成

### 🐛 バグ修正
- バグの発見・報告
- 修正の実装
- テストケースの追加

### ✨ 新機能
- 新しい取引戦略の実装
- UI/UX の改善
- パフォーマンスの最適化
- セキュリティの強化

### 🧪 テスト
- 自動テストの追加
- テストカバレッジの向上
- 統合テストの実装

---

## 🚀 開発環境のセットアップ

### 1. フォークとクローン

```bash
# 1. GitHub でリポジトリをフォーク
# 2. フォークしたリポジトリをクローン
git clone https://github.com/YOUR_USERNAME/advanced-crypto-trading-bot.git
cd advanced-crypto-trading-bot

# 3. オリジナルリポジトリをupstreamとして追加
git remote add upstream https://github.com/ORIGINAL_OWNER/advanced-crypto-trading-bot.git
```

### 2. 環境構築

```bash
# Python 仮想環境
python3 -m venv venv
source venv/bin/activate  # macOS/Linux
pip install -r requirements.txt

# Node.js 依存関係
cd frontend
npm install
cd ..

# 環境変数設定
cp .env.example .env
# .env ファイルを編集して必要な値を設定
```

### 3. 開発ツールのセットアップ

```bash
# pre-commit hooks のインストール
pip install pre-commit
pre-commit install

# VS Code 拡張機能のインストール（推奨）
# - Python
# - Black Formatter  
# - Prettier
# - TypeScript
```

---

## 🔄 開発ワークフロー

### ブランチ戦略

```mermaid
gitgraph
    commit id: "main"
    branch feature/new-strategy
    checkout feature/new-strategy
    commit id: "Add: new trading strategy"
    commit id: "Test: strategy validation"
    checkout main
    merge feature/new-strategy
    commit id: "Release: v1.1.0"
```

#### ブランチ命名規則

| ブランチタイプ | 命名例 | 用途 |
|---------------|--------|------|
| `feature/` | `feature/add-rsi-strategy` | 新機能開発 |
| `bugfix/` | `bugfix/fix-auth-error` | バグ修正 |
| `hotfix/` | `hotfix/security-patch` | 緊急修正 |
| `docs/` | `docs/update-api-reference` | ドキュメント更新 |
| `test/` | `test/add-unit-tests` | テスト追加 |
| `refactor/` | `refactor/optimize-queries` | リファクタリング |

### 1. 新しい作業の開始

```bash
# 最新の main ブランチに同期
git checkout main
git pull upstream main

# 新しいブランチを作成
git checkout -b feature/your-feature-name

# 作業開始...
```

### 2. 開発プロセス

```bash
# 1. 実装
# 2. テスト実行
python -m pytest tests/
npm test  # フロントエンド

# 3. コードフォーマット
black backend/
prettier --write frontend/src/

# 4. リント
flake8 backend/
npm run lint  # フロントエンド

# 5. 型チェック  
mypy backend/
npm run type-check  # フロントエンド
```

### 3. コミットとプッシュ

```bash
# 変更をコミット
git add .
git commit -m "Add: new trading strategy for RSI indicators"

# フォークリポジトリにプッシュ
git push origin feature/your-feature-name
```

---

## 📝 コミットメッセージ規約

### 形式

```
<type>(<scope>): <subject>

<body>

<footer>
```

### タイプ

| タイプ | 説明 | 例 |
|--------|------|---|
| **Add** | 新機能の追加 | `Add: RSI trading strategy` |
| **Fix** | バグ修正 | `Fix: authentication token expiry` |
| **Update** | 既存機能の改善 | `Update: improve API response time` |
| **Remove** | 機能・コードの削除 | `Remove: deprecated endpoint` |
| **Refactor** | リファクタリング | `Refactor: optimize database queries` |
| **Test** | テストの追加・修正 | `Test: add unit tests for auth module` |
| **Docs** | ドキュメント更新 | `Docs: update API reference` |
| **Style** | コードスタイル修正 | `Style: format code with Black` |
| **Perf** | パフォーマンス改善 | `Perf: cache frequently used data` |
| **Security** | セキュリティ修正 | `Security: fix JWT token validation` |

### 例

```bash
# 良い例
git commit -m "Add: Bollinger Bands trading strategy

- Implement BB indicator calculation
- Add entry/exit signal logic  
- Include risk management parameters
- Add comprehensive unit tests

Closes #123"

# 悪い例
git commit -m "fixed stuff"
```

---

## 🧪 テスト指針

### テスト戦略

```mermaid
pyramid
    title Testing Pyramid
    section Unit Tests
        description 70% - 個別モジュール
    section Integration Tests  
        description 20% - API・DB連携
    section E2E Tests
        description 10% - ユーザーフロー
```

### 必須テスト項目

#### バックエンド（Python）

```python
# 1. ユニットテスト
def test_strategy_signal_generation():
    strategy = RSIStrategy(period=14)
    signals = strategy.generate_signals(mock_data)
    assert len(signals) > 0
    assert all(s in ['buy', 'sell', 'hold'] for s in signals)

# 2. API テスト
def test_strategy_creation_endpoint():
    response = client.post("/strategies/", 
                          json={"name": "Test", "parameters": {}},
                          headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 201
    assert "id" in response.json()
```

#### フロントエンド（TypeScript）

```typescript
// 1. コンポーネントテスト
test('StrategyList renders strategies correctly', () => {
  render(<StrategyList strategies={mockStrategies} />);
  expect(screen.getByText('BTC Strategy')).toBeInTheDocument();
});

// 2. API 統合テスト
test('creates new strategy via API', async () => {
  const response = await api.createStrategy(newStrategy);
  expect(response.status).toBe(201);
  expect(response.data.id).toBeDefined();
});
```

### テスト実行

```bash
# バックエンドテスト
source venv/bin/activate
python -m pytest tests/ -v --cov=backend --cov-report=html

# フロントエンドテスト
cd frontend
npm test
npm run test:coverage

# 統合テスト
python test_backend_deployment.py
```

---

## 📋 プルリクエスト手順

### 1. PR 作成前チェックリスト

- [ ] 最新の `main` ブランチから派生している
- [ ] 全テストがパスしている
- [ ] リントエラーがない
- [ ] ドキュメントが更新されている
- [ ] 変更ログが更新されている

### 2. PR テンプレート

```markdown
## 📋 変更内容

### 概要
この PR では何を実装/修正しましたか？

### 変更詳細
- [ ] 新機能: XXX を追加
- [ ] バグ修正: YYY を修正  
- [ ] ドキュメント: ZZZ を更新

## 🧪 テスト

### テスト項目
- [ ] ユニットテスト追加
- [ ] 統合テスト確認
- [ ] 手動テスト実施

### テスト手順
1. ...
2. ...
3. ...

## 📸 スクリーンショット
（UI変更がある場合）

## 🔗 関連 Issue
Closes #123

## 📝 レビュー観点
レビューアに特に確認してほしい点があれば記載

## 📚 その他
その他の補足情報があれば記載
```

### 3. PR 作成

1. GitHub で **New Pull Request** をクリック
2. base: `main` ← compare: `feature/your-branch` を設定
3. タイトルとテンプレートに従って詳細を記入
4. 適切なラベルを付与
5. レビューアを指定（可能であれば）

---

## 👀 コードレビュー指針

### レビューアの観点

#### 🔍 機能性
- [ ] 要件を満たしているか
- [ ] エラーハンドリングが適切か
- [ ] エッジケースを考慮しているか

#### 🎨 コード品質
- [ ] 読みやすく理解しやすいか
- [ ] DRY原則に従っているか
- [ ] 適切な抽象化レベルか

#### 🚀 パフォーマンス
- [ ] 不要なDBクエリがないか
- [ ] メモリリークの可能性はないか
- [ ] アルゴリズムの時間計算量は適切か

#### 🔐 セキュリティ
- [ ] 入力値の検証をしているか
- [ ] 認証・認可が適切か
- [ ] 機密情報の露出はないか

### レビューコメント例

```markdown
# 良いコメント例

## 提案
```python
# より読みやすくするため、この部分を関数に分離することを提案します
def calculate_rsi(prices, period=14):
    # RSI計算ロジック
    pass
```

## 質問
この条件分岐の意図を教えてください。コメントがあると理解しやすくなります。

## 賞賛
このエラーハンドリングは非常に適切ですね！ユーザー体験が向上します。

# 避けるべきコメント例
- "これは良くない" （理由と改善案がない）
- "なぜこうしたの？" （建設的でない質問）
```

---

## 🎨 コーディング規約

### Python（バックエンド）

#### スタイル
- **PEP 8** 準拠
- **Black** でフォーマット
- **flake8** でリント
- **mypy** で型チェック

```python
# 良い例
class TradingStrategy:
    """取引戦略の基底クラス"""
    
    def __init__(self, symbol: str, timeframe: str) -> None:
        self.symbol = symbol
        self.timeframe = timeframe
        self._indicators: Dict[str, Any] = {}
    
    def generate_signal(self, data: pd.DataFrame) -> Signal:
        """シグナルを生成する
        
        Args:
            data: OHLCV データ
            
        Returns:
            売買シグナル
        """
        if len(data) < self.min_periods:
            return Signal.HOLD
            
        return self._calculate_signal(data)

# 悪い例
def func(d):
    # コメントなし、型ヒントなし
    if len(d)>10:
        return 1
    else:
        return 0
```

#### 命名規則

| 対象 | 規則 | 例 |
|------|------|---|
| 変数・関数 | snake_case | `calculate_rsi`, `user_id` |
| クラス | PascalCase | `TradingStrategy`, `OrderManager` |
| 定数 | UPPER_CASE | `MAX_POSITION_SIZE`, `API_TIMEOUT` |
| プライベート | _prefix | `_calculate_signal`, `_api_key` |

### TypeScript（フロントエンド）

#### スタイル
- **Prettier** でフォーマット
- **ESLint** でリント
- **strict TypeScript** モード

```typescript
// 良い例
interface StrategyConfig {
  symbol: string;
  timeframe: '1m' | '5m' | '1h' | '1d';
  parameters: Record<string, number>;
}

const createStrategy = async (config: StrategyConfig): Promise<Strategy> => {
  try {
    const response = await api.post('/strategies/', config);
    return response.data;
  } catch (error) {
    throw new Error(`Failed to create strategy: ${error.message}`);
  }
};

// 悪い例
const create = (c: any) => {
  return api.post('/strategies/', c);
};
```

---

## 📊 品質メトリクス

### 目標値

| メトリクス | 目標 | 測定方法 |
|-----------|------|----------|
| **テストカバレッジ** | > 80% | pytest-cov, Jest |
| **型安全性** | 100% | mypy, TypeScript strict |
| **リント適合** | 100% | flake8, ESLint |
| **API応答時間** | < 200ms | 統合テスト |
| **セキュリティ** | 0 warnings | bandit, npm audit |

### 継続的インテグレーション

```yaml
# .github/workflows/ci.yml
name: CI

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.12'
          
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          
      - name: Run tests
        run: |
          pytest --cov=backend --cov-report=xml
          
      - name: Upload coverage
        uses: codecov/codecov-action@v3
```

---

## 🚨 セキュリティガイドライン

### 機密情報の取り扱い

#### ❌ 絶対にコミットしてはいけないもの
- API キー・シークレット
- パスワード・トークン  
- プライベートキー
- データベース接続文字列
- ユーザーの個人情報

#### ✅ 適切な管理方法
```bash
# 環境変数で管理
export API_KEY="your-secret-key"

# .env ファイル（.gitignore 必須）
echo "API_KEY=your-secret-key" > .env
echo ".env" >> .gitignore

# 暗号化して保存
gpg --encrypt --recipient your@email.com secrets.txt
```

### セキュアコーディング

```python
# SQL インジェクション対策
# ❌ 悪い例
query = f"SELECT * FROM users WHERE id = {user_id}"

# ✅ 良い例  
query = "SELECT * FROM users WHERE id = %s"
cursor.execute(query, (user_id,))

# XSS 対策
# ❌ 悪い例
return f"<div>{user_input}</div>"

# ✅ 良い例
from html import escape
return f"<div>{escape(user_input)}</div>"
```

---

## 📞 サポート・質問

### 質問方法

1. **GitHub Issues**: バグ報告・機能要望
2. **GitHub Discussions**: 一般的な質問・議論
3. **Pull Request**: コードレビュー依頼

### Issue テンプレート

```markdown
## 🐛 バグ報告

### 環境
- OS: [e.g. macOS 13.0]
- Python: [e.g. 3.12.0]
- Node.js: [e.g. 18.0.0]

### 再現手順
1. ...
2. ...
3. ...

### 期待する動作
...

### 実際の動作
...

### スクリーンショット
（可能であれば）
```

---

## 🎉 貢献者の認識

### 貢献者リスト

すべての貢献者は `CONTRIBUTORS.md` に記載され、リリースノートで感謝の意を表します。

### 貢献レベル

| レベル | 基準 | 特典 |
|--------|------|------|
| **Contributor** | 1回以上のPR | README掲載 |
| **Regular Contributor** | 5回以上のPR | 専用バッジ |
| **Core Contributor** | 20回以上のPR | レビュー権限 |
| **Maintainer** | 長期的な貢献 | リポジトリ管理権限 |

---

**あなたの貢献がプロジェクトをより良いものにします。一緒に素晴らしい暗号通貨取引ボットを作りましょう！** 🚀