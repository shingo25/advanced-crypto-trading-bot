'use client';

import { Grid, Paper, Typography, Box, Card, CardContent, Chip, Avatar } from '@mui/material';
import {
  TrendingUp,
  TrendingDown,
  AccountBalanceWallet,
  PlayArrow,
  SwapHoriz,
  Notifications,
} from '@mui/icons-material';
import { useDashboardStore } from '@/store/dashboard';

interface SummaryCardProps {
  title: string;
  value: string;
  subtitle?: string;
  icon: React.ReactNode;
  color?: 'success' | 'error' | 'warning' | 'info';
  trend?: 'up' | 'down' | 'neutral';
}

function SummaryCard({ title, value, subtitle, icon, color = 'info', trend }: SummaryCardProps) {
  const getTrendIcon = () => {
    switch (trend) {
      case 'up':
        return <TrendingUp sx={{ fontSize: 16, color: 'success.main' }} />;
      case 'down':
        return <TrendingDown sx={{ fontSize: 16, color: 'error.main' }} />;
      default:
        return null;
    }
  };

  return (
    <Card elevation={2}>
      <CardContent>
        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <Box>
            <Typography color="text.secondary" variant="body2">
              {title}
            </Typography>
            <Typography variant="h4" component="div" sx={{ fontWeight: 'bold' }}>
              {value}
            </Typography>
            {subtitle && (
              <Box sx={{ display: 'flex', alignItems: 'center', mt: 1 }}>
                {getTrendIcon()}
                <Typography variant="body2" color="text.secondary" sx={{ ml: 0.5 }}>
                  {subtitle}
                </Typography>
              </Box>
            )}
          </Box>
          <Avatar sx={{ bgcolor: `${color}.main`, width: 56, height: 56 }}>{icon}</Avatar>
        </Box>
      </CardContent>
    </Card>
  );
}

export default function DashboardSummary() {
  const { summary } = useDashboardStore();

  if (!summary) {
    return (
      <Typography variant="h6" color="text.secondary">
        データを読み込み中...
      </Typography>
    );
  }

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('ja-JP', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(amount);
  };

  const formatPercent = (value: number) => {
    return new Intl.NumberFormat('ja-JP', {
      style: 'percent',
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(value);
  };

  const dailyTrend = summary.daily_pnl > 0 ? 'up' : summary.daily_pnl < 0 ? 'down' : 'neutral';

  return (
    <Box>
      <Typography variant="h4" component="h1" gutterBottom>
        ダッシュボード
      </Typography>

      <Grid container spacing={3}>
        {/* 総資産 */}
        <Grid size={{ xs: 12, sm: 6, md: 3 }}>
          <SummaryCard
            title="総資産"
            value={formatCurrency(summary.total_value)}
            subtitle={`${formatCurrency(summary.daily_pnl)} (${formatPercent(summary.daily_pnl_pct)})`}
            icon={<AccountBalanceWallet />}
            color="info"
            trend={dailyTrend}
          />
        </Grid>

        {/* 累計損益 */}
        <Grid size={{ xs: 12, sm: 6, md: 3 }}>
          <SummaryCard
            title="累計損益"
            value={formatCurrency(summary.total_pnl)}
            subtitle="開始からの累計"
            icon={<TrendingUp />}
            color={summary.total_pnl > 0 ? 'success' : 'error'}
            trend={summary.total_pnl > 0 ? 'up' : 'down'}
          />
        </Grid>

        {/* 稼働戦略数 */}
        <Grid size={{ xs: 12, sm: 6, md: 3 }}>
          <SummaryCard
            title="稼働戦略"
            value={summary.active_strategies.toString()}
            subtitle="個の戦略が稼働中"
            icon={<PlayArrow />}
            color="success"
          />
        </Grid>

        {/* 未読アラート */}
        <Grid size={{ xs: 12, sm: 6, md: 3 }}>
          <SummaryCard
            title="未読アラート"
            value={summary.unread_alerts.toString()}
            subtitle="件の未読アラート"
            icon={<Notifications />}
            color={summary.unread_alerts > 0 ? 'warning' : 'info'}
          />
        </Grid>

        {/* オープンポジション */}
        <Grid size={{ xs: 12, sm: 6, md: 3 }}>
          <SummaryCard
            title="オープンポジション"
            value={summary.open_positions.toString()}
            subtitle="個のポジション"
            icon={<SwapHoriz />}
            color="info"
          />
        </Grid>

        {/* アクティブ注文 */}
        <Grid size={{ xs: 12, sm: 6, md: 3 }}>
          <SummaryCard
            title="アクティブ注文"
            value={summary.active_orders.toString()}
            subtitle="個の注文"
            icon={<SwapHoriz />}
            color="warning"
          />
        </Grid>
      </Grid>

      {/* ポートフォリオ概要 */}
      <Paper sx={{ mt: 3, p: 2 }}>
        <Typography variant="h6" gutterBottom>
          ポートフォリオ概要
        </Typography>
        <Grid container spacing={2}>
          {Object.entries(summary.portfolio.assets).map(([symbol, asset]) => (
            <Grid size={{ xs: 12, sm: 6, md: 4 }} key={symbol}>
              <Box
                sx={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  p: 1,
                  border: 1,
                  borderColor: 'divider',
                  borderRadius: 1,
                }}
              >
                <Box>
                  <Typography variant="subtitle1" fontWeight="bold">
                    {symbol}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    {asset.balance.toFixed(4)}
                  </Typography>
                </Box>
                <Box sx={{ textAlign: 'right' }}>
                  <Typography variant="subtitle1">{formatCurrency(asset.market_value)}</Typography>
                  <Chip
                    label={formatPercent(asset.actual_weight)}
                    size="small"
                    color={
                      Math.abs(asset.actual_weight - asset.target_weight) > 0.05
                        ? 'warning'
                        : 'success'
                    }
                  />
                </Box>
              </Box>
            </Grid>
          ))}
        </Grid>
      </Paper>

      {/* 最近の取引 */}
      <Paper sx={{ mt: 3, p: 2 }}>
        <Typography variant="h6" gutterBottom>
          最近の取引
        </Typography>
        {summary.recent_trades.length > 0 ? (
          <Grid container spacing={1}>
            {summary.recent_trades.map((trade, index) => (
              <Grid size={12} key={index}>
                <Box
                  sx={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    p: 1,
                    bgcolor: trade.pnl > 0 ? 'success.light' : 'error.light',
                    borderRadius: 1,
                    opacity: 0.7,
                  }}
                >
                  <Box>
                    <Typography variant="body2" fontWeight="bold">
                      {trade.symbol} - {trade.side.toUpperCase()}
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      {new Date(trade.timestamp).toLocaleString('ja-JP')}
                    </Typography>
                  </Box>
                  <Box sx={{ textAlign: 'right' }}>
                    <Typography variant="body2">
                      {trade.amount} @ {formatCurrency(trade.price)}
                    </Typography>
                    <Typography
                      variant="body2"
                      fontWeight="bold"
                      color={trade.pnl > 0 ? 'success.main' : 'error.main'}
                    >
                      {trade.pnl > 0 ? '+' : ''}
                      {formatCurrency(trade.pnl)}
                    </Typography>
                  </Box>
                </Box>
              </Grid>
            ))}
          </Grid>
        ) : (
          <Typography color="text.secondary">最近の取引はありません</Typography>
        )}
      </Paper>
    </Box>
  );
}
