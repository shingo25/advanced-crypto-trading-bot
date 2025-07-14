import { create } from 'zustand';
import { authApi, setAuthToken, clearAuthToken, getAuthToken } from '@/lib/api';

interface User {
  id: string;
  username: string;
  email: string;
}

interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
  
  // アクション
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
  initialize: () => void;
  clearError: () => void;
}

export const useAuthStore = create<AuthState>((set, get) => ({
  user: null,
  isAuthenticated: false,
  isLoading: false,
  error: null,

  login: async (username: string, password: string) => {
    set({ isLoading: true, error: null });
    
    try {
      const response = await authApi.login(username, password);
      
      setAuthToken(response.access_token);
      
      set({
        user: response.user,
        isAuthenticated: true,
        isLoading: false,
        error: null
      });
    } catch (error: any) {
      set({
        user: null,
        isAuthenticated: false,
        isLoading: false,
        error: error.response?.data?.detail || 'ログインに失敗しました'
      });
      throw error;
    }
  },

  logout: () => {
    clearAuthToken();
    set({
      user: null,
      isAuthenticated: false,
      isLoading: false,
      error: null
    });
  },

  initialize: () => {
    const token = getAuthToken();
    if (token) {
      // 実際の実装では、トークンの有効性を確認する
      set({
        user: {
          id: '1',
          username: 'admin',
          email: 'admin@example.com'
        },
        isAuthenticated: true,
        isLoading: false,
        error: null
      });
    }
  },

  clearError: () => {
    set({ error: null });
  }
}));