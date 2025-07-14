import type { 
  DashboardSummary,
  PerformanceData,
  Strategy,
  AuthResponse
} from '@/types/api';

// 開発環境でのモックデータ
export const mockAuthResponse: AuthResponse = {
  access_token: 'mock-jwt-token',
  token_type: 'Bearer',
  expires_in: 3600,
  user: {
    id: '1',
    username: 'admin',
    email: 'admin@example.com'
  }
};

export const mockDashboardSummary: DashboardSummary = {
  total_value: 125000.50,
  daily_pnl: 2350.25,
  daily_pnl_pct: 0.0192,
  total_pnl: 25000.50,
  active_strategies: 5,
  open_positions: 3,
  active_orders: 2,
  unread_alerts: 1,
  portfolio: {
    name: 'Main Portfolio',
    total_value: 125000.50,
    asset_count: 4,
    created_at: '2024-01-01T00:00:00Z',
    last_rebalance: '2024-01-14T10:30:00Z',
    assets: {
      'BTC': {
        balance: 2.5,
        current_price: 50000.0,
        market_value: 125000.0,
        target_weight: 0.6,
        actual_weight: 0.58,
        asset_type: 'crypto'
      },
      'ETH': {
        balance: 15.0,
        current_price: 3200.0,
        market_value: 48000.0,
        target_weight: 0.3,
        actual_weight: 0.32,
        asset_type: 'crypto'
      }
    }
  },
  recent_trades: [
    {
      symbol: 'BTCUSDT',
      side: 'buy',
      amount: 0.1,
      price: 51000.0,
      pnl: 500.0,
      timestamp: '2024-01-14T15:30:00Z'
    }
  ]
};

export const mockStrategies: Strategy[] = [
  {
    id: 'ema_001',
    name: 'EMA Crossover BTC',
    type: 'ema',
    symbol: 'BTCUSDT',
    timeframe: '1h',
    enabled: true,
    status: 'running',
    parameters: {
      ema_fast: 12,
      ema_slow: 26,
      stop_loss_pct: 0.02,
      take_profit_pct: 0.06
    },
    performance: {
      total_return: 0.15,
      sharpe_ratio: 1.2,
      max_drawdown: 0.08,
      total_trades: 45,
      win_rate: 0.65
    },
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-14T15:30:00Z'
  },
  {
    id: 'rsi_001',
    name: 'RSI Mean Reversion ETH',
    type: 'rsi',
    symbol: 'ETHUSDT',
    timeframe: '15m',
    enabled: true,
    status: 'stopped',
    parameters: {
      rsi_period: 14,
      oversold_threshold: 30,
      overbought_threshold: 70
    },
    performance: {
      total_return: 0.08,
      sharpe_ratio: 0.9,
      max_drawdown: 0.12,
      total_trades: 123,
      win_rate: 0.58
    },
    created_at: '2024-01-05T00:00:00Z',
    updated_at: '2024-01-14T12:00:00Z'
  }
];

export const generateMockPerformanceData = (): PerformanceData[] => {
  const mockData: PerformanceData[] = [];
  const now = new Date();
  
  for (let i = 6; i >= 0; i--) {
    const date = new Date(now);
    date.setDate(date.getDate() - i);
    
    mockData.push({
      timestamp: date.toISOString(),
      total_value: 100000 + Math.random() * 50000,
      daily_return: (Math.random() - 0.5) * 0.1,
      cumulative_return: Math.random() * 0.3,
      drawdown: Math.random() * 0.1
    });
  }
  
  return mockData;
};

// モックデータを使用するかの判定
export const shouldUseMockData = (): boolean => {
  return process.env.NODE_ENV === 'development' && 
         process.env.NEXT_PUBLIC_USE_MOCK_DATA === 'true';
};