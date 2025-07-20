# APIエンドポイント一覧

## Market Data API

### 基本情報
- **ベースURL**: `/api/market-data`
- **認証**: 不要
- **レート制限**: 1000リクエスト/時間
- **キャッシュ**: 60秒TTL

### エンドポイント

#### 1. OHLCV価格データ取得
```http
GET /api/market-data/ohlcv
```

**パラメータ:**
- `exchange` (string, optional): 取引所名 (デフォルト: "binance")
- `symbol` (string, required): シンボル（例: "BTCUSDT"）
- `timeframe` (string, optional): 時間足 (デフォルト: "1h")
- `limit` (integer, optional): 取得件数 (1-1000, デフォルト: 100)
- `start_time` (datetime, optional): 開始時刻 (ISO 8601形式)
- `end_time` (datetime, optional): 終了時刻 (ISO 8601形式)

**レスポンス例:**
```json
[
  {
    "timestamp": "2024-01-15T10:00:00Z",
    "open": 50000.0,
    "high": 51000.0,
    "low": 49500.0,
    "close": 50800.0,
    "volume": 1250.5
  }
]
```

**使用例:**
```javascript
// 基本的な使用
const ohlcv = await marketDataApi.getOHLCV({
  symbol: "BTCUSDT",
  timeframe: "1h",
  limit: 100
});

// 時間範囲指定
const ohlcv = await marketDataApi.getOHLCV({
  symbol: "ETHUSDT",
  timeframe: "4h",
  start_time: "2024-01-01T00:00:00Z",
  end_time: "2024-01-07T23:59:59Z"
});
```

#### 2. 利用可能なシンボル一覧
```http
GET /api/market-data/symbols
```

**パラメータ:**
- `exchange` (string, optional): 取引所名 (デフォルト: "binance")

**レスポンス例:**
```json
{
  "symbols": ["BTCUSDT", "ETHUSDT", "BNBUSDT", "ADAUSDT", "SOLUSDT"]
}
```

#### 3. 利用可能な時間足一覧
```http
GET /api/market-data/timeframes
```

**パラメータ:**
- `exchange` (string, optional): 取引所名 (デフォルト: "binance")
- `symbol` (string, optional): 特定シンボルの時間足

**レスポンス例:**
```json
{
  "timeframes": ["1m", "5m", "15m", "30m", "1h", "4h", "1d"]
}
```

#### 4. 最新価格取得
```http
GET /api/market-data/latest
```

**パラメータ:**
- `exchange` (string, optional): 取引所名 (デフォルト: "binance")
- `symbols` (string, optional): カンマ区切りのシンボル一覧
- `timeframe` (string, optional): 時間足 (デフォルト: "1h")

**レスポンス例:**
```json
{
  "latest_prices": [
    {
      "symbol": "BTCUSDT",
      "timestamp": "2024-01-15T10:00:00Z",
      "open": 50000.0,
      "high": 51000.0,
      "low": 49500.0,
      "close": 50800.0,
      "volume": 1250.5
    }
  ]
}
```

#### 5. ヘルスチェック
```http
GET /api/market-data/health
```

**レスポンス例:**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:00:00Z",
  "database_connection": "ok",
  "total_records": 150000,
  "cache_size": 45
}
```

## Performance API

### 基本情報
- **ベースURL**: `/api/performance`
- **認証**: 不要（将来的には認証が必要になる予定）
- **データソース**: price_dataテーブルのBTCUSDT価格をベースに計算

### エンドポイント

#### 1. パフォーマンス履歴取得
```http
GET /api/performance/history
```

**パラメータ:**
- `period` (string, optional): 期間 ("1d", "7d", "30d", "90d", デフォルト: "7d")

**レスポンス例:**
```json
[
  {
    "timestamp": "2024-01-15T00:00:00Z",
    "total_value": 105000.0,
    "daily_return": 0.02,
    "cumulative_return": 0.15,
    "drawdown": 0.03
  }
]
```

#### 2. パフォーマンスサマリー取得
```http
GET /api/performance/summary
```

**レスポンス例:**
```json
{
  "total_value": 105000.0,
  "cumulative_return": 0.15,
  "daily_return_avg": 0.012,
  "daily_return_max": 0.08,
  "daily_return_min": -0.05,
  "volatility": 0.025,
  "max_drawdown": 0.08,
  "sharpe_ratio": 1.2,
  "calculation_period": "7d",
  "last_updated": "2024-01-15T10:00:00Z"
}
```

#### 3. ヘルスチェック
```http
GET /api/performance/health
```

**レスポンス例:**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:00:00Z",
  "database_connection": "ok",
  "btc_records": 8760
}
```

## エラーレスポンス

### 共通エラーコード
- `400`: Bad Request - パラメータエラー
- `404`: Not Found - データが見つからない
- `500`: Internal Server Error - サーバーエラー
- `503`: Service Unavailable - サービス利用不可

### エラーレスポンス例
```json
{
  "detail": "無効な時間足です。有効な値: 1m, 5m, 15m, 30m, 1h, 4h, 1d"
}
```

## 使用方法（フロントエンド）

### TypeScript型定義
```typescript
// パラメータ型
interface MarketDataParams {
  exchange?: string;
  symbol: string;
  timeframe?: string;
  limit?: number;
  start_time?: string;
  end_time?: string;
}

// レスポンス型
interface OHLCVData {
  timestamp: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

interface PerformanceData {
  timestamp: string;
  total_value: number;
  daily_return: number;
  cumulative_return: number;
  drawdown: number;
}
```

### APIクライアント使用例
```typescript
import { marketDataApi } from '@/lib/api';

// OHLCVデータ取得
const ohlcvData = await marketDataApi.getOHLCV({
  symbol: "BTCUSDT",
  timeframe: "1h",
  limit: 100
});

// 最新価格取得
const latestPrices = await marketDataApi.getLatestPrices(
  "binance",
  "BTCUSDT,ETHUSDT",
  "1h"
);

// 利用可能なシンボル取得
const symbols = await marketDataApi.getSymbols("binance");
```

## パフォーマンス最適化

### キャッシュ戦略
- **TTL**: 60秒
- **キャッシュキー**: exchange:symbol:timeframe:start_time:end_time:limit
- **最大サイズ**: 1000エントリ

### データベース最適化
- **インデックス**: composite index on (exchange, symbol, timeframe, timestamp)
- **ページネーション**: cursor-based pagination（将来実装予定）
- **クエリ最適化**: timestamp DESC ordering

### レート制限
- **制限**: 1000リクエスト/時間/IP
- **ヘッダー**: X-RateLimit-* headers（将来実装予定）

## 今後の予定

### Phase 2.5 予定機能
1. **認証機能**: ユーザー別のAPIアクセス管理
2. **WebSocket**: リアルタイム価格配信
3. **より詳細なページネーション**: cursor-based pagination
4. **レート制限強化**: ユーザー別制限
5. **指標計算API**: SMA, EMA, RSI等のテクニカル指標

### Phase 3 予定機能
1. **カスタム指標**: ユーザー定義指標の計算
2. **アラート機能**: 価格アラート、指標アラート
3. **データエクスポート**: CSV、JSON形式でのデータ出力
4. **バックテスト連携**: 過去データを使用したバックテスト
