'use client';

import React, { useState } from 'react';
import {
  Paper,
  Typography,
  Box,
  Grid,
  Tabs,
  Tab,
  Card,
  CardContent,
  Chip,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Tooltip as MuiTooltip,
} from '@mui/material';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  AreaChart,
  Area,
  BarChart,
  Bar,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Radar,
  ScatterChart,
  Scatter,
  Cell,
  ComposedChart,
} from 'recharts';
import { format, parseISO } from 'date-fns';
import { ja } from 'date-fns/locale';

interface Trade {
  id: string;
  timestamp: string;
  type: 'buy' | 'sell';
  symbol: string;
  price: number;
  quantity: number;
  realized_pnl: number;
}

interface BacktestResult {
  id: string;
  strategy_name: string;
  symbol: string;
  timeframe: string;
  start_date: string;
  end_date: string;
  initial_capital: number;
  final_capital: number;
  total_trades: number;
  win_rate: number;
  sharpe_ratio: number;
  sortino_ratio: number;
  calmar_ratio: number;
  max_drawdown: number;
  total_return: number;
  annualized_return: number;
  volatility: number;
  profit_factor: number;
  trades: Trade[];
  equity_curve: Array<{
    timestamp: string;
    equity: number;
    drawdown: number;
    daily_return: number;
  }>;
  monthly_returns: Array<{
    year: number;
    month: number;
    return: number;
  }>;
  performance_metrics: {
    var_95: number;
    var_99: number;
    beta: number;
    skewness: number;
    kurtosis: number;
    consecutive_wins: number;
    consecutive_losses: number;
  };
}

interface BacktestVisualizationProps {
  result: BacktestResult;
  benchmarkData?: Array<{
    timestamp: string;
    price: number;
    return: number;
  }>;
}

