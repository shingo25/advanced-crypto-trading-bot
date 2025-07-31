'use client';

import { useEffect } from 'react';
import { Paper, Typography, Box, ButtonGroup, Button, CircularProgress } from '@mui/material';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Area,
  AreaChart,
} from 'recharts';
import { useDashboardStore } from '@/store/dashboard';

interface PerformanceChartProps {
  period?: string;
}

export default function PerformanceChart({ period = '7d' }: PerformanceChartProps) {
  const { performanceData, fetchPerformanceData, isLoading } = useDashboardStore();

  useEffect(() => {
    fetchPerformanceData(period);
  }, [period, fetchPerformanceData]);

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('ja-JP', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(value);
  };

  const formatPercent = (value: number) => {
    return new Intl.NumberFormat('ja-JP', {
      style: 'percent',
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(value);
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('ja-JP', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  // チャートデータの準備
  const chartData = performanceData.map((item) => ({
    ...item,
    date: formatDate(item.timestamp),
    formattedValue: formatCurrency(item.total_value),
    formattedReturn: formatPercent(item.cumulative_return),
  }));

  const CustomTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
      return (
        <Box
          sx={{
            bgcolor: 'background.paper',
            p: 1,
            border: 1,
            borderColor: 'divider',
            borderRadius: 1,
            boxShadow: 1,
          }}
        >
          <Typography variant="body2" gutterBottom>
            {label}
          </Typography>
          {payload.map((entry: any, index: number) => (
            <Typography key={index} variant="body2" sx={{ color: entry.color }}>
              {entry.name}:{' '}
              {entry.name === '累計リターン'
                ? formatPercent(entry.value)
                : formatCurrency(entry.value)}
            </Typography>
          ))}
        </Box>
      );
    }
    return null;
  };

  return (
    <Paper sx={{ p: 2, height: 400 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
        <Typography variant="h6">パフォーマンス推移</Typography>
        <ButtonGroup size="small">
          <Button variant={period === '1d' ? 'contained' : 'outlined'}>1日</Button>
          <Button variant={period === '7d' ? 'contained' : 'outlined'}>7日</Button>
          <Button variant={period === '30d' ? 'contained' : 'outlined'}>30日</Button>
          <Button variant={period === '90d' ? 'contained' : 'outlined'}>90日</Button>
        </ButtonGroup>
      </Box>

      {isLoading ? (
        <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: 300 }}>
          <CircularProgress />
        </Box>
      ) : chartData.length > 0 ? (
        <ResponsiveContainer width="100%" height={300}>
          <AreaChart data={chartData}>
            <defs>
              <linearGradient id="colorValue" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#8884d8" stopOpacity={0.8} />
                <stop offset="95%" stopColor="#8884d8" stopOpacity={0.1} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="date" tick={{ fontSize: 12 }} interval="preserveStartEnd" />
            <YAxis yAxisId="left" tick={{ fontSize: 12 }} tickFormatter={formatCurrency} />
            <YAxis
              yAxisId="right"
              orientation="right"
              tick={{ fontSize: 12 }}
              tickFormatter={formatPercent}
            />
            <Tooltip content={<CustomTooltip />} />
            <Area
              yAxisId="left"
              type="monotone"
              dataKey="total_value"
              stroke="#8884d8"
              fillOpacity={1}
              fill="url(#colorValue)"
              name="総資産"
            />
            <Line
              yAxisId="right"
              type="monotone"
              dataKey="cumulative_return"
              stroke="#82ca9d"
              strokeWidth={2}
              dot={false}
              name="累計リターン"
            />
          </AreaChart>
        </ResponsiveContainer>
      ) : (
        <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: 300 }}>
          <Typography color="text.secondary">データがありません</Typography>
        </Box>
      )}
    </Paper>
  );
}
