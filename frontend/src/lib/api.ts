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
  ApiError,
  OHLCVData,
  MarketDataParams,
  LatestPrice,
} from '@/types/api';
import {
  mockDashboardSummary,
  mockStrategies,
  generateMockPerformanceData,
  shouldUseMockData,
} from '@/lib/mockData';

// API設定
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// Axiosインスタンス作成
const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
  withCredentials: true, // httpOnlyクッキーを送信するために必要
});

// 認証状態管理（httpOnlyクッキー使用のため、トークンは直接管理しない）
let isAuthenticated = false;

export const setAuthenticatedState = (authenticated: boolean) => {
  isAuthenticated = authenticated;
};

export const getAuthenticatedState = (): boolean => {
  return isAuthenticated;
};

export const clearAuthenticatedState = () => {
  isAuthenticated = false;
};

// レスポンスインターセプター
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      clearAuthenticatedState();
      // リダイレクト処理は呼び出し元で行う
      if (typeof window !== 'undefined') {
        window.location.href = '/login';
      }
    }
    return Promise.reject(error);
  }
);

// 認証API
export const authApi = {
  async login(username: string, password: string): Promise<AuthResponse> {
    try {
      const response = await apiClient.post('/api/auth/login', {
        username,
        password,
      });

      setAuthenticatedState(true);
      return response.data;
    } catch (error) {
      clearAuthenticatedState();
      throw error;
    }
  },

  async logout(): Promise<void> {
    try {
      await apiClient.post('/api/auth/logout');
    } catch (error) {
      console.warn('Logout request failed:', error);
    } finally {
      clearAuthenticatedState();
    }
  },

  async getProfile(): Promise<any> {
    const response = await apiClient.get('/api/auth/me');
    return response.data;
  },

  async refreshToken(): Promise<void> {
    try {
      await apiClient.post('/api/auth/refresh');
      setAuthenticatedState(true);
    } catch (error) {
      clearAuthenticatedState();
      throw error;
    }
  },
};

// ダッシュボードAPI
export const dashboardApi = {
  async getSummary(): Promise<DashboardSummary> {
    if (shouldUseMockData()) {
      return mockDashboardSummary;
    }

    try {
      const response = await apiClient.get('/api/dashboard/summary');
      return response.data;
    } catch (error) {
      console.warn('API call failed, using mock data for dashboard summary');
      return mockDashboardSummary;
    }
  },

  async getPerformanceHistory(period: string = '7d'): Promise<PerformanceData[]> {
    if (shouldUseMockData()) {
      return generateMockPerformanceData();
    }

    try {
      const response = await apiClient.get(`/api/performance/history?period=${period}`);
      return response.data;
    } catch (error) {
      console.warn('API call failed, using mock data for performance history');
      return generateMockPerformanceData();
    }
  },
};

// 戦略API
export const strategyApi = {
  async getStrategies(): Promise<Strategy[]> {
    if (shouldUseMockData()) {
      return mockStrategies;
    }

    try {
      const response = await apiClient.get('/api/strategies');
      return response.data;
    } catch (error) {
      console.warn('API call failed, using mock data for strategies');
      return mockStrategies;
    }
  },

  async getStrategy(id: string): Promise<Strategy> {
    if (shouldUseMockData()) {
      const strategy = mockStrategies.find((s) => s.id === id);
      if (!strategy) {
        throw new Error(`Strategy with id ${id} not found`);
      }
      return strategy;
    }

    const response = await apiClient.get(`/api/strategies/${id}`);
    return response.data;
  },

  async startStrategy(id: string): Promise<void> {
    if (shouldUseMockData()) {
      console.log(`Mock: Starting strategy ${id}`);
      await new Promise((resolve) => setTimeout(resolve, 500));
      return;
    }

    await apiClient.post(`/api/strategies/${id}/start`);
  },

  async stopStrategy(id: string): Promise<void> {
    if (shouldUseMockData()) {
      console.log(`Mock: Stopping strategy ${id}`);
      await new Promise((resolve) => setTimeout(resolve, 500));
      return;
    }

    await apiClient.post(`/api/strategies/${id}/stop`);
  },

  async updateStrategy(id: string, data: Partial<Strategy>): Promise<Strategy> {
    if (shouldUseMockData()) {
      const strategy = mockStrategies.find((s) => s.id === id);
      if (!strategy) {
        throw new Error(`Strategy with id ${id} not found`);
      }
      return { ...strategy, ...data };
    }

    const response = await apiClient.put(`/api/strategies/${id}`, data);
    return response.data;
  },
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
  },
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
  },
};

