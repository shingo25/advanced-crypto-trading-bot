'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuthStore } from '@/store/auth';
import LoginForm from '@/components/auth/LoginForm';

export default function LoginPage() {
  const router = useRouter();
  const { isAuthenticated, initialize, personalModeInfo } = useAuthStore();

  useEffect(() => {
    initialize();
  }, [initialize]);

  useEffect(() => {
    if (isAuthenticated) {
      router.push('/dashboard');
    }
  }, [isAuthenticated, router]);

  // 個人モードで自動ログイン有効な場合は、ログインページをスキップしてダッシュボードに進む
  useEffect(() => {
    if (personalModeInfo?.personal_mode && personalModeInfo?.auto_login && !isAuthenticated) {
      // initializeで自動ログインが実行されるため、少し待ってからリダイレクト
      const timer = setTimeout(() => {
        if (!isAuthenticated) {
          router.push('/dashboard');
        }
      }, 1000);
      return () => clearTimeout(timer);
    }
  }, [personalModeInfo, isAuthenticated, router]);

  if (isAuthenticated) {
    return null;
  }

  return <LoginForm />;
}
