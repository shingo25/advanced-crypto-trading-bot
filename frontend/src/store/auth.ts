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

// 個人利用版：常に認証済み状態を返すように無効化
export const useAuthStore = create<AuthState>((set) => ({
  user: { id: 'local-user', username: 'local', email: 'local@example.com' }, // ダミーユーザー情報
  isAuthenticated: true, // 常に認証済み
  isLoading: false,
  error: null,
  login: async () => {}, // 何もしない
  logout: () => {}, // 何もしない
  initialize: () => {}, // 何もしない
  clearError: () => {}, // 何もしない
}));