// マーケットデータAPI
export const marketDataApi = {
  async getOHLCV(params: MarketDataParams): Promise<OHLCVData[]> {
    const queryParams = new URLSearchParams();

    if (params.exchange) queryParams.append('exchange', params.exchange);
    queryParams.append('symbol', params.symbol);
    if (params.timeframe) queryParams.append('timeframe', params.timeframe);
    if (params.limit) queryParams.append('limit', params.limit.toString());
    if (params.start_time) queryParams.append('start_time', params.start_time);
    if (params.end_time) queryParams.append('end_time', params.end_time);

    const response = await apiClient.get(`/api/market-data/ohlcv?${queryParams}`);
    return response.data;
  },

  async getSymbols(exchange: string = 'binance'): Promise<{ symbols: string[] }> {
    const response = await apiClient.get(`/api/market-data/symbols?exchange=${exchange}`);
    return response.data;
  },

  async getTimeframes(
    exchange: string = 'binance',
    symbol?: string
  ): Promise<{ timeframes: string[] }> {
    const queryParams = new URLSearchParams();
    queryParams.append('exchange', exchange);
    if (symbol) queryParams.append('symbol', symbol);

    const response = await apiClient.get(`/api/market-data/timeframes?${queryParams}`);
    return response.data;
  },

  async getLatestPrices(
    exchange: string = 'binance',
    symbols?: string,
    timeframe: string = '1h'
  ): Promise<{ latest_prices: LatestPrice[] }> {
    const queryParams = new URLSearchParams();
    queryParams.append('exchange', exchange);
    queryParams.append('timeframe', timeframe);
    if (symbols) queryParams.append('symbols', symbols);

    const response = await apiClient.get(`/api/market-data/latest?${queryParams}`);
    return response.data;
  },
};

// Phase3 新機能: 戦略API拡張
export const strategyApiExtended = {
  // 戦略の有効/無効切り替え
  async toggleStrategy(id: string): Promise<Strategy> {
    const response = await apiClient.patch(`/strategies/${id}/toggle`);
    return response.data;
  },

  // パラメータ更新
  async updateStrategyParameters(id: string, parameters: Record<string, any>): Promise<Strategy> {
    const response = await apiClient.patch(`/strategies/${id}/parameters`, parameters);
    return response.data;
  },

  // ステータス詳細取得
  async getStrategyStatusDetails(id: string): Promise<any> {
    const response = await apiClient.get(`/strategies/${id}/status`);
    return response.data;
  },

  // アクティブな戦略のみ取得
  async getActiveStrategies(): Promise<Strategy[]> {
    const response = await apiClient.get('/strategies/active');
    return response.data;
  },
};

// Phase3 新機能: ポートフォリオAPI拡張
export const portfolioApiExtended = {
  // ポートフォリオサマリー取得
  async getPortfolioSummary(): Promise<any> {
    const response = await apiClient.get('/api/portfolio/');
    return response.data;
  },

  // 戦略配分管理
  async addStrategyToPortfolio(strategyData: any): Promise<any> {
    const response = await apiClient.post('/api/portfolio/strategies', strategyData);
    return response.data;
  },

  async removeStrategyFromPortfolio(strategyName: string): Promise<any> {
    const response = await apiClient.delete(`/api/portfolio/strategies/${strategyName}`);
    return response.data;
  },

  async updateStrategyStatus(strategyName: string, status: string): Promise<any> {
    const response = await apiClient.patch(`/api/portfolio/strategies/${strategyName}/status`, { status });
    return response.data;
  },

  // パフォーマンス追跡
  async getStrategyPerformance(strategyName: string): Promise<any> {
    const response = await apiClient.get(`/api/portfolio/strategies/${strategyName}/performance`);
    return response.data;
  },

  // 相関行列取得
  async getCorrelationMatrix(): Promise<any> {
    const response = await apiClient.get('/api/portfolio/correlation');
    return response.data;
  },

  // リバランシング提案
  async getRebalanceRecommendations(): Promise<any> {
    const response = await apiClient.post('/api/portfolio/rebalance');
    return response.data;
  },

  // リスクレポート
  async getRiskReport(): Promise<any> {
    const response = await apiClient.get('/api/portfolio/risk-report');
    return response.data;
  },

  // ポートフォリオ最適化
  async getPortfolioOptimization(): Promise<any> {
    const response = await apiClient.post('/api/portfolio/optimize');
    return response.data;
  },

  // ヘルスチェック
  async getPortfolioHealth(): Promise<any> {
    const response = await apiClient.get('/api/portfolio/health');
    return response.data;
  },
};

