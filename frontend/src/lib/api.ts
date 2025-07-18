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
