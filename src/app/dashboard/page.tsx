'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { Grid, Box } from '@mui/material';
import { useAuthStore } from '@/store/auth';
import { useDashboardStore } from '@/store/dashboard';
import AppLayout from '@/components/layout/AppLayout';
import DashboardSummary from '@/components/dashboard/DashboardSummary';
import PerformanceChart from '@/components/dashboard/PerformanceChart';

export default function DashboardPage() {
  const router = useRouter();
  const { isAuthenticated, initialize } = useAuthStore();
  const { fetchSummary, fetchPerformanceData } = useDashboardStore();

  useEffect(() => {
    initialize();
  }, [initialize]);

  useEffect(() => {
    if (!isAuthenticated) {
      router.push('/login');
      return;
    }

    // データを取得
    fetchSummary();
    fetchPerformanceData();
  }, [isAuthenticated, router, fetchSummary, fetchPerformanceData]);

  if (!isAuthenticated) {
    return null;
  }

  return (
    <AppLayout>
      <Box>
        <DashboardSummary />
        <Grid container spacing={3} sx={{ mt: 1 }}>
          <Grid size={12}>
            <PerformanceChart />
          </Grid>
        </Grid>
      </Box>
    </AppLayout>
  );
}
