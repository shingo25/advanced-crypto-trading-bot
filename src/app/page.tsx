'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAuthStore } from '@/store/auth';
import { Box, CircularProgress } from '@mui/material';

export default function Home() {
  const router = useRouter();
  const { isAuthenticated, isLoading } = useAuthStore();
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  useEffect(() => {
    if (mounted && !isLoading) {
      if (isAuthenticated) {
        router.push('/dashboard');
      } else {
        // 自動ログインが失敗した場合のみログインページに遷移
        setTimeout(() => {
          if (!isAuthenticated) {
            router.push('/login');
          }
        }, 2000); // 2秒待って自動ログインの完了を待つ
      }
    }
  }, [isAuthenticated, isLoading, router, mounted]);

  if (!mounted) {
    return null;
  }

  return (
    <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh' }}>
      <CircularProgress />
    </Box>
  );
}