// Phase3 新機能: リスク管理API
export const riskApi = {
  // リスクサマリー取得
  async getRiskSummary(): Promise<any> {
    const response = await apiClient.get('/api/risk/summary');
    return response.data;
  },

  // VaR計算
  async calculateVaR(params: {
    portfolio_id?: string;
    confidence_level?: number;
    time_horizon?: string;
    method?: 'historical' | 'parametric' | 'monte_carlo';
  }): Promise<any> {
    const response = await apiClient.post('/api/risk/var', params);
    return response.data;
  },

  // ストレステスト実行
  async runStressTest(params: {
    scenario: string;
    parameters?: Record<string, any>;
  }): Promise<any> {
    const response = await apiClient.post('/api/risk/stress-test', params);
    return response.data;
  },

  // ポジションサイジング取得
  async getPositionSizing(params: {
    strategy_name: string;
    symbol: string;
    entry_price: number;
    direction?: 'long' | 'short';
  }): Promise<any> {
    const queryParams = new URLSearchParams();
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined) queryParams.append(key, value.toString());
    });

    const response = await apiClient.get(`/api/risk/position-sizing?${queryParams}`);
    return response.data;
  },

  // 利用可能なシナリオ取得
  async getAvailableScenarios(): Promise<any> {
    const response = await apiClient.get('/api/risk/scenarios');
    return response.data;
  },

  // ヘルスチェック
  async getRiskHealth(): Promise<any> {
    const response = await apiClient.get('/api/risk/health');
    return response.data;
  },
};

// Phase3 新機能: アラートAPI拡張
export const alertApiExtended = {
  // アラート作成
  async createAlert(alertData: {
    name: string;
    target: string;
    symbol?: string;
    condition: 'GREATER_THAN' | 'LESS_THAN' | 'EQUALS' | 'NOT_EQUALS';
    value: number;
    notification_channels?: string[];
    level?: 'info' | 'warning' | 'critical';
    enabled?: boolean;
  }): Promise<any> {
    const response = await apiClient.post('/api/alerts/', alertData);
    return response.data;
  },

  // アラート一覧取得
  async getAlerts(enabledOnly?: boolean): Promise<any[]> {
    const params = enabledOnly ? '?enabled_only=true' : '';
    const response = await apiClient.get(`/api/alerts/${params}`);
    return response.data;
  },

  // アラート詳細取得
  async getAlert(alertId: string): Promise<any> {
    const response = await apiClient.get(`/api/alerts/${alertId}`);
    return response.data;
  },

  // アラート更新
  async updateAlert(alertId: string, alertData: Partial<any>): Promise<any> {
    const response = await apiClient.put(`/api/alerts/${alertId}`, alertData);
    return response.data;
  },

  // アラート削除
  async deleteAlert(alertId: string): Promise<any> {
    const response = await apiClient.delete(`/api/alerts/${alertId}`);
    return response.data;
  },

  // アラート有効/無効切り替え
  async toggleAlert(alertId: string): Promise<any> {
    const response = await apiClient.patch(`/api/alerts/${alertId}/toggle`);
    return response.data;
  },

  // アラートテスト配信
  async testAlert(alertId: string): Promise<any> {
    const response = await apiClient.post(`/api/alerts/${alertId}/test`);
    return response.data;
  },

  // アラート履歴取得
  async getAlertHistory(params?: { limit?: number; alert_id?: string }): Promise<any[]> {
    const queryParams = new URLSearchParams();
    if (params) {
      Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined) queryParams.append(key, value.toString());
      });
    }

    const response = await apiClient.get(`/api/alerts/history?${queryParams}`);
    return response.data;
  },

  // アラート統計取得
  async getAlertStatistics(): Promise<any> {
    const response = await apiClient.get('/api/alerts/stats');
    return response.data;
  },

  // ヘルスチェック
  async getAlertHealth(): Promise<any> {
    const response = await apiClient.get('/api/alerts/health');
    return response.data;
  },
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
      console.log(
        `Attempting to reconnect (${this.reconnectAttempts}/${this.maxReconnectAttempts})`
      );

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
