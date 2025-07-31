'use client';

import { useEffect } from 'react';
import { useAuthStore } from '@/store/auth';

interface AuthProviderProps {
  children: React.ReactNode;
}

export function AuthProvider({ children }: AuthProviderProps) {
  const { autoLogin, initialize, isAuthenticated } = useAuthStore();

  useEffect(() => {
    // 初期化処理
    initialize();

    // 認証されていない場合は自動ログインを実行
    if (!isAuthenticated) {
      autoLogin();
    }
  }, [autoLogin, initialize, isAuthenticated]);

  return <>{children}</>;
}