export default function BacktestVisualization({
  result,
  benchmarkData = [],
}: BacktestVisualizationProps) {
  const [activeTab, setActiveTab] = useState(0);
  const [timeframe, setTimeframe] = useState('all');

  // 色定義
  const colors = {
    primary: '#1976d2',
    success: '#2e7d32',
    error: '#d32f2f',
    warning: '#f57c00',
    info: '#0288d1',
    secondary: '#7b1fa2',
  };

  // データフォーマッター
  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('ja-JP', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(value);
  };

  const formatPercent = (value: number) => {
    const percent = (value * 100).toFixed(2);
    return `${percent}%`;
  };

  const formatDate = (dateString: string) => {
    return format(parseISO(dateString), 'MM/dd', { locale: ja });
  };

  // 1. エクイティカーブチャート
  const EquityCurveChart = () => {
    const chartData = result.equity_curve.map((item, index) => {
      const benchmark = benchmarkData[index] || { return: 0 };
      return {
        ...item,
        date: formatDate(item.timestamp),
        fullDate: item.timestamp,
        equity: item.equity,
        benchmark: result.initial_capital * (1 + benchmark.return),
        drawdownPercent: item.drawdown * 100,
      };
    });

    return (
      <ResponsiveContainer width=\"100%\" height={400}>
        <ComposedChart data={chartData}>
          <CartesianGrid strokeDasharray=\"3 3\" />
          <XAxis
            dataKey=\"date\"
            tick={{ fontSize: 12 }}
            interval=\"preserveStartEnd\"
          />
          <YAxis
            yAxisId=\"equity\"
            tick={{ fontSize: 12 }}
            tickFormatter={formatCurrency}
          />
          <YAxis
            yAxisId=\"drawdown\"
            orientation=\"right\"
            tick={{ fontSize: 12 }}
            tickFormatter={(value) => `${value.toFixed(1)}%`}
          />
          <Tooltip
            content={({ active, payload, label }) => {
              if (active && payload && payload.length) {
                const data = payload[0]?.payload;
                return (
                  <Card sx={{ p: 1 }}>
                    <Typography variant=\"body2\">{label}</Typography>
                    <Typography variant=\"body2\" color={colors.primary}>
                      資産: {formatCurrency(data?.equity || 0)}
                    </Typography>
                    {benchmarkData.length > 0 && (
                      <Typography variant=\"body2\" color={colors.secondary}>
                        ベンチマーク: {formatCurrency(data?.benchmark || 0)}
                      </Typography>
                    )}
                    <Typography variant=\"body2\" color={colors.error}>
                      ドローダウン: {data?.drawdownPercent?.toFixed(2)}%
                    </Typography>
                  </Card>
                );
              }
              return null;
            }}
          />
          <Area
            yAxisId=\"equity\"
            type=\"monotone\"
            dataKey=\"equity\"
            stroke={colors.primary}
            fill={colors.primary}
            fillOpacity={0.1}
            name=\"資産\"
          />
          {benchmarkData.length > 0 && (
            <Line
              yAxisId=\"equity\"
              type=\"monotone\"
              dataKey=\"benchmark\"
              stroke={colors.secondary}
              strokeDasharray=\"5 5\"
              dot={false}
              name=\"ベンチマーク\"
            />
          )}
          <Bar
            yAxisId=\"drawdown\"
            dataKey=\"drawdownPercent\"
            fill={colors.error}
            fillOpacity={0.3}
            name=\"ドローダウン\"
          />
        </ComposedChart>
      </ResponsiveContainer>
    );
  };

  // 2. 月次リターンヒートマップ
  const MonthlyReturnsHeatmap = () => {
    const heatmapData = result.monthly_returns.map((item) => ({
      year: item.year,
      month: item.month,
      return: item.return * 100,
      monthName: new Date(item.year, item.month - 1).toLocaleDateString('ja-JP', {
        month: 'short',
      }),
    }));

    const getColorIntensity = (value: number) => {
      const absMax = Math.max(...heatmapData.map(d => Math.abs(d.return)));
      const intensity = Math.abs(value) / absMax;
      return value >= 0
        ? `rgba(76, 175, 80, ${intensity})`
        : `rgba(244, 67, 54, ${intensity})`;
    };

    return (
      <Box sx={{ height: 300, overflowX: 'auto' }}>
        <Grid container spacing={0.5}>
          {heatmapData.map((item, index) => (
            <Grid item key={index}>
              <MuiTooltip
                title={`${item.year}年${item.monthName}: ${item.return.toFixed(2)}%`}
              >
                <Card
                  sx={{
                    width: 60,
                    height: 40,
                    backgroundColor: getColorIntensity(item.return),
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    cursor: 'pointer',
                  }}
                >
                  <Typography variant=\"caption\" color=\"white\">
                    {item.return.toFixed(1)}%
                  </Typography>
                </Card>
              </MuiTooltip>
            </Grid>
          ))}
        </Grid>
      </Box>
    );
  };

  // 3. トレード分析チャート
  const TradeAnalysisChart = () => {
    const tradeData = result.trades.map((trade, index) => ({
      index: index + 1,
      pnl: trade.realized_pnl,
      cumulativePnl: result.trades.slice(0, index + 1).reduce((sum, t) => sum + t.realized_pnl, 0),
      isWin: trade.realized_pnl > 0,
    }));

    return (
      <ResponsiveContainer width=\"100%\" height={300}>
        <ComposedChart data={tradeData}>
          <CartesianGrid strokeDasharray=\"3 3\" />
          <XAxis
            dataKey=\"index\"
            tick={{ fontSize: 12 }}
            label={{ value: 'トレード番号', position: 'insideBottom', offset: -5 }}
          />
          <YAxis
            yAxisId=\"pnl\"
            tick={{ fontSize: 12 }}
            tickFormatter={formatCurrency}
          />
          <YAxis
            yAxisId=\"cumulative\"
            orientation=\"right\"
            tick={{ fontSize: 12 }}
            tickFormatter={formatCurrency}
          />
          <Tooltip
            content={({ active, payload, label }) => {
              if (active && payload && payload.length) {
                const data = payload[0]?.payload;
                return (
                  <Card sx={{ p: 1 }}>
                    <Typography variant=\"body2\">トレード #{label}</Typography>
                    <Typography
                      variant=\"body2\"
                      color={data?.isWin ? colors.success : colors.error}
                    >
                      PnL: {formatCurrency(data?.pnl || 0)}
                    </Typography>
                    <Typography variant=\"body2\" color={colors.primary}>
                      累計PnL: {formatCurrency(data?.cumulativePnl || 0)}
                    </Typography>
                  </Card>
                );
              }
              return null;
            }}
          />
          <Bar
            yAxisId=\"pnl\"
            dataKey=\"pnl\"
            name=\"個別PnL\"
          >
            {tradeData.map((entry, index) => (
              <Cell
                key={`cell-${index}`}
                fill={entry.isWin ? colors.success : colors.error}
              />
            ))}
          </Bar>
          <Line
            yAxisId=\"cumulative\"
            type=\"monotone\"
            dataKey=\"cumulativePnl\"
            stroke={colors.primary}
            strokeWidth={2}
            dot={false}
            name=\"累計PnL\"
          />
        </ComposedChart>
      </ResponsiveContainer>
    );
  };

  // 4. リスク指標レーダーチャート
  const RiskRadarChart = () => {
    const maxValues = {
      sharpe: 3,
      sortino: 3,
      calmar: 2,
      profit_factor: 3,
      win_rate: 1,
      beta: 2,
    };

    const radarData = [
      {
        metric: 'シャープ',
        value: Math.min(Math.max(result.sharpe_ratio, 0), maxValues.sharpe),
        fullValue: result.sharpe_ratio,
      },
      {
        metric: 'ソルティノ',
        value: Math.min(Math.max(result.sortino_ratio, 0), maxValues.sortino),
        fullValue: result.sortino_ratio,
      },
      {
        metric: 'カルマー',
        value: Math.min(Math.max(result.calmar_ratio, 0), maxValues.calmar),
        fullValue: result.calmar_ratio,
      },
      {
        metric: 'プロフィット',
        value: Math.min(Math.max(result.profit_factor, 0), maxValues.profit_factor),
        fullValue: result.profit_factor,
      },
      {
        metric: '勝率',
        value: result.win_rate,
        fullValue: result.win_rate,
      },
      {
        metric: 'ベータ',
        value: Math.min(Math.max(Math.abs(result.performance_metrics.beta || 0), 0), maxValues.beta),
        fullValue: result.performance_metrics.beta || 0,
      },
    ];

    return (
      <ResponsiveContainer width=\"100%\" height={300}>
        <RadarChart data={radarData}>
          <PolarGrid />
          <PolarAngleAxis
            dataKey=\"metric\"
            tick={{ fontSize: 12 }}
          />
          <PolarRadiusAxis
            angle={90}
            domain={[0, 'dataMax']}
            tick={{ fontSize: 10 }}
          />
          <Radar
            name=\"指標値\"
            dataKey=\"value\"
            stroke={colors.primary}
            fill={colors.primary}
            fillOpacity={0.3}
            strokeWidth={2}
          />
          <Tooltip
            content={({ payload }) => {
              if (payload && payload.length > 0) {
                const data = payload[0]?.payload;
                return (
                  <Card sx={{ p: 1 }}>
                    <Typography variant=\"body2\">
                      {data?.metric}: {data?.fullValue?.toFixed(3)}
                    </Typography>
                  </Card>
                );
              }
              return null;
            }}
          />
        </RadarChart>
      </ResponsiveContainer>
    );
  };

  // 5. パフォーマンス統計カード
  const PerformanceStats = () => {
    const stats = [
      { label: '総リターン', value: formatPercent(result.total_return), color: colors.primary },
      { label: '年率リターン', value: formatPercent(result.annualized_return), color: colors.success },
      { label: '最大ドローダウン', value: formatPercent(result.max_drawdown), color: colors.error },
      { label: 'ボラティリティ', value: formatPercent(result.volatility), color: colors.warning },
      { label: 'シャープレシオ', value: result.sharpe_ratio.toFixed(3), color: colors.info },
      { label: 'プロフィットファクター', value: result.profit_factor.toFixed(2), color: colors.secondary },
      { label: '勝率', value: formatPercent(result.win_rate), color: colors.success },
      { label: '総トレード数', value: result.total_trades.toString(), color: colors.primary },
    ];

    return (
      <Grid container spacing={2}>
        {stats.map((stat, index) => (
          <Grid item xs={6} sm={3} key={index}>
            <Card>
              <CardContent>
                <Typography variant=\"body2\" color=\"text.secondary\">
                  {stat.label}
                </Typography>
                <Typography
                  variant=\"h6\"
                  sx={{ color: stat.color, fontWeight: 'bold' }}
                >
                  {stat.value}
                </Typography>
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>
    );
  };

  const tabLabels = ['概要', 'エクイティカーブ', '月次リターン', 'トレード分析', 'リスク指標'];

  return (
    <Box sx={{ width: '100%' }}>
      {/* ヘッダー情報 */}
      <Paper sx={{ p: 2, mb: 2 }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
          <Typography variant=\"h5\" component=\"h2\">
            バックテスト結果: {result.strategy_name}
          </Typography>
          <Box sx={{ display: 'flex', gap: 1 }}>
            <Chip label={result.symbol} variant=\"outlined\" />
            <Chip label={result.timeframe} variant=\"outlined\" />
            <Chip
              label={`${formatDate(result.start_date)} - ${formatDate(result.end_date)}`}
              variant=\"outlined\"
            />
          </Box>
        </Box>

        {/* 期間選択 */}
        <Box sx={{ display: 'flex', gap: 2, alignItems: 'center' }}>
          <FormControl size=\"small\" sx={{ minWidth: 120 }}>
            <InputLabel>表示期間</InputLabel>
            <Select
              value={timeframe}
              label=\"表示期間\"
              onChange={(e) => setTimeframe(e.target.value)}
            >
              <MenuItem value=\"all\">全期間</MenuItem>
              <MenuItem value=\"1y\">1年</MenuItem>
              <MenuItem value=\"6m\">6ヶ月</MenuItem>
              <MenuItem value=\"3m\">3ヶ月</MenuItem>
              <MenuItem value=\"1m\">1ヶ月</MenuItem>
            </Select>
          </FormControl>
        </Box>
      </Paper>

      {/* タブナビゲーション */}
      <Paper sx={{ mb: 2 }}>
        <Tabs
          value={activeTab}
          onChange={(e, newValue) => setActiveTab(newValue)}
          variant=\"scrollable\"
          scrollButtons=\"auto\"
        >
          {tabLabels.map((label, index) => (
            <Tab key={index} label={label} />
          ))}
        </Tabs>
      </Paper>

      {/* タブコンテンツ */}
      <Paper sx={{ p: 2 }}>
        {activeTab === 0 && <PerformanceStats />}
        {activeTab === 1 && (
          <Box>
            <Typography variant=\"h6\" gutterBottom>
              エクイティカーブ & ドローダウン
            </Typography>
            <EquityCurveChart />
          </Box>
        )}
        {activeTab === 2 && (
          <Box>
            <Typography variant=\"h6\" gutterBottom>
              月次リターンヒートマップ
            </Typography>
            <MonthlyReturnsHeatmap />
          </Box>
        )}
        {activeTab === 3 && (
          <Box>
            <Typography variant=\"h6\" gutterBottom>
              トレード分析
            </Typography>
            <TradeAnalysisChart />
          </Box>
        )}
        {activeTab === 4 && (
          <Box>
            <Typography variant=\"h6\" gutterBottom>
              リスク指標レーダーチャート
            </Typography>
            <RiskRadarChart />
          </Box>
        )}
      </Paper>
    </Box>
  );
}
