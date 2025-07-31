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
  autoLogin: () => Promise<void>;
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

  autoLogin: async () => {
    const { isAuthenticated } = get();

    // 既に認証済みの場合は何もしない
    if (isAuthenticated) return;

    set({ isLoading: true, error: null });

    try {
      // デモユーザーで自動ログイン
      const response = await authApi.login('demo', 'demo');

      setAuthenticatedState(true);

      set({
        user: response.user,
        isAuthenticated: true,
        isLoading: false,
        error: null,
      });

      console.log('自動ログイン成功: デモユーザーでログインしました');
    } catch (error: any) {
      console.warn('自動ログインに失敗:', error);
      // 自動ログインの失敗は通常のエラーとして扱わない
      set({
        user: null,
        isAuthenticated: false,
        isLoading: false,
        error: null, // エラーをユーザーに表示しない
      });
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
