'use client';

import { useEffect } from 'react';
import { Grid, Box } from '@mui/material';
import { useDashboardStore } from '@/store/dashboard';
import AppLayout from '@/components/layout/AppLayout';
import DashboardSummary from '@/components/dashboard/DashboardSummary';
import PerformanceChart from '@/components/dashboard/PerformanceChart';

export default function DashboardPage() {
  const { fetchSummary, fetchPerformanceData } = useDashboardStore();

  useEffect(() => {
    // ページが読み込まれたら、ダッシュボードのデータを取得します。
    fetchSummary();
    fetchPerformanceData();
  }, [fetchSummary, fetchPerformanceData]);

  return (
    <AppLayout>
      <Box>
        <DashboardSummary />
        <Grid container spacing={3} sx={{ mt: 1 }}>
          <Grid item xs={12}>
            <PerformanceChart />
          </Grid>
        </Grid>
      </Box>
    </AppLayout>
  );
}
