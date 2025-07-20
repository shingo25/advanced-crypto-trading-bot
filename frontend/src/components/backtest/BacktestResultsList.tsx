'use client';

import React, { useState, useEffect } from 'react';
import {
  Box,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TablePagination,
  TableSortLabel,
  Chip,
  IconButton,
  Tooltip,
  Typography,
  Button,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  MenuItem,
  FormControl,
  InputLabel,
  Select,
  Alert,
  CircularProgress,
  Card,
  CardContent,
  Grid,
} from '@mui/material';
import {
  Visibility as VisibilityIcon,
  Delete as DeleteIcon,
  FilterList as FilterIcon,
  Download as DownloadIcon,
  Compare as CompareIcon,
  TrendingUp as TrendingUpIcon,
  TrendingDown as TrendingDownIcon,
} from '@mui/icons-material';
import { format, parseISO } from 'date-fns';
import { ja } from 'date-fns/locale';
import BacktestVisualization from './BacktestVisualization';

interface BacktestResultSummary {
  id: string;
  strategy_name: string;
  symbol: string;
  timeframe: string;
  start_date: string;
  end_date: string;
  initial_capital: number;
  final_capital: number;
  total_return: number;
  annualized_return: number;
  max_drawdown: number;
  sharpe_ratio: number;
  sortino_ratio: number;
  win_rate: number;
  total_trades: number;
  created_at: string;
  status: 'completed' | 'running' | 'failed';
}

interface BacktestResultsListProps {
  onViewResult?: (id: string) => void;
  onDeleteResult?: (id: string) => void;
  onCompareResults?: (ids: string[]) => void;
}

type SortKey = keyof BacktestResultSummary;
type SortOrder = 'asc' | 'desc';

