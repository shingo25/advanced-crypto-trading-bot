# 開発用スクリプト

このディレクトリには、開発過程で作成されたセットアップ・起動スクリプトが含まれています。

## ファイル一覧

### セットアップスクリプト
- `setup_admin_user.py` - 管理者ユーザーセットアップ

### 起動スクリプト
- `start_backend.py` - バックエンドサーバー起動
- `start_demo.py` - デモ環境起動

### API関連
- `simple_api.py` - シンプルなAPI実装（デモ用）

## 使用方法

```bash
# 例: 管理者ユーザーセットアップ
cd scripts/development
python setup_admin_user.py

# バックエンド起動
python start_backend.py

# デモ環境起動
python start_demo.py
```

## 注意事項

- これらのファイルは開発・デバッグ用です
- 本番環境での使用は想定していません
- 環境変数の設定が必要な場合があります
