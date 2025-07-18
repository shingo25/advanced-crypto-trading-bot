import { create } from 'zustand';
import {
  authApi,
  setAuthenticatedState,
  clearAuthenticatedState,
  getAuthenticatedState,
} from '@/lib/api';

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

      setAuthenticatedState(true);

      set({
        user: response.user,
        isAuthenticated: true,
        isLoading: false,
        error: null,
      });
    } catch (error: any) {
      const errorMessage =
        typeof error === 'string'
          ? error
          : error?.response?.data?.detail || error?.message || 'ログインに失敗しました';

      set({
        user: null,
        isAuthenticated: false,
        isLoading: false,
        error: errorMessage,
      });
      throw error;
    }
  },

  logout: () => {
    clearAuthenticatedState();
    set({
      user: null,
      isAuthenticated: false,
      isLoading: false,
      error: null,
    });
  },

  initialize: () => {
    if (typeof window !== 'undefined') {
      const isAuth = getAuthenticatedState();
      if (isAuth) {
        // 実際の実装では、認証状態の有効性を確認する
        set({
          user: {
            id: '1',
            username: 'admin',
            email: 'admin@example.com',
          },
          isAuthenticated: true,
          isLoading: false,
          error: null,
        });
      }
    }
  },

  clearError: () => {
    set({ error: null });
  },
}));
