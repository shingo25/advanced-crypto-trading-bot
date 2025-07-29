# 📚 API Reference

Advanced Crypto Trading Bot APIの完全リファレンスガイドです。

## 🌐 Base URL

- **開発環境**: `http://localhost:8000`
- **本番環境**: `https://your-domain.vercel.app/api`

## 🔑 認証

### JWT Bearer Token

すべての保護されたエンドポイントで必要です。

```http
Authorization: Bearer <your_jwt_token>
```

### トークン取得

```http
POST /auth/login
Content-Type: application/json

{
  "username": "string",
  "password": "string"
}
```

**レスポンス**:

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 3600
}
```

## 📊 認証エンドポイント

### POST /auth/register

新規ユーザー登録

**リクエスト**:

```json
{
  "username": "string",
  "email": "user@example.com",
  "password": "string",
  "confirm_password": "string"
}
```

**レスポンス**:

```json
{
  "id": 1,
  "username": "string",
  "email": "user@example.com",
  "created_at": "2025-01-15T10:30:00Z"
}
```

### POST /auth/refresh

トークン更新

**リクエスト**:

```json
{
  "refresh_token": "string"
}
```

## 💹 取引エンドポイント

### GET /api/trades

取引履歴の取得

**パラメータ**:

- `limit` (optional): 件数制限 (default: 100)
- `offset` (optional): オフセット (default: 0)
- `symbol` (optional): 通貨ペアフィルター

**レスポンス**:

```json
{
  "trades": [
    {
      "id": 1,
      "symbol": "BTCUSDT",
      "side": "buy",
      "amount": "0.001",
      "price": "45000.00",
      "fee": "0.045",
      "timestamp": "2025-01-15T10:30:00Z",
      "strategy": "ema_crossover"
    }
  ],
  "total": 150,
  "has_more": true
}
```

### POST /api/trades

新規取引実行 (ライブ取引)

**リクエスト**:

```json
{
  "symbol": "BTCUSDT",
  "side": "buy",
  "amount": "0.001",
  "type": "market", // market, limit
  "price": "45000.00" // limit注文時のみ
}
```

## 📈 戦略エンドポイント

### GET /api/strategies

利用可能な戦略一覧

**レスポンス**:

```json
{
  "strategies": [
    {
      "id": "ema_crossover",
      "name": "EMA Crossover",
      "description": "短期・長期EMAのクロスオーバー戦略",
      "parameters": [
        {
          "name": "fast_period",
          "type": "integer",
          "default": 12,
          "min": 5,
          "max": 50
        },
        {
          "name": "slow_period",
          "type": "integer",
          "default": 26,
          "min": 10,
          "max": 200
        }
      ]
    }
  ]
}
```

### POST /api/strategies/{strategy_id}/backtest

バックテスト実行

**リクエスト**:

```json
{
  "symbol": "BTCUSDT",
  "timeframe": "1h",
  "start_date": "2024-01-01",
  "end_date": "2024-12-31",
  "initial_capital": 10000,
  "parameters": {
    "fast_period": 12,
    "slow_period": 26
  }
}
```

**レスポンス**:

```json
{
  "backtest_id": "bt_123456",
  "status": "running",
  "estimated_completion": "2025-01-15T10:35:00Z"
}
```

### GET /api/strategies/backtest/{backtest_id}

バックテスト結果取得

**レスポンス**:

```json
{
  "id": "bt_123456",
  "status": "completed",
  "results": {
    "total_return": 0.1234,
    "sharpe_ratio": 1.45,
    "max_drawdown": 0.0892,
    "win_rate": 0.67,
    "total_trades": 45,
    "profit_factor": 1.89
  },
  "equity_curve": [
    {
      "timestamp": "2024-01-01T00:00:00Z",
      "equity": 10000
    }
  ],
  "trades": [
    {
      "timestamp": "2024-01-15T10:30:00Z",
      "symbol": "BTCUSDT",
      "side": "buy",
      "price": 45000,
      "amount": 0.001,
      "pnl": 12.34
    }
  ]
}
```

## 📊 マーケットデータエンドポイント

### GET /api/market/ohlcv/{symbol}

OHLCV価格データ取得

**パラメータ**:

- `timeframe`: 時間足 (1m, 5m, 15m, 1h, 4h, 1d)
- `start_time` (optional): 開始時刻
- `end_time` (optional): 終了時刻
- `limit` (optional): 件数 (default: 100, max: 1000)

**レスポンス**:

```json
{
  "symbol": "BTCUSDT",
  "timeframe": "1h",
  "data": [
    {
      "timestamp": "2025-01-15T10:00:00Z",
      "open": "45000.00",
      "high": "45500.00",
      "low": "44800.00",
      "close": "45200.00",
      "volume": "123.456"
    }
  ]
}
```

### GET /api/market/ticker/{symbol}

現在価格取得

**レスポンス**:

```json
{
  "symbol": "BTCUSDT",
  "price": "45200.00",
  "change_24h": "0.0234",
  "volume_24h": "12345.67",
  "timestamp": "2025-01-15T10:30:00Z"
}
```

## 🔧 設定エンドポイント

### GET /api/settings/exchanges

取引所設定一覧

**レスポンス**:

```json
{
  "exchanges": [
    {
      "id": "binance",
      "name": "Binance",
      "enabled": true,
      "api_configured": true,
      "supported_symbols": ["BTCUSDT", "ETHUSDT"]
    }
  ]
}
```

### POST /api/settings/exchanges/{exchange_id}/configure

取引所API設定

**リクエスト**:

```json
{
  "api_key": "string",
  "api_secret": "string",
  "passphrase": "string", // OKXなど必要な場合
  "sandbox": true // テストネット使用
}
```

## 🚨 リスク管理エンドポイント

### GET /api/risk/limits

現在のリスク制限設定

**レスポンス**:

```json
{
  "max_position_size": 0.1,
  "max_daily_loss": 0.05,
  "max_drawdown": 0.15,
  "allowed_symbols": ["BTCUSDT", "ETHUSDT"],
  "trading_enabled": true
}
```

### POST /api/risk/limits

リスク制限設定更新

**リクエスト**:

```json
{
  "max_position_size": 0.1,
  "max_daily_loss": 0.05,
  "max_drawdown": 0.15
}
```

## 📱 WebSocket API

### 価格データストリーム

```javascript
// 接続
const ws = new WebSocket('ws://localhost:8000/ws/prices/BTCUSDT');