export default function BacktestResultsList({
  onViewResult,
  onDeleteResult,
  onCompareResults,
}: BacktestResultsListProps) {
  // State
  const [results, setResults] = useState<BacktestResultSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(10);
  const [sortKey, setSortKey] = useState<SortKey>('created_at');
  const [sortOrder, setSortOrder] = useState<SortOrder>('desc');
  const [selectedResults, setSelectedResults] = useState<string[]>([]);
  const [filterOpen, setFilterOpen] = useState(false);
  const [detailDialogOpen, setDetailDialogOpen] = useState(false);
  const [selectedResult, setSelectedResult] = useState<any>(null);

  // Filters
  const [strategyFilter, setStrategyFilter] = useState('all');
  const [symbolFilter, setSymbolFilter] = useState('all');
  const [timeframeFilter, setTimeframeFilter] = useState('all');
  const [performanceFilter, setPerformanceFilter] = useState('all');

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
    const sign = value >= 0 ? '+' : '';
    return `${sign}${percent}%`;
  };

  const formatDate = (dateString: string) => {
    return format(parseISO(dateString), 'yyyy/MM/dd HH:mm', { locale: ja });
  };

  // パフォーマンス評価
  const getPerformanceRating = (sharpe: number, maxDrawdown: number, totalReturn: number) => {
    const score = sharpe * 0.4 + (1 - Math.abs(maxDrawdown)) * 0.3 + totalReturn * 0.3;
    if (score >= 0.8) return { label: '優秀', color: '#4caf50' };
    if (score >= 0.5) return { label: '良好', color: '#2196f3' };
    if (score >= 0.2) return { label: '普通', color: '#ff9800' };
    return { label: '要改善', color: '#f44336' };
  };

  // データ取得
  const fetchResults = async () => {
    try {
      setLoading(true);
      setError(null);

      // API呼び出し（実装例）
      const response = await fetch('/backtest/results');
      if (!response.ok) {
        throw new Error('データの取得に失敗しました');
      }

      const data = await response.json();
      setResults(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : '不明なエラーが発生しました');
      // デモデータ
      setResults([
        {
          id: '1',
          strategy_name: 'RSIスイング戦略',
          symbol: 'BTC/USDT',
          timeframe: '1h',
          start_date: '2024-01-01T00:00:00Z',
          end_date: '2024-06-30T23:59:59Z',
          initial_capital: 10000,
          final_capital: 12500,
          total_return: 0.25,
          annualized_return: 0.50,
          max_drawdown: -0.15,
          sharpe_ratio: 1.85,
          sortino_ratio: 2.10,
          win_rate: 0.68,
          total_trades: 45,
          created_at: '2024-07-01T10:30:00Z',
          status: 'completed',
        },
        {
          id: '2',
          strategy_name: 'MACD クロス戦略',
          symbol: 'ETH/USDT',
          timeframe: '4h',
          start_date: '2024-01-01T00:00:00Z',
          end_date: '2024-06-30T23:59:59Z',
          initial_capital: 10000,
          final_capital: 9500,
          total_return: -0.05,
          annualized_return: -0.10,
          max_drawdown: -0.25,
          sharpe_ratio: -0.35,
          sortino_ratio: -0.20,
          win_rate: 0.42,
          total_trades: 32,
          created_at: '2024-07-01T09:15:00Z',
          status: 'completed',
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchResults();
  }, []);

  // ソート処理
  const handleSort = (key: SortKey) => {
    const isAsc = sortKey === key && sortOrder === 'asc';
    setSortOrder(isAsc ? 'desc' : 'asc');
    setSortKey(key);
  };

  // フィルタリング
  const getFilteredResults = () => {
    let filtered = [...results];

    if (strategyFilter !== 'all') {
      filtered = filtered.filter(r => r.strategy_name === strategyFilter);
    }
    if (symbolFilter !== 'all') {
      filtered = filtered.filter(r => r.symbol === symbolFilter);
    }
    if (timeframeFilter !== 'all') {
      filtered = filtered.filter(r => r.timeframe === timeframeFilter);
    }
    if (performanceFilter !== 'all') {
      const threshold = performanceFilter === 'profitable' ? 0 : -0.05;
      filtered = filtered.filter(r =>
        performanceFilter === 'profitable' ? r.total_return > threshold : r.total_return <= threshold
      );
    }

    return filtered.sort((a, b) => {
      const aValue = a[sortKey];
      const bValue = b[sortKey];

      if (aValue < bValue) return sortOrder === 'asc' ? -1 : 1;
      if (aValue > bValue) return sortOrder === 'asc' ? 1 : -1;
      return 0;
    });
  };

  const filteredResults = getFilteredResults();
  const paginatedResults = filteredResults.slice(
    page * rowsPerPage,
    page * rowsPerPage + rowsPerPage
  );

  // 選択処理
  const handleSelectResult = (id: string) => {
    setSelectedResults(prev =>
      prev.includes(id)
        ? prev.filter(r => r !== id)
        : [...prev, id]
    );
  };

  // 詳細表示
  const handleViewDetail = async (id: string) => {
    try {
      // 詳細データを取得
      const response = await fetch(`/backtest/results/${id}`);
      const detailData = await response.json();
      setSelectedResult(detailData);
      setDetailDialogOpen(true);
    } catch (error) {
      console.error('詳細データの取得に失敗:', error);
    }
  };

  // サマリー統計
  const SummaryStats = () => {
    const stats = {
      total: results.length,
      profitable: results.filter(r => r.total_return > 0).length,
      avgReturn: results.reduce((sum, r) => sum + r.total_return, 0) / results.length || 0,
      avgSharpe: results.reduce((sum, r) => sum + r.sharpe_ratio, 0) / results.length || 0,
    };

    return (
      <Grid container spacing={2} sx={{ mb: 2 }}>
        <Grid item xs={3}>
          <Card>
            <CardContent>
              <Typography variant=\"body2\" color=\"text.secondary\">
                総テスト数
              </Typography>
              <Typography variant=\"h6\">{stats.total}</Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={3}>
          <Card>
            <CardContent>
              <Typography variant=\"body2\" color=\"text.secondary\">
                利益率
              </Typography>
              <Typography variant=\"h6\" sx={{ color: '#4caf50' }}>
                {((stats.profitable / stats.total) * 100).toFixed(1)}%
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={3}>
          <Card>
            <CardContent>
              <Typography variant=\"body2\" color=\"text.secondary\">
                平均リターン
              </Typography>
              <Typography
                variant=\"h6\"
                sx={{ color: stats.avgReturn >= 0 ? '#4caf50' : '#f44336' }}
              >
                {formatPercent(stats.avgReturn)}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={3}>
          <Card>
            <CardContent>
              <Typography variant=\"body2\" color=\"text.secondary\">
                平均シャープ
              </Typography>
              <Typography
                variant=\"h6\"
                sx={{ color: stats.avgSharpe >= 1 ? '#4caf50' : '#f44336' }}
              >
                {stats.avgSharpe.toFixed(2)}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    );
  };

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box sx={{ width: '100%' }}>
      <Paper sx={{ p: 2, mb: 2 }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
          <Typography variant=\"h5\" component=\"h2\">
            バックテスト結果一覧
          </Typography>
          <Box sx={{ display: 'flex', gap: 1 }}>
            <Button
              startIcon={<FilterIcon />}
              onClick={() => setFilterOpen(true)}
              variant=\"outlined\"
            >
              フィルター
            </Button>
            <Button
              startIcon={<CompareIcon />}
              onClick={() => onCompareResults?.(selectedResults)}
              disabled={selectedResults.length < 2}
              variant=\"outlined\"
            >
              比較 ({selectedResults.length})
            </Button>
            <Button
              startIcon={<DownloadIcon />}
              variant=\"outlined\"
            >
              エクスポート
            </Button>
          </Box>
        </Box>

        <SummaryStats />

        {error && (
          <Alert severity=\"error\" sx={{ mb: 2 }}>
            {error}
          </Alert>
        )}
      </Paper>

      <TableContainer component={Paper}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell padding=\"checkbox\">選択</TableCell>
              <TableCell>
                <TableSortLabel
                  active={sortKey === 'strategy_name'}
                  direction={sortKey === 'strategy_name' ? sortOrder : 'asc'}
                  onClick={() => handleSort('strategy_name')}
                >
                  戦略名
                </TableSortLabel>
              </TableCell>
              <TableCell>シンボル/時間枠</TableCell>
              <TableCell>
                <TableSortLabel
                  active={sortKey === 'total_return'}
                  direction={sortKey === 'total_return' ? sortOrder : 'asc'}
                  onClick={() => handleSort('total_return')}
                >
                  総リターン
                </TableSortLabel>
              </TableCell>
              <TableCell>
                <TableSortLabel
                  active={sortKey === 'sharpe_ratio'}
                  direction={sortKey === 'sharpe_ratio' ? sortOrder : 'asc'}
                  onClick={() => handleSort('sharpe_ratio')}
                >
                  シャープ
                </TableSortLabel>
              </TableCell>
              <TableCell>
                <TableSortLabel
                  active={sortKey === 'max_drawdown'}
                  direction={sortKey === 'max_drawdown' ? sortOrder : 'asc'}
                  onClick={() => handleSort('max_drawdown')}
                >
                  最大DD
                </TableSortLabel>
              </TableCell>
              <TableCell>勝率</TableCell>
              <TableCell>評価</TableCell>
              <TableCell>
                <TableSortLabel
                  active={sortKey === 'created_at'}
                  direction={sortKey === 'created_at' ? sortOrder : 'asc'}
                  onClick={() => handleSort('created_at')}
                >
                  作成日時
                </TableSortLabel>
              </TableCell>
              <TableCell>操作</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {paginatedResults.map((result) => {
              const rating = getPerformanceRating(
                result.sharpe_ratio,
                result.max_drawdown,
                result.total_return
              );
              return (
                <TableRow
                  key={result.id}
                  selected={selectedResults.includes(result.id)}
                  hover
                >
                  <TableCell padding=\"checkbox\">
                    <input
                      type=\"checkbox\"
                      checked={selectedResults.includes(result.id)}
                      onChange={() => handleSelectResult(result.id)}
                    />
                  </TableCell>
                  <TableCell>
                    <Typography variant=\"body2\" fontWeight=\"medium\">
                      {result.strategy_name}
                    </Typography>
                    <Typography variant=\"caption\" color=\"text.secondary\">
                      {result.total_trades} トレード
                    </Typography>
                  </TableCell>
                  <TableCell>
                    <Box>
                      <Chip label={result.symbol} size=\"small\" sx={{ mb: 0.5 }} />
                      <br />
                      <Chip label={result.timeframe} size=\"small\" variant=\"outlined\" />
                    </Box>
                  </TableCell>
                  <TableCell>
                    <Box sx={{ display: 'flex', alignItems: 'center' }}>
                      {result.total_return >= 0 ? (
                        <TrendingUpIcon sx={{ color: '#4caf50', mr: 0.5 }} />
                      ) : (
                        <TrendingDownIcon sx={{ color: '#f44336', mr: 0.5 }} />
                      )}
                      <Typography
                        variant=\"body2\"
                        sx={{
                          color: result.total_return >= 0 ? '#4caf50' : '#f44336',
                          fontWeight: 'medium'
                        }}
                      >
                        {formatPercent(result.total_return)}
                      </Typography>
                    </Box>
                  </TableCell>
                  <TableCell>
                    <Typography
                      variant=\"body2\"
                      sx={{
                        color: result.sharpe_ratio >= 1 ? '#4caf50' : '#f44336',
                        fontWeight: 'medium'
                      }}
                    >
                      {result.sharpe_ratio.toFixed(2)}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    <Typography
                      variant=\"body2\"
                      sx={{ color: '#f44336', fontWeight: 'medium' }}
                    >
                      {formatPercent(result.max_drawdown)}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    <Typography variant=\"body2\">
                      {formatPercent(result.win_rate)}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    <Chip
                      label={rating.label}
                      size=\"small\"
                      sx={{
                        backgroundColor: rating.color,
                        color: 'white',
                      }}
                    />
                  </TableCell>
                  <TableCell>
                    <Typography variant=\"caption\" color=\"text.secondary\">
                      {formatDate(result.created_at)}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    <Box sx={{ display: 'flex' }}>
                      <Tooltip title=\"詳細表示\">
                        <IconButton
                          size=\"small\"
                          onClick={() => handleViewDetail(result.id)}
                        >
                          <VisibilityIcon />
                        </IconButton>
                      </Tooltip>
                      <Tooltip title=\"削除\">
                        <IconButton
                          size=\"small\"
                          onClick={() => onDeleteResult?.(result.id)}
                          sx={{ color: '#f44336' }}
                        >
                          <DeleteIcon />
                        </IconButton>
                      </Tooltip>
                    </Box>
                  </TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>

        <TablePagination
          rowsPerPageOptions={[10, 25, 50]}
          component=\"div\"
          count={filteredResults.length}
          rowsPerPage={rowsPerPage}
          page={page}
          onPageChange={(e, newPage) => setPage(newPage)}
          onRowsPerPageChange={(e) => {
            setRowsPerPage(parseInt(e.target.value, 10));
            setPage(0);
          }}
        />
      </TableContainer>

      {/* 詳細表示ダイアログ */}
      <Dialog
        open={detailDialogOpen}
        onClose={() => setDetailDialogOpen(false)}
        maxWidth=\"xl\"
        fullWidth
      >
        <DialogTitle>バックテスト詳細結果</DialogTitle>
        <DialogContent>
          {selectedResult && (
            <BacktestVisualization result={selectedResult} />
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDetailDialogOpen(false)}>閉じる</Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
