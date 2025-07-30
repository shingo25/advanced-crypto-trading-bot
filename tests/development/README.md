# 開発用テストファイル

このディレクトリには、開発過程で作成されたテスト・デバッグファイルが含まれています。

## ファイル一覧

### 接続テスト

- `test_supabase_connection.py` - Supabase接続テスト
- `test_supabase_sdk_connection.py` - Supabase SDK接続テスト
- `test_sqlalchemy_connection.py` - SQLAlchemy接続テスト
- `test_multiple_connections.py` - 複数接続テスト
- `debug_supabase_connection.py` - Supabase接続デバッグ

### API テスト

- `test_auth_api.py` - 認証APIテスト
- `test_strategies_api.py` - 戦略APIテスト
- `test_backend_deployment.py` - バックエンドデプロイテスト

### データベーステスト

- `test_supabase_auth.py` - Supabase認証テスト
- `test_supabase_models.py` - Supabaseモデルテスト
- `test_database_migration.py` - データベース移行テスト

## 使用方法

これらのファイルは開発・デバッグ用です。本格的なテストは `/tests/` ディレクトリのファイルを使用してください。

```bash
# 例: Supabase接続テスト
cd tests/development
python test_supabase_connection.py
```

## 注意事項

- これらのファイルは一時的な開発用です
- 本番環境では使用しないでください
- APIキーなどの機密情報を含む場合があります