// メッセージ受信
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('Price update:', data);
};

// データ形式
{
  "symbol": "BTCUSDT",
  "price": "45200.00",
  "timestamp": "2025-01-15T10:30:00Z",
  "change": "0.0234"
}
```

### 取引実行通知

```javascript
const ws = new WebSocket('ws://localhost:8000/ws/trades');

// 取引実行通知
{
  "type": "trade_executed",
  "trade": {
    "id": 123,
    "symbol": "BTCUSDT",
    "side": "buy",
    "amount": "0.001",
    "price": "45000.00"
  }
}
```

## ❌ エラーレスポンス

すべてのエラーは以下の形式で返されます：

```json
{
  "error": {
    "code": "INVALID_PARAMETER",
    "message": "パラメータが無効です",
    "details": {
      "field": "amount",
      "reason": "金額は0より大きい値を指定してください"
    }
  },
  "timestamp": "2025-01-15T10:30:00Z"
}
```

### エラーコード一覧

| コード                 | 説明                     |
| ---------------------- | ------------------------ |
| `UNAUTHORIZED`         | 認証が必要です           |
| `FORBIDDEN`            | アクセス権限がありません |
| `INVALID_PARAMETER`    | パラメータが無効です     |
| `RESOURCE_NOT_FOUND`   | リソースが見つかりません |
| `EXCHANGE_ERROR`       | 取引所APIエラー          |
| `INSUFFICIENT_BALANCE` | 残高不足                 |
| `RATE_LIMITED`         | レート制限に達しました   |

## 📝 レート制限

- **認証済みエンドポイント**: 1000 requests/minute
- **公開エンドポイント**: 100 requests/minute
- **WebSocket**: 接続数制限 10 connections/user

制限に達した場合、`429 Too Many Requests`が返されます。

## 🔍 SDKサンプル

### Python

```python
import requests

class TradingBotAPI:
    def __init__(self, base_url, token):
        self.base_url = base_url
        self.headers = {"Authorization": f"Bearer {token}"}

    def get_trades(self, limit=100):
        response = requests.get(
            f"{self.base_url}/api/trades",
            params={"limit": limit},
            headers=self.headers
        )
        return response.json()

# 使用例
api = TradingBotAPI("http://localhost:8000", "your_token")
trades = api.get_trades()
```

### JavaScript

```javascript
class TradingBotAPI {
  constructor(baseUrl, token) {
    this.baseUrl = baseUrl;
    this.headers = {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    };
  }

  async getTrades(limit = 100) {
    const response = await fetch(`${this.baseUrl}/api/trades?limit=${limit}`, {
      headers: this.headers,
    });
    return response.json();
  }
}

// 使用例
const api = new TradingBotAPI("http://localhost:8000", "your_token");
const trades = await api.getTrades();
```

---

**このAPIリファレンスは継続的に更新されます。** 最新の情報は `/docs` エンドポイントでも確認できます。
