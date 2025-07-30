# Phase 2 実装詳細 - Advanced Crypto Trading Bot

このドキュメントでは、Phase 2の実装内容と今後の開発計画について詳述します。

**最終更新**: 2025-01-20

---

## 📊 Phase 2 概要

Phase 2では、リアルタイムデータ収集と処理基盤の構築に焦点を当てています。

### 🎯 Phase 2 の目標

1. **データパイプライン構築**: 取引所APIからのリアルタイムデータ収集
2. **データストレージ最適化**: Supabaseへの効率的なデータ保存
3. **API実データ対応**: モックからリアルデータへの移行
4. **バックテスト強化**: 実データを使用したバックテスト機能
5. **リアルタイム更新**: WebSocketによる価格更新

---

## ✅ 実装済み機能 (2025-01-20)

### 1. データパイプライン - Binance OHLCV収集

#### 実装内容

##### **DataCollectorクラス** (`backend/data_pipeline/collector.py`)

```python
class DataCollector:
    """データ収集クラス"""

    async def collect_ohlcv(
        self,
        symbol: str,
        timeframe: TimeFrame,
        since: Optional[datetime] = None,
        limit: int = 1000,
    ) -> List[OHLCV]:
        """OHLCV データを収集"""

    async def collect_batch_ohlcv(
        self,
        symbols: List[str],
        timeframes: List[TimeFrame],
        since: Optional[datetime] = None,
    ) -> Dict[str, Dict[str, List[OHLCV]]]:
        """複数シンボル・時間枠のOHLCVデータを並列収集"""
```

##### **主な特徴**

- 非同期処理による高速データ収集
- バッチ処理対応（複数シンボル・タイムフレーム）
- Parquetファイルへのバックアップ保存
- エラーハンドリングとリトライ機能

#### Supabase連携

##### **price_dataテーブル**

```sql
CREATE TABLE public.price_data (
    id bigserial NOT NULL PRIMARY KEY,
    exchange text NOT NULL,
    symbol text NOT NULL,
    timeframe text NOT NULL,
    timestamp timestamp with time zone NOT NULL,
    open_price numeric(20,8) NOT NULL,
    high_price numeric(20,8) NOT NULL,
    low_price numeric(20,8) NOT NULL,
    close_price numeric(20,8) NOT NULL,
    volume numeric(20,8) NOT NULL,
    created_at timestamp with time zone DEFAULT timezone('utc'::text, now()) NOT NULL,
    UNIQUE(exchange, symbol, timeframe, timestamp)
);
```

##### **バッチ保存の最適化**

- 1000件/バッチのサイズ制限
- upsert処理による重複データ回避
- 進捗ログ出力

#### テスト実装

- **単体テスト**: 9個のテストケース
- **統合テスト**: データフロー全体の動作確認
- **機能テスト**: 実API呼び出しテスト

```bash
# テスト実行
python -m pytest tests/test_data_pipeline.py -v

# 機能テスト
python scripts/test_data_pipeline.py
```

---

## 🚀 今後の実装計画

### Phase 2 残タスク

#### 1. API エンドポイント実データ対応 (優先度: 高)

**実装内容**:

- `/api/market-data/ohlcv` エンドポイントの実データ対応
- キャッシュ戦略の実装（Redis検討）
- ページネーション対応

**ファイル**:

- `backend/api/routes/market_data.py`
- `backend/services/market_data_service.py`

#### 2. バックテスト機能改善 (優先度: 高)

**実装内容**:

- 実データを使用したバックテストエンジン
- パフォーマンス指標の計算精度向上
- バックテスト結果の可視化改善

**ファイル**:

- `backend/services/backtest_service.py`
- `backend/models/backtest_result.py`

#### 3. リアルタイム価格更新 (優先度: 中)

**実装内容**:

- WebSocket接続管理
- リアルタイム価格配信
- フロントエンドとの連携

**ファイル**:

- `backend/websocket/price_stream.py`
- `backend/api/websocket_handler.py`

### Phase 3 計画

#### 1. 高度な取引戦略実装

- **機械学習モデル統合**
  - LSTMによる価格予測
  - 強化学習エージェント

- **テクニカル指標拡充**
  - カスタムインジケーター
  - マルチタイムフレーム分析

#### 2. リスク管理システム

- **ポートフォリオ最適化**
  - モダンポートフォリオ理論の実装
  - リスクパリティ戦略

- **自動リスク制御**
  - ドローダウン制限
  - ポジションサイジング

#### 3. 取引実行エンジン

- **スマートオーダールーティング**
- **高頻度取引対応**
- **複数取引所アービトラージ**

---

## 📝 開発ガイドライン

### コーディング規約

1. **非同期処理優先**

   ```python
   # 良い例
   async def fetch_data():
       results = await asyncio.gather(*tasks)

   # 避けるべき例
   def fetch_data():
       for task in tasks:
           result = task()
   ```

2. **エラーハンドリング**

   ```python
   try:
       data = await fetch_ohlcv()
   except Exception as e:
       logger.error(f"Error fetching data: {e}")
       # 処理は継続
   ```

3. **型ヒント使用**
   ```python
   async def collect_ohlcv(
       self,
       symbol: str,
       timeframe: TimeFrame,
   ) -> List[OHLCV]:
   ```

### テスト方針

1. **単体テスト**: 各クラス・メソッドごと
2. **統合テスト**: 機能間の連携確認
3. **E2Eテスト**: ユーザーシナリオベース

### パフォーマンス考慮事項

1. **バッチ処理**: 大量データは分割処理
2. **並列処理**: `asyncio.gather()`の活用
3. **キャッシュ**: 頻繁にアクセスされるデータ

---

## 🔧 環境設定

### 必要な環境変数

```bash
# Supabase
SUPABASE_URL=your_supabase_url
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key

# Exchange API (Optional)
BINANCE_API_KEY=your_api_key
BINANCE_API_SECRET=your_api_secret
```

### データベースマイグレーション

```bash
# price_dataテーブル作成
psql $DATABASE_URL < database/migrations/002_add_price_data.sql
```

---

## 📚 参考資料

- [Binance API Documentation](https://binance-docs.github.io/apidocs/)
- [Supabase Database Functions](https://supabase.com/docs/guides/database)
- [AsyncIO Best Practices](https://docs.python.org/3/library/asyncio.html)

---

**注意**: このドキュメントは開発の進行に応じて更新されます。最新の実装状況はGitHubのissuesとPRを参照してください。
