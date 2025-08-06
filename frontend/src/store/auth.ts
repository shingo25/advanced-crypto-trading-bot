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
  personalModeInfo: any;

  // アクション
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
  initialize: () => void;
  clearError: () => void;
  autoLogin: () => Promise<void>;
  getPersonalModeInfo: () => Promise<void>;
}

export const useAuthStore = create<AuthState>((set, get) => ({
  user: null,
  isAuthenticated: false,
  isLoading: false,
  error: null,
  personalModeInfo: null,

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

  initialize: async () => {
    if (typeof window !== 'undefined') {
      try {
        // 個人モード情報を取得
        await get().getPersonalModeInfo();
        
        const personalModeInfo = get().personalModeInfo;
        
        // 個人モードで自動ログインが有効な場合
        if (personalModeInfo?.personal_mode && personalModeInfo?.auto_login) {
          await get().autoLogin();
        } else {
          // 通常の認証状態確認
          const isAuth = getAuthenticatedState();
          if (isAuth) {
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
      } catch (error) {
        console.log('Initialize auth failed (possibly normal):', error);
      }
    }
  },

  autoLogin: async () => {
    set({ isLoading: true, error: null });
    
    try {
      const response = await authApi.autoLogin();
      
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
          : error?.response?.data?.detail || error?.message || '自動ログインに失敗しました';
      
      set({
        user: null,
        isAuthenticated: false,
        isLoading: false,
        error: errorMessage,
      });
      throw error;
    }
  },

  getPersonalModeInfo: async () => {
    try {
      const personalModeInfo = await authApi.getPersonalModeInfo();
      set({ personalModeInfo });
    } catch (error) {
      console.log('Failed to get personal mode info:', error);
      set({ personalModeInfo: { personal_mode: false, auto_login: false } });
    }
  },

  clearError: () => {
    set({ error: null });
  },
}));
