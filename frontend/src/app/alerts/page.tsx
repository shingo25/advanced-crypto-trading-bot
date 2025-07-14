'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { Typography, Box, Paper } from '@mui/material';
import { useAuthStore } from '@/store/auth';
import AppLayout from '@/components/layout/AppLayout';

export default function AlertsPage() {
  const router = useRouter();
  const { isAuthenticated, initialize } = useAuthStore();

  useEffect(() => {
    initialize();
  }, [initialize]);

  useEffect(() => {
    if (!isAuthenticated) {
      router.push('/login');
    }
  }, [isAuthenticated, router]);

  if (!isAuthenticated) {
    return null;
  }

  return (
    <AppLayout>
      <Box>
        <Typography variant="h4" component="h1" gutterBottom>
          アラート
        </Typography>
        <Paper sx={{ p: 3, textAlign: 'center' }}>
          <Typography variant="h6" color="text.secondary">
            アラート画面（実装予定）
          </Typography>
          <Typography variant="body1" color="text.secondary" sx={{ mt: 2 }}>
            システムアラートと通知機能を実装予定です。
          </Typography>
        </Paper>
      </Box>
    </AppLayout>
  );
}