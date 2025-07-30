# CI環境でのデータベース設定

## 問題の概要

CI環境（GitHub Actions）でPaper Tradingテストを実行する際、PostgreSQLへの接続を試みてエラーが発生していました。

```
sqlalchemy.exc.OperationalError: connection to server at "localhost", port 5432 failed: Connection refused
```

## 解決策

### 1. ExchangeFactoryの修正

`src/backend/exchanges/factory.py`でCI/テスト環境を検出してSQLiteを使用するように修正：

```python
# CI環境またはテスト環境ではSQLiteを使用
default_db_url = "sqlite:///paper_trading.db"
if settings.ENVIRONMENT.lower() not in ["test", "ci", "testing"]:
    default_db_url = "postgresql://localhost/trading_bot_paper"
```

### 2. conftest.pyでのモック設定

`tests/conftest.py`に以下の設定を追加：

- CI環境の検出と環境変数の設定
- DatabaseManagerのモック化
- ExchangeFactoryのデフォルトデータベースURLの上書き

### 3. GitHub ActionsでのCI環境変数

`.github/workflows/ci.yml`でテスト実行時に環境変数を設定：

```yaml
- name: 🧪 Run unit tests
  env:
    CI: "true"
    ENVIRONMENT: "test"
  run: |
    export PYTHONPATH=$PYTHONPATH:$(pwd)
    python -m pytest tests/ -v
```

## テスト実行時の動作

1. **CI環境（GitHub Actions）**
   - `CI=true`環境変数が設定される
   - `ENVIRONMENT=test`または`ci`が設定される
   - DatabaseManagerはモック化され、実際のデータベース接続は行われない
   - Paper TradingはインメモリSQLite（`sqlite:///:memory:`）を使用

2. **ローカル開発環境**
   - テスト時は一時的なSQLiteファイルを使用
   - 本番環境では通常通りPostgreSQLを使用可能

## トラブルシューティング

### エラーが継続する場合

1. 環境変数の確認：
   ```bash
   echo $CI
   echo $ENVIRONMENT
   ```

2. pytestの詳細ログを確認：
   ```bash
   pytest -vvs tests/test_paper_live_safety.py
   ```

3. DatabaseManagerの初期化をトレース：
   ```python
   import logging
   logging.basicConfig(level=logging.DEBUG)
   ```

### ローカルでのCI環境再現

CI環境と同じ条件でテストを実行：

```bash
CI=true ENVIRONMENT=test pytest tests/
```

## 関連ファイル

- `src/backend/exchanges/factory.py` - ExchangeFactoryの実装
- `src/backend/exchanges/paper_trading_adapter.py` - Paper Trading実装
- `src/backend/database/models.py` - DatabaseManagerの実装
- `tests/conftest.py` - pytest設定とモック
- `tests/test_helpers.py` - テスト用ヘルパー関数
- `.github/workflows/ci.yml` - CI/CD設定
