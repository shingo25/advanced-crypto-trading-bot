// API型定義
export interface Strategy {
  id: string;
  name: string;
  type: string;
  symbol: string;
  timeframe: string;
  enabled: boolean;
  status: 'running' | 'stopped' | 'error';
  parameters: Record<string, any>;
  performance: {
    total_return: number;
    sharpe_ratio: number;
    max_drawdown: number;
    total_trades: number;
    win_rate: number;
  };
  created_at: string;
  updated_at: string;
}

export interface Portfolio {
  name: string;
  total_value: number;
  asset_count: number;
  created_at: string;
  last_rebalance: string | null;
  assets: Record<
    string,
    {
      balance: number;
      current_price: number;
      market_value: number;
      target_weight: number;
      actual_weight: number;
      asset_type: string;
    }
  >;
}

export interface Position {
  symbol: string;
  side: 'buy' | 'sell';
  amount: number;
  entry_price: number;
  current_price: number;
  unrealized_pnl: number;
  realized_pnl: number;
  created_at: string;
  strategy_name: string | null;
}

export interface Order {
  id: string;
  symbol: string;
  side: 'buy' | 'sell';
  order_type: 'market' | 'limit' | 'stop_loss' | 'take_profit';
  amount: number;
  price: number | null;
  status: 'pending' | 'filled' | 'cancelled' | 'rejected';
  filled_amount: number;
  filled_price: number | null;
  created_at: string;
  strategy_name: string | null;
}

export interface Alert {
  id: string;
  alert_type: string;
  level: 'info' | 'warning' | 'error' | 'critical';
  title: string;
  message: string;
  symbol: string | null;
  strategy_name: string | null;
  data: Record<string, any>;
  created_at: string;
  acknowledged: boolean;
}

export interface DashboardSummary {
  total_value: number;
  daily_pnl: number;
  daily_pnl_pct: number;
  total_pnl: number;
  active_strategies: number;
  open_positions: number;
  active_orders: number;
  unread_alerts: number;
  portfolio: Portfolio;
  recent_trades: Array<{
    symbol: string;
    side: string;
    amount: number;
    price: number;
    pnl: number;
    timestamp: string;
  }>;
}

export interface PerformanceData {
  timestamp: string;
  total_value: number;
  daily_return: number;
  cumulative_return: number;
  drawdown: number;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
  user: {
    id: string;
    username: string;
    email: string;
  };
}

export interface ApiError {
  detail: string;
  status_code: number;
}

export interface WebSocketMessage {
  type: 'dashboard_update' | 'strategy_update' | 'alert' | 'trade';
  data: any;
  timestamp: string;
}
