'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { Box, CircularProgress } from '@mui/material';

// 個人利用版：認証不要で直接ダッシュボードにリダイレクト
export default function Home() {
  const router = useRouter();

  useEffect(() => {
    // trailingSlash設定に合わせて末尾に/を付与
    window.location.href = '/dashboard/';
  }, []);

  return (
    <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh' }}>
      <CircularProgress />
      <Box sx={{ ml: 2 }}>
        <span>ダッシュボードにリダイレクト中...</span>
      </Box>
    </Box>
  );
}
