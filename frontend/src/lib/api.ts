import axios from 'axios';
import type { 
  Strategy, 
  Portfolio, 
  Position, 
  Order, 
  Alert, 
  DashboardSummary,
  PerformanceData,
  AuthResponse,
  ApiError 
} from '@/types/api';

// API設定
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// Axiosインスタンス作成
const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// 認証トークン管理
let authToken: string | null = null;

export const setAuthToken = (token: string) => {
  authToken = token;
  apiClient.defaults.headers.common['Authorization'] = `Bearer ${token}`;
  localStorage.setItem('auth_token', token);
};

export const getAuthToken = (): string | null => {
  if (!authToken && typeof window !== 'undefined') {
    authToken = localStorage.getItem('auth_token');
    if (authToken) {
      apiClient.defaults.headers.common['Authorization'] = `Bearer ${authToken}`;
    }
  }
  return authToken;
};

export const clearAuthToken = () => {
  authToken = null;
  delete apiClient.defaults.headers.common['Authorization'];
  if (typeof window !== 'undefined') {
    localStorage.removeItem('auth_token');
  }
};

// レスポンスインターセプター
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      clearAuthToken();
      // リダイレクト処理は呼び出し元で行う
    }
    return Promise.reject(error);
  }
);

// 認証API
export const authApi = {
  async login(username: string, password: string): Promise<AuthResponse> {
    // 開発用モック
    if (username === 'admin' && password === 'password') {
      const mockResponse: AuthResponse = {
        access_token: 'mock-jwt-token',
        token_type: 'Bearer',
        expires_in: 3600,
        user: {
          id: '1',
          username: 'admin',
          email: 'admin@example.com'
        }
      };
      return mockResponse;
    }
    
    const response = await apiClient.post('/api/auth/login', {
      username,
      password
    });
    return response.data;
  },

  async logout(): Promise<void> {
    clearAuthToken();
  },

  async getProfile(): Promise<any> {
    const response = await apiClient.get('/api/auth/profile');
    return response.data;
  }
};

// ダッシュボードAPI
export const dashboardApi = {
  async getSummary(): Promise<DashboardSummary> {
    // 開発用モック
    const mockSummary: DashboardSummary = {
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
    
    try {
      const response = await apiClient.get('/api/dashboard/summary');
      return response.data;
    } catch (error) {
      console.warn('Using mock data for dashboard summary');
      return mockSummary;
    }
  },

  async getPerformanceHistory(period: string = '7d'): Promise<PerformanceData[]> {
    // 開発用モック
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
    
    try {
      const response = await apiClient.get(`/api/performance/history?period=${period}`);
      return response.data;
    } catch (error) {
      console.warn('Using mock data for performance history');
      return mockData;
    }
  }
};

// 戦略API
export const strategyApi = {
  async getStrategies(): Promise<Strategy[]> {
    // 開発用モック
    const mockStrategies: Strategy[] = [
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
    
    try {
      const response = await apiClient.get('/api/strategies');
      return response.data;
    } catch (error) {
      console.warn('Using mock data for strategies');
      return mockStrategies;
    }
  },

  async getStrategy(id: string): Promise<Strategy> {
    const response = await apiClient.get(`/api/strategies/${id}`);
    return response.data;
  },

  async startStrategy(id: string): Promise<void> {
    console.log(`Starting strategy: ${id}`);
    // モック実装
    await new Promise(resolve => setTimeout(resolve, 500));
    // 実際の実装
    // await apiClient.post(`/api/strategies/${id}/start`);
  },

  async stopStrategy(id: string): Promise<void> {
    console.log(`Stopping strategy: ${id}`);
    // モック実装
    await new Promise(resolve => setTimeout(resolve, 500));
    // 実際の実装
    // await apiClient.post(`/api/strategies/${id}/stop`);
  },

  async updateStrategy(id: string, data: Partial<Strategy>): Promise<Strategy> {
    const response = await apiClient.put(`/api/strategies/${id}`, data);
    return response.data;
  }
};

// ポートフォリオAPI
export const portfolioApi = {
  async getPortfolio(name: string = 'main'): Promise<Portfolio> {
    const response = await apiClient.get(`/api/portfolio/${name}`);
    return response.data;
  },

  async getPositions(): Promise<Position[]> {
    const response = await apiClient.get('/api/positions');
    return response.data;
  },

  async getOrders(): Promise<Order[]> {
    const response = await apiClient.get('/api/orders');
    return response.data;
  }
};

// アラートAPI
export const alertApi = {
  async getAlerts(acknowledged: boolean = false): Promise<Alert[]> {
    const response = await apiClient.get(`/api/alerts?acknowledged=${acknowledged}`);
    return response.data;
  },

  async acknowledgeAlert(id: string): Promise<void> {
    await apiClient.post(`/api/alerts/${id}/acknowledge`);
  },

  async acknowledgeAllAlerts(): Promise<void> {
    await apiClient.post('/api/alerts/acknowledge-all');
  }
};

// WebSocket管理
export class WebSocketManager {
  private ws: WebSocket | null = null;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectDelay = 1000;

  constructor(private url: string) {}

  connect(onMessage: (data: any) => void, onError?: (error: Event) => void) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      return;
    }

    try {
      this.ws = new WebSocket(this.url);

      this.ws.onopen = () => {
        console.log('WebSocket connected');
        this.reconnectAttempts = 0;
      };

      this.ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          onMessage(data);
        } catch (error) {
          console.error('Error parsing WebSocket message:', error);
        }
      };

      this.ws.onclose = () => {
        console.log('WebSocket disconnected');
        this.attemptReconnect(onMessage, onError);
      };

      this.ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        if (onError) {
          onError(error);
        }
      };
    } catch (error) {
      console.error('Error creating WebSocket:', error);
      if (onError) {
        onError(error as Event);
      }
    }
  }

  private attemptReconnect(onMessage: (data: any) => void, onError?: (error: Event) => void) {
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      this.reconnectAttempts++;
      console.log(`Attempting to reconnect (${this.reconnectAttempts}/${this.maxReconnectAttempts})`);
      
      setTimeout(() => {
        this.connect(onMessage, onError);
      }, this.reconnectDelay * this.reconnectAttempts);
    } else {
      console.error('Max reconnection attempts reached');
    }
  }

  disconnect() {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }

  send(data: any) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(data));
    }
  }
}

export default apiClient;